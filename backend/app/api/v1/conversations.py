"""Conversation endpoints (docs/05-task.md Phase 16).

Conversations are nested under document/vector-index, the same VIEWER+
pattern as retrievals/prompts — starting or continuing a chat is a
read-oriented action over an existing index, not a mutation of it.
`POST .../messages` is the one endpoint that does real work (a full
retrieval -> prompt -> completion turn, synchronously) — see
`ConversationService.send_message`'s docstring for why.

Conversation memory (long-term, per user+repository) lives at the
repository level rather than nested under a document, since it's
explicitly *not* scoped to one conversation or document (section 95:
"persisted across conversations").
"""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from app.api.conversation_deps import get_conversation_service, get_memory_service
from app.api.document_deps import DocumentAccess, require_document_role
from app.api.tenancy_deps import require_repository_role
from app.models.membership import MemberRole
from app.models.repository import RepositoryMember
from app.schemas.common import SuccessResponse
from app.schemas.conversation import (
    ConversationMemoryRead,
    ConversationRead,
    CreateConversationRequest,
    MessageRead,
    MessageTurnRead,
    SendMessageRequest,
    UpdateConversationMemoryRequest,
)
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService

router = APIRouter(tags=["conversations"])

_CONVERSATIONS_PATH = (
    "/documents/{document_id}/vector-indexes/{vector_index_id}/conversations"
)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(_CONVERSATIONS_PATH, response_model=SuccessResponse[ConversationRead])
async def create_conversation(
    vector_index_id: uuid.UUID,
    payload: CreateConversationRequest,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[ConversationRead]:
    conversation = await service.create_conversation(
        access.document, vector_index_id, payload, actor_id=access.membership.user_id
    )
    return SuccessResponse(
        data=ConversationRead.model_validate(conversation), request_id=_request_id(request)
    )


@router.get(_CONVERSATIONS_PATH, response_model=SuccessResponse[list[ConversationRead]])
async def list_conversations(
    vector_index_id: uuid.UUID,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[list[ConversationRead]]:
    conversations = await service.list_conversations(access.document.id, vector_index_id)
    return SuccessResponse(
        data=[ConversationRead.model_validate(c) for c in conversations],
        request_id=_request_id(request),
    )


@router.get(
    f"{_CONVERSATIONS_PATH}/{{conversation_id}}", response_model=SuccessResponse[ConversationRead]
)
async def get_conversation(
    vector_index_id: uuid.UUID,
    conversation_id: uuid.UUID,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[ConversationRead]:
    conversation = await service.get_conversation(
        access.document.id, vector_index_id, conversation_id
    )
    return SuccessResponse(
        data=ConversationRead.model_validate(conversation), request_id=_request_id(request)
    )


@router.delete(f"{_CONVERSATIONS_PATH}/{{conversation_id}}", response_model=SuccessResponse[dict])
async def delete_conversation(
    vector_index_id: uuid.UUID,
    conversation_id: uuid.UUID,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[dict]:
    await service.delete_conversation(
        access.document.id,
        vector_index_id,
        conversation_id,
        actor_id=access.membership.user_id,
    )
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))


@router.get(
    f"{_CONVERSATIONS_PATH}/{{conversation_id}}/messages",
    response_model=SuccessResponse[list[MessageRead]],
)
async def list_messages(
    vector_index_id: uuid.UUID,
    conversation_id: uuid.UUID,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[list[MessageRead]]:
    messages = await service.list_messages(access.document.id, vector_index_id, conversation_id)
    return SuccessResponse(
        data=[MessageRead.model_validate(m) for m in messages], request_id=_request_id(request)
    )


@router.post(
    f"{_CONVERSATIONS_PATH}/{{conversation_id}}/messages",
    response_model=SuccessResponse[MessageTurnRead],
)
async def send_message(
    vector_index_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[MessageTurnRead]:
    user_message, assistant_message = await service.send_message(
        access.document,
        vector_index_id,
        conversation_id,
        payload,
        actor_id=access.membership.user_id,
    )
    return SuccessResponse(
        data=MessageTurnRead(
            user_message=MessageRead.model_validate(user_message),
            assistant_message=MessageRead.model_validate(assistant_message),
        ),
        request_id=_request_id(request),
    )


@router.get(f"{_CONVERSATIONS_PATH}/{{conversation_id}}/export")
async def export_conversation(
    vector_index_id: uuid.UUID,
    conversation_id: uuid.UUID,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ConversationService = Depends(get_conversation_service),
) -> PlainTextResponse:
    conversation = await service.get_conversation(
        access.document.id, vector_index_id, conversation_id
    )
    messages = await service.list_messages(access.document.id, vector_index_id, conversation_id)
    lines = [f"# {conversation.title or 'Conversation'}", ""]
    for message in messages:
        speaker = "User" if message.role.value == "user" else "Assistant"
        lines.append(f"**{speaker}:** {message.content}")
        lines.append("")
    return PlainTextResponse("\n".join(lines), media_type="text/markdown")


@router.get(
    "/repositories/{repository_id}/conversation-memory",
    response_model=SuccessResponse[ConversationMemoryRead],
)
async def get_conversation_memory(
    repository_id: uuid.UUID,
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.VIEWER)),
    service: MemoryService = Depends(get_memory_service),
) -> SuccessResponse[ConversationMemoryRead]:
    memory = await service.get_or_create(membership.user_id, repository_id)
    return SuccessResponse(
        data=ConversationMemoryRead.model_validate(memory), request_id=_request_id(request)
    )


@router.patch(
    "/repositories/{repository_id}/conversation-memory",
    response_model=SuccessResponse[ConversationMemoryRead],
)
async def update_conversation_memory(
    repository_id: uuid.UUID,
    payload: UpdateConversationMemoryRequest,
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.VIEWER)),
    service: MemoryService = Depends(get_memory_service),
) -> SuccessResponse[ConversationMemoryRead]:
    memory = await service.update(membership.user_id, repository_id, payload)
    return SuccessResponse(
        data=ConversationMemoryRead.model_validate(memory), request_id=_request_id(request)
    )
