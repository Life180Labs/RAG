"""Vector index read/create/delete business logic (docs/05-task.md
Phase 8). Index build and delete always run in `index_worker` — this
service only records intent (audit log) and validates ownership; the
controller schedules the actual enqueue via `BackgroundTasks` so it only
fires after this request's transaction commits, mirroring Phases 6-7.

Unlike chunk sets and embedding versions (whose data lives entirely in
this app's own Postgres), a vector index's actual vectors may live in an
external store (Qdrant, Chroma, Pinecone) — so delete is enqueue-only
here too, never a synchronous ORM delete, since removing only our
tracking row would silently orphan data in that external store.
"""

import uuid

from app.core.exceptions import NotFoundError
from app.models.audit_log import AuditLog
from app.models.vector_index import VectorIndex
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.chunk_repository import ChunkSetRepository
from app.repositories.embedding_repository import EmbeddingVersionRepository
from app.repositories.vector_index_repository import VectorIndexRepository


class VectorIndexService:
    def __init__(
        self,
        vector_index_repository: VectorIndexRepository,
        embedding_version_repository: EmbeddingVersionRepository,
        chunk_set_repository: ChunkSetRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.vector_indexes = vector_index_repository
        self.embedding_versions = embedding_version_repository
        self.chunk_sets = chunk_set_repository
        self.audit_logs = audit_log_repository

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def _get_embedding_version_for_chunk_set(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID, embedding_version_id: uuid.UUID
    ):
        chunk_set = await self.chunk_sets.get_by_id(chunk_set_id)
        if chunk_set is None or chunk_set.document_id != document_id:
            raise NotFoundError("Chunk set not found.", code="CHUNK_SET_NOT_FOUND")
        version = await self.embedding_versions.get_by_id(embedding_version_id)
        if version is None or version.chunk_set_id != chunk_set_id:
            raise NotFoundError("Embedding version not found.", code="EMBEDDING_VERSION_NOT_FOUND")
        return version

    async def list_vector_indexes(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID, embedding_version_id: uuid.UUID
    ) -> list[VectorIndex]:
        await self._get_embedding_version_for_chunk_set(
            document_id, chunk_set_id, embedding_version_id
        )
        return await self.vector_indexes.list_by_embedding_version(embedding_version_id)

    async def get_vector_index(
        self,
        document_id: uuid.UUID,
        chunk_set_id: uuid.UUID,
        embedding_version_id: uuid.UUID,
        vector_index_id: uuid.UUID,
    ) -> VectorIndex:
        await self._get_embedding_version_for_chunk_set(
            document_id, chunk_set_id, embedding_version_id
        )
        index = await self.vector_indexes.get_by_id(vector_index_id)
        if index is None or index.embedding_version_id != embedding_version_id:
            raise NotFoundError("Vector index not found.", code="VECTOR_INDEX_NOT_FOUND")
        return index

    async def request_create(
        self,
        document_id: uuid.UUID,
        chunk_set_id: uuid.UUID,
        embedding_version_id: uuid.UUID,
        provider: str,
        *,
        actor_id: uuid.UUID,
    ) -> None:
        await self._get_embedding_version_for_chunk_set(
            document_id, chunk_set_id, embedding_version_id
        )
        await self._record_audit(
            user_id=actor_id,
            action="vector_index.create_requested",
            resource=str(embedding_version_id),
        )

    async def request_delete(
        self,
        document_id: uuid.UUID,
        chunk_set_id: uuid.UUID,
        embedding_version_id: uuid.UUID,
        vector_index_id: uuid.UUID,
        *,
        actor_id: uuid.UUID,
    ) -> None:
        await self.get_vector_index(
            document_id, chunk_set_id, embedding_version_id, vector_index_id
        )
        await self._record_audit(
            user_id=actor_id, action="vector_index.delete_requested", resource=str(vector_index_id)
        )
