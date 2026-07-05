"""Conversation orchestration (docs/05-task.md Phase 16;
docs/02-architecture.md section 97's "Memory Retrieval Pipeline": New
Query -> Retrieve Conversation -> Summarize History (if required) ->
Merge User Query -> Send to Retriever -> Prompt Builder).

`send_message` is the one method that actually runs a full turn:
persist the user's message, condense it against prior history into a
standalone query (`core/conversation/condensation.py`), run a real
Phase 9 retrieval, build a real Phase 14 prompt (folding in short-term
history and this user's long-term custom instructions), generate a real
Phase 15 completion, persist the assistant's message, and summarize the
conversation if it has grown past the token threshold. Every step reuses
the existing phase's service rather than re-implementing it.

**Why this method commits mid-request** (`await self.session.commit()`
right after creating the `Retrieval` row, before enqueueing): `get_db`
normally commits only once, after the whole request finishes — but this
method needs to synchronously wait for a Celery-processed result within
the *same* request (there is no "come back later and poll" UX for a chat
message), and `retrieval_worker` runs in a separate process with its own
DB connection. Enqueueing before this transaction commits would let the
worker query for a `Retrieval` row that, from its connection's point of
view, doesn't exist yet — the exact race `document_service.py` already
documents and works around (there, by deferring the enqueue to a
`BackgroundTasks` callback that only runs after the response). That
technique doesn't work here because we can't defer past the response —
we *are* the response — so this is a deliberate, narrow, documented
exception to the "services only flush, `get_db` commits" convention.
"""

import asyncio
import uuid

from app.core.conversation.condensation import condense_query
from app.core.conversation.summarization import summarize_messages
from app.core.exceptions import NotFoundError
from app.core.llm.gateway import LLMGateway
from app.core.task_queue import enqueue_execute_retrieval
from app.core.token_budget import count_tokens
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, ConversationSummary, Message, MessageRole
from app.models.document import Document
from app.models.retrieval import Retrieval, RetrievalStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.conversation_repository import (
    ConversationMemoryRepository,
    ConversationRepository,
    ConversationSummaryRepository,
    MessageRepository,
)
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.schemas.conversation import CreateConversationRequest, SendMessageRequest
from app.schemas.llm import CreateCompletionRequest
from app.schemas.prompt import CreatePromptRequest
from app.schemas.retrieval import CreateRetrievalRequest
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.retrieval_service import RetrievalService

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful enterprise assistant. Answer only using the supplied context and "
    'conversation history. If the answer is unavailable, say "I don\'t know."'
)
SUMMARIZATION_TOKEN_THRESHOLD = 2000
RETRIEVAL_POLL_TIMEOUT_SECONDS = 20.0
RETRIEVAL_POLL_INTERVAL_SECONDS = 0.3


