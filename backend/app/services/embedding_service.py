"""Embedding read/comparison/delete business logic (docs/05-task.md
Phase 7). Embedding generation itself always runs in `embedding_worker`
— this service only records intent (audit log) and validates ownership;
the controller schedules the actual enqueue via `BackgroundTasks` so it
only fires after this request's transaction commits, mirroring Phase 6's
chunk generation and Phase 5's `enqueue_finalize_upload` timing fix.
"""

import uuid

from app.core.exceptions import NotFoundError
from app.models.audit_log import AuditLog
from app.models.embedding import Embedding, EmbeddingVersion
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.chunk_repository import ChunkSetRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_repository import EmbeddingRepository, EmbeddingVersionRepository
from app.repositories.repository_repository import RepositoryRepository


class EmbeddingService:
    def __init__(
        self,
        embedding_version_repository: EmbeddingVersionRepository,
        embedding_repository: EmbeddingRepository,
        chunk_set_repository: ChunkSetRepository,
        document_repository: DocumentRepository,
        repository_repository: RepositoryRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.embedding_versions = embedding_version_repository
        self.embeddings = embedding_repository
        self.chunk_sets = chunk_set_repository
        self.documents = document_repository
        self.repositories = repository_repository
        self.audit_logs = audit_log_repository

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def _get_chunk_set_for_document(self, document_id: uuid.UUID, chunk_set_id: uuid.UUID):
        chunk_set = await self.chunk_sets.get_by_id(chunk_set_id)
        if chunk_set is None or chunk_set.document_id != document_id:
            raise NotFoundError("Chunk set not found.", code="CHUNK_SET_NOT_FOUND")
        return chunk_set

    async def list_embedding_versions(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID
    ) -> list[EmbeddingVersion]:
        await self._get_chunk_set_for_document(document_id, chunk_set_id)
        return await self.embedding_versions.list_by_chunk_set(chunk_set_id)

    async def get_embedding_version_for_chunk_set(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID, embedding_version_id: uuid.UUID
    ) -> EmbeddingVersion:
        await self._get_chunk_set_for_document(document_id, chunk_set_id)
        version = await self.embedding_versions.get_by_id(embedding_version_id)
        if version is None or version.chunk_set_id != chunk_set_id:
            raise NotFoundError("Embedding version not found.", code="EMBEDDING_VERSION_NOT_FOUND")
        return version

    async def list_embeddings(
        self,
        document_id: uuid.UUID,
        chunk_set_id: uuid.UUID,
        embedding_version_id: uuid.UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[EmbeddingVersion, list[Embedding]]:
        version = await self.get_embedding_version_for_chunk_set(
            document_id, chunk_set_id, embedding_version_id
        )
        embeddings = await self.embeddings.list_by_version(
            embedding_version_id, limit=limit, offset=offset
        )
        return version, embeddings

    async def compare(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID, provider_a: str, provider_b: str
    ) -> tuple[EmbeddingVersion, list[Embedding], EmbeddingVersion, list[Embedding]]:
        await self._get_chunk_set_for_document(document_id, chunk_set_id)
        version_a = await self.embedding_versions.get_by_chunk_set_and_provider(
            chunk_set_id, provider_a
        )
        version_b = await self.embedding_versions.get_by_chunk_set_and_provider(
            chunk_set_id, provider_b
        )
        if version_a is None or version_b is None:
            raise NotFoundError(
                "Both providers must have already been generated for this chunk set to compare "
                "them.",
                code="EMBEDDING_VERSION_NOT_FOUND",
            )
        embeddings_a = await self.embeddings.list_by_version(version_a.id, limit=1000)
        embeddings_b = await self.embeddings.list_by_version(version_b.id, limit=1000)
        return version_a, embeddings_a, version_b, embeddings_b

    async def request_generation(
        self, document_id: uuid.UUID, chunk_set_id: uuid.UUID, provider: str, *, actor_id: uuid.UUID
    ) -> None:
        await self._get_chunk_set_for_document(document_id, chunk_set_id)
        await self._record_audit(
            user_id=actor_id,
            action="embedding_version.generate_requested",
            resource=str(chunk_set_id),
        )

    async def delete_embedding_version(
        self,
        document_id: uuid.UUID,
        chunk_set_id: uuid.UUID,
        embedding_version_id: uuid.UUID,
        *,
        actor_id: uuid.UUID,
    ) -> None:
        version = await self.get_embedding_version_for_chunk_set(
            document_id, chunk_set_id, embedding_version_id
        )

        document = await self.documents.get_active_by_id(document_id)
        if document is not None:
            repository = await self.repositories.get_active_by_id(document.repository_id)
            if repository is not None:
                repository.embedding_count = max(
                    0, repository.embedding_count - version.embedding_count
                )

        await self.embedding_versions.delete(version)
        await self._record_audit(
            user_id=actor_id,
            action="embedding_version.delete",
            resource=str(embedding_version_id),
        )
