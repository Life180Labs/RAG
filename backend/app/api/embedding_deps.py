"""DI wiring for embedding routes. Embeddings are nested under their
document and chunk set in the URL
(`/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/...`),
so RBAC reuses `require_document_role` directly rather than a separate
embedding-specific membership dependency — the document_id is already
right there in the path.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chunk_deps import get_chunk_set_repository
from app.api.deps import get_audit_log_repository
from app.api.document_deps import get_document_repository
from app.api.tenancy_deps import get_repository_repository
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.chunk_repository import ChunkSetRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_repository import EmbeddingRepository, EmbeddingVersionRepository
from app.repositories.repository_repository import RepositoryRepository
from app.services.embedding_service import EmbeddingService


def get_embedding_version_repository(
    db: AsyncSession = Depends(get_db),
) -> EmbeddingVersionRepository:
    return EmbeddingVersionRepository(db)


def get_embedding_repository(db: AsyncSession = Depends(get_db)) -> EmbeddingRepository:
    return EmbeddingRepository(db)


def get_embedding_service(
    embedding_version_repository: EmbeddingVersionRepository = Depends(
        get_embedding_version_repository
    ),
    embedding_repository: EmbeddingRepository = Depends(get_embedding_repository),
    chunk_set_repository: ChunkSetRepository = Depends(get_chunk_set_repository),
    document_repository: DocumentRepository = Depends(get_document_repository),
    repository_repository: RepositoryRepository = Depends(get_repository_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> EmbeddingService:
    return EmbeddingService(
        embedding_version_repository,
        embedding_repository,
        chunk_set_repository,
        document_repository,
        repository_repository,
        audit_log_repository,
    )