class ConversationService:
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        summary_repository: ConversationSummaryRepository,
        memory_repository: ConversationMemoryRepository,
        prompt_template_repository: PromptTemplateRepository,
        retrieval_service: RetrievalService,
        prompt_service: PromptService,
        llm_service: LLMService,
        audit_log_repository: AuditLogRepository,
    ):
        self.conversations = conversation_repository
        self.messages = message_repository
        self.summaries = summary_repository
        self.memory = memory_repository
        self.prompt_templates = prompt_template_repository
        self.retrievals = retrieval_service
        self.prompts = prompt_service
        self.llm = llm_service
        self.audit_logs = audit_log_repository
        # Every repository above shares one AsyncSession (they're all built from the
        # same request-scoped `get_db`) — reused here for the documented mid-request
        # commit, not a second connection.
        self.session = conversation_repository.session

    async def create_conversation(
        self,
        document: Document,
        vector_index_id: uuid.UUID,
        payload: CreateConversationRequest,
        *,
        actor_id: uuid.UUID,
    ) -> Conversation:
        await self.retrievals.get_vector_index(document.id, vector_index_id)
        conversation = await self.conversations.add(
            Conversation(
                repository_id=document.repository_id,
                document_id=document.id,
                vector_index_id=vector_index_id,
                prompt_template_id=payload.prompt_template_id,
                title=payload.title,
                created_by=actor_id,
            )
        )
        await self._record_audit(actor_id, "conversation.create", conversation.id)
        return conversation

    async def list_conversations(
        self, document_id: uuid.UUID, vector_index_id: uuid.UUID
    ) -> list[Conversation]:
        return [
            c
            for c in await self.conversations.list_by_document(document_id)
            if c.vector_index_id == vector_index_id
        ]

    async def get_conversation(
        self, document_id: uuid.UUID, vector_index_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self.conversations.get_by_id(conversation_id)
        if (
            conversation is None
            or conversation.document_id != document_id
            or conversation.vector_index_id != vector_index_id
        ):
            raise NotFoundError("Conversation not found.", code="CONVERSATION_NOT_FOUND")
        return conversation

    async def delete_conversation(
        self,
        document_id: uuid.UUID,
        vector_index_id: uuid.UUID,
        conversation_id: uuid.UUID,
        *,
        actor_id: uuid.UUID,
    ) -> None:
        conversation = await self.get_conversation(document_id, vector_index_id, conversation_id)
        await self.conversations.delete(conversation)
        await self._record_audit(actor_id, "conversation.delete", conversation_id)

    async def list_messages(
        self, document_id: uuid.UUID, vector_index_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> list[Message]:
        await self.get_conversation(document_id, vector_index_id, conversation_id)
        return await self.messages.list_by_conversation(conversation_id)

    async def _history_text(self, conversation_id: uuid.UUID) -> str:
        summary = await self.summaries.get_latest(conversation_id)
        recent = await self.messages.list_by_conversation(
            conversation_id,
            after_message_id=summary.covers_up_to_message_id if summary else None,
        )
        parts = []
        if summary:
            parts.append(f"Summary of earlier conversation: {summary.summary_text}")
        for message in recent:
            speaker = "User" if message.role == MessageRole.USER else "Assistant"
            parts.append(f"{speaker}: {message.content}")
        return "\n".join(parts)

    async def _wait_for_retrieval(self, retrieval_id: uuid.UUID) -> Retrieval:
        retrieval = await self.retrievals.retrievals.get_by_id(retrieval_id)
        assert retrieval is not None
        elapsed = 0.0
        while (
            retrieval.status == RetrievalStatus.PENDING
            and elapsed < RETRIEVAL_POLL_TIMEOUT_SECONDS
        ):
            await asyncio.sleep(RETRIEVAL_POLL_INTERVAL_SECONDS)
            elapsed += RETRIEVAL_POLL_INTERVAL_SECONDS
            await self.session.refresh(retrieval)
        return retrieval

    async def _resolve_system_prompt(
        self, conversation: Conversation, actor_id: uuid.UUID
    ) -> str:
        base_prompt = DEFAULT_SYSTEM_PROMPT
        if conversation.prompt_template_id is not None:
            template = await self.prompt_templates.get_by_id(conversation.prompt_template_id)
            if template is not None:
                base_prompt = template.system_prompt

        memory = await self.memory.get_for_user_repository(actor_id, conversation.repository_id)
        if memory and memory.custom_instructions:
            return f"{base_prompt}\n\nAdditional instructions: {memory.custom_instructions}"
        return base_prompt

    async def send_message(
        self,
        document: Document,
        vector_index_id: uuid.UUID,
        conversation_id: uuid.UUID,
        payload: SendMessageRequest,
        *,
        actor_id: uuid.UUID,
    ) -> tuple[Message, Message]:
        conversation = await self.get_conversation(
            document.id, vector_index_id, conversation_id
        )
        history_text = await self._history_text(conversation.id)

        user_message = await self.messages.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=payload.content,
                token_count=count_tokens(payload.content),
            )
        )

        gateway = LLMGateway()
        standalone_query = await condense_query(gateway, history_text, payload.content)

        retrieval = await self.retrievals.create_retrieval(
            document.id,
            vector_index_id,
            CreateRetrievalRequest(query_text=standalone_query),
            actor_id=actor_id,
        )
        await self.session.commit()
        enqueue_execute_retrieval(str(retrieval.id))
        retrieval = await self._wait_for_retrieval(retrieval.id)

        if retrieval.status != RetrievalStatus.COMPLETED:
            assistant_message = await self.messages.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=(
                        "Sorry, I couldn't retrieve context for that question in time. "
                        "Please try again."
                    ),
                    token_count=0,
                    retrieval_id=retrieval.id,
                )
            )
            conversation.total_tokens += user_message.token_count
            return user_message, assistant_message

        system_prompt = await self._resolve_system_prompt(conversation, actor_id)
        prompt = await self.prompts.build_prompt(
            document,
            vector_index_id,
            retrieval.id,
            CreatePromptRequest(system_prompt=system_prompt),
            actor_id=actor_id,
            conversation_text=history_text or None,
        )

        llm_request = await self.llm.create_completion(
            document.id,
            vector_index_id,
            retrieval.id,
            prompt.id,
            CreateCompletionRequest(),
            actor_id=actor_id,
        )

        assistant_content = llm_request.output_text or (
            llm_request.status_message or "The assistant could not generate a response."
        )
        assistant_message = await self.messages.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                token_count=llm_request.output_tokens,
                retrieval_id=retrieval.id,
                prompt_id=prompt.id,
                llm_request_id=llm_request.id,
            )
        )

        conversation.total_tokens += user_message.token_count + assistant_message.token_count
        await self._maybe_summarize(conversation, gateway)
        await self._record_audit(actor_id, "conversation.message", conversation.id)

        return user_message, assistant_message

    async def _maybe_summarize(self, conversation: Conversation, gateway: LLMGateway) -> None:
        summary = await self.summaries.get_latest(conversation.id)
        unsummarized = await self.messages.list_by_conversation(
            conversation.id,
            after_message_id=summary.covers_up_to_message_id if summary else None,
        )
        unsummarized_tokens = sum(m.token_count for m in unsummarized)
        if unsummarized_tokens < SUMMARIZATION_TOKEN_THRESHOLD or len(unsummarized) < 2:
            return

        history_prefix = f"{summary.summary_text}\n\n" if summary else ""
        transcript = "\n".join(
            f"{'User' if m.role == MessageRole.USER else 'Assistant'}: {m.content}"
            for m in unsummarized
        )
        try:
            summary_text = await summarize_messages(gateway, history_prefix + transcript)
        except Exception:  # noqa: BLE001 - skip this turn's summarization, try again later
            return

        await self.summaries.add(
            ConversationSummary(
                conversation_id=conversation.id,
                summary_text=summary_text,
                covers_message_count=(summary.covers_message_count if summary else 0)
                + len(unsummarized),
                covers_up_to_message_id=unsummarized[-1].id,
            )
        )

    async def _record_audit(self, actor_id: uuid.UUID, action: str, resource_id: uuid.UUID) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=actor_id, action=action, resource=str(resource_id), result="success")
        )
