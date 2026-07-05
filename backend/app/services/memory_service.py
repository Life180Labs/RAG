"""Long-Term Memory (docs/05-task.md Phase 16; docs/02-architecture.md
section 95): persisted per `(user, repository)`, across conversations —
unlike `ConversationSummary`/short-term memory, which lives and dies
with one conversation.

"Frequently Accessed Repositories" is intentionally not a stored field
on `ConversationMemory` — it's derived by counting `conversations` grouped
by repository for that user, the same "query the source data instead of
caching a redundant counter" choice this codebase already made for, e.g.,
`Repository.document_count` (Phase 4, populated for real — this one
isn't even stored at all, since nothing else needs a persisted counter).
"""

import uuid

from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, ConversationMemory
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.conversation_repository import ConversationMemoryRepository
from app.schemas.conversation import UpdateConversationMemoryRequest


class MemoryService:
    def __init__(
        self,
        memory_repository: ConversationMemoryRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.memory = memory_repository
        self.audit_logs = audit_log_repository

    async def get_or_create(
        self, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> ConversationMemory:
        memory = await self.memory.get_for_user_repository(user_id, repository_id)
        if memory is not None:
            return memory
        return await self.memory.add(
            ConversationMemory(user_id=user_id, repository_id=repository_id)
        )

    async def update(
        self,
        user_id: uuid.UUID,
        repository_id: uuid.UUID,
        payload: UpdateConversationMemoryRequest,
    ) -> ConversationMemory:
        memory = await self.get_or_create(user_id, repository_id)
        if payload.custom_instructions is not None:
            memory.custom_instructions = payload.custom_instructions or None
        if payload.preferences is not None:
            memory.preferences = payload.preferences
        await self.audit_logs.add(
            AuditLog(
                user_id=user_id,
                action="conversation_memory.update",
                resource=str(memory.id),
                result="success",
            )
        )
        return memory

    async def frequently_accessed_repositories(
        self, user_id: uuid.UUID, limit: int = 5
    ) -> list[tuple[uuid.UUID, int]]:
        result = await self.memory.session.execute(
            select(Conversation.repository_id, func.count(Conversation.id))
            .where(Conversation.created_by == user_id)
            .group_by(Conversation.repository_id)
            .order_by(func.count(Conversation.id).desc())
            .limit(limit)
        )
        return [(row[0], row[1]) for row in result.all()]
