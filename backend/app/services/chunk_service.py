"""Chunk read/comparison/regeneration business logic (docs/05-task.md
Phase 6). Chunk generation itself always runs in `chunk_worker` — this
service only records intent (audit log) and validates ownership; the
controller schedules the actual enqueue via `BackgroundTasks` so it only
fires after this request's transaction commits (same reasoning as
Phase 5's `enqueue_finalize_upload` timing fix).
"""

import uuid

from app.core.exceptions import NotFoundError
from app.models.audit_log import AuditLog
from app.models.chunk import Chunk, DocumentChunkSet
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.chunk_repository import ChunkRepository, ChunkSetRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.repository_repository import RepositoryRepository


class ChunkService:
    def __init__(
        self,
        chunk_set_repository: ChunkSetRepository,
        chunk_repository: ChunkRepository,
        document_repository: DocumentRepository,
        repository_repository: RepositoryRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.chunk_sets = chunk_set_repository
        self.chunks = chunk_repository
        self.documents = document_repository
        self.repositories = repository_repository
        self.audit_logs = audit_log_repository

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def list_chunk_sets(self, document_id: uuid.UUID) -> list[DocumentChunkSet]:
        return await self.chunk_sets.list_by_document(document_id)

    async def get_chunk_set_for_document(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID
    ) -> DocumentChunkSet:
        chunk_set = await self.chunk_sets.get_by_id(chunk_set_id)
        if chunk_set is None or chunk_set.document_id != document_id:
            raise NotFoundError("Chunk set not found.", code="CHUNK_SET_NOT_FOUND")
        return chunk_set

    async def list_chunks(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID, *, limit: int = 100, offset: int = 0
    ) -> tuple[DocumentChunkSet, list[Chunk]]:
        chunk_set = await self.get_chunk_set_for_document(document_id, chunk_set_id)
        chunks = await self.chunks.list_by_chunk_set(chunk_set_id, limit=limit, offset=offset)
        return chunk_set, chunks

    async def compare(
        self, document_id: uuid.UUID, strategy_a: str, strategy_b: str
    ) -> tuple[DocumentChunkSet, list[Chunk], DocumentChunkSet, list[Chunk]]:
        set_a = await self.chunk_sets.get_by_document_and_strategy(document_id, strategy_a)
        set_b = await self.chunk_sets.get_by_document_and_strategy(document_id, strategy_b)
        if set_a is None or set_b is None:
            raise NotFoundError(
                "Both strategies must have already been generated for this document to compare "
                "them.",
                code="CHUNK_SET_NOT_FOUND",
            )
        chunks_a = await self.chunks.list_by_chunk_set(set_a.id, limit=1000)
        chunks_b = await self.chunks.list_by_chunk_set(set_b.id, limit=1000)
        return set_a, chunks_a, set_b, chunks_b

    async def request_generation(
        self, document_id: uuid.UUID, strategy: str, *, actor_id: uuid.UUID
    ) -> None:
        await self._record_audit(
            user_id=actor_id, action="chunk_set.generate_requested", resource=str(document_id)
        )

    async def delete_chunk_set(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID, *, actor_id: uuid.UUID
    ) -> None:
        chunk_set = await self.get_chunk_set_for_document(document_id, chunk_set_id)

        document = await self.documents.get_active_by_id(document_id)
        if document is not None:
            repository = await self.repositories.get_active_by_id(document.repository_id)
            if repository is not None:
                repository.chunk_count = max(0, repository.chunk_count - chunk_set.chunk_count)

        await self.chunk_sets.delete(chunk_set)
        await self._record_audit(
            user_id=actor_id, action="chunk_set.delete", resource=str(chunk_set_id)
        )
