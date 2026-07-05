"""Prompt Builder orchestration (docs/05-task.md Phase 14).

Builds a `Prompt` synchronously from a completed `Retrieval` — no Celery
task, unlike Phase 5-13's document/chunk/embedding/index/retrieval
pipeline stages. Token counting and context assembly are deterministic
CPU-bound computation over data the caller already fetched (no ML
inference, no external HTTP calls), so there is nothing here that
benefits from async background processing the way, say, cross-encoder
reranking (Phase 13) or embedding generation (Phase 7) do.

Depends on `RetrievalService` rather than its own copy of
document/vector-index/retrieval verification — that logic already lives
there (`_get_vector_index`, `get_retrieval`, `get_results`) and
duplicating it here would just be two places that could drift out of
sync on what "this retrieval belongs to this document" means.
"""

import uuid
from typing import cast

from app.core.citations import build_citations
from app.core.context_window import build_context_window
from app.core.exceptions import ConflictError, NotFoundError
from app.core.prompt_render import render_prompt
from app.core.token_budget import available_context_tokens, count_tokens
from app.models.audit_log import AuditLog
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.prompt import Prompt, PromptStatus
from app.models.retrieval import RetrievalResult, RetrievalStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.prompt_repository import PromptRepository
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.schemas.prompt import CreatePromptRequest
from app.services.retrieval_service import RetrievalService


class PromptService:
    def __init__(
        self,
        prompt_repository: PromptRepository,
        prompt_template_repository: PromptTemplateRepository,
        retrieval_service: RetrievalService,
        audit_log_repository: AuditLogRepository,
    ):
        self.prompts = prompt_repository
        self.prompt_templates = prompt_template_repository
        self.retrievals = retrieval_service
        self.audit_logs = audit_log_repository

    async def build_prompt(
        self,
        document: Document,
        vector_index_id: uuid.UUID,
        retrieval_id: uuid.UUID,
        payload: CreatePromptRequest,
        *,
        actor_id: uuid.UUID,
    ) -> Prompt:
        retrieval = await self.retrievals.get_retrieval(document.id, vector_index_id, retrieval_id)
        if retrieval.status != RetrievalStatus.COMPLETED:
            raise ConflictError(
                "Retrieval has not completed yet; cannot build a prompt from it.",
                code="RETRIEVAL_NOT_COMPLETED",
            )

        system_prompt = payload.system_prompt
        formatting_instructions = payload.formatting_instructions
        output_schema = payload.output_schema
        if payload.prompt_template_id is not None:
            template = await self.prompt_templates.get_by_id(payload.prompt_template_id)
            if template is None or template.repository_id != document.repository_id:
                raise NotFoundError(
                    "Prompt template not found.", code="PROMPT_TEMPLATE_NOT_FOUND"
                )
            system_prompt = system_prompt or template.system_prompt
            formatting_instructions = formatting_instructions or template.formatting_instructions
            output_schema = output_schema or template.output_schema

        # Guaranteed non-None: CreatePromptRequest's validator requires
        # system_prompt whenever no prompt_template_id is given, and the
        # branch above resolves it from the template otherwise.
        assert system_prompt is not None
        query_tokens = count_tokens(retrieval.query_text)
        system_prompt_tokens = count_tokens(system_prompt)
        conversation_tokens = 0  # Phase 16 (conversation memory) does not exist yet.

        context_budget = available_context_tokens(
            model_context_window=payload.model_context_window,
            system_prompt_tokens=system_prompt_tokens,
            conversation_tokens=conversation_tokens,
            query_tokens=query_tokens,
            response_reserve_tokens=payload.response_reserve_tokens,
        )

        prompt = Prompt(
            retrieval_id=retrieval_id,
            prompt_template_id=payload.prompt_template_id,
            model_context_window=payload.model_context_window,
            system_prompt_tokens=system_prompt_tokens,
            conversation_tokens=conversation_tokens,
            response_budget_tokens=payload.response_reserve_tokens,
            query_tokens=query_tokens,
            created_by=actor_id,
        )

        if context_budget <= 0:
            prompt.status = PromptStatus.FAILED
            prompt.status_message = (
                "System prompt, query, and response reserve alone exceed "
                "model_context_window; no room left for retrieved context."
            )
            await self.prompts.add(prompt)
            await self._record_audit(actor_id, prompt, result="failed")
            return prompt

        # get_results is typed loosely as list[tuple[RetrievalResult, object]]
        # (pre-existing, see retrieval_service.py) — the join always yields
        # actual Chunk rows.
        rows = cast(
            "list[tuple[RetrievalResult, Chunk]]",
            await self.retrievals.get_results(document.id, vector_index_id, retrieval_id),
        )
        context_text, entries = build_context_window(
            rows,
            document_id=str(document.id),
            token_budget=context_budget,
            order_by_page=payload.order_by_page,
        )
        citations = build_citations(entries, document_filename=document.filename)

        rendered_prompt = render_prompt(
            system_prompt=system_prompt,
            context_text=context_text,
            query_text=retrieval.query_text,
            formatting_instructions=formatting_instructions,
            output_schema=output_schema,
        )

        prompt.context_tokens = count_tokens(context_text)
        prompt.total_tokens = count_tokens(rendered_prompt)
        prompt.rendered_system_prompt = system_prompt
        prompt.rendered_context = context_text
        prompt.rendered_prompt = rendered_prompt
        prompt.citations = citations
        prompt.status = PromptStatus.COMPLETED
        if rows and not entries:
            prompt.status_message = "No retrieved context could fit within the token budget."

        await self.prompts.add(prompt)
        await self._record_audit(actor_id, prompt, result="success")
        return prompt

    async def _record_audit(self, actor_id: uuid.UUID, prompt: Prompt, *, result: str) -> None:
        await self.audit_logs.add(
            AuditLog(
                user_id=actor_id,
                action="prompt.build",
                resource=str(prompt.id),
                result=result,
            )
        )

    async def list_by_retrieval(
        self, document_id: uuid.UUID, vector_index_id: uuid.UUID, retrieval_id: uuid.UUID
    ) -> list[Prompt]:
        await self.retrievals.get_retrieval(document_id, vector_index_id, retrieval_id)
        return await self.prompts.list_by_retrieval(retrieval_id)

    async def get(
        self,
        document_id: uuid.UUID,
        vector_index_id: uuid.UUID,
        retrieval_id: uuid.UUID,
        prompt_id: uuid.UUID,
    ) -> Prompt:
        await self.retrievals.get_retrieval(document_id, vector_index_id, retrieval_id)
        prompt = await self.prompts.get_by_id(prompt_id)
        if prompt is None or prompt.retrieval_id != retrieval_id:
            raise NotFoundError("Prompt not found.", code="PROMPT_NOT_FOUND")
        return prompt
