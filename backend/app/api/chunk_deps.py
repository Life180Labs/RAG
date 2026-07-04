"""DI wiring for chunk routes. Chunks are nested under their document in
the URL (`/documents/{document_id}/chunk-sets/...`), so RBAC reuses
`require_document_role` directly rather than a separate chunk-specific
membership dependency — the document_id is already right there in the
path.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_repository
from app.api.document_deps import get_document_repository
from app.api.tenancy_deps import get_repository_repository
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.chunk_repository import ChunkRepository, ChunkSetRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.repository_repository import RepositoryRepository
from app.services.chunk_service import ChunkService


def get_chunk_set_repository(db: AsyncSession = Depends(get_db)) -> ChunkSetRepository:
    return ChunkSetRepository(db)


def get_chunk_repository(db: AsyncSession = Depends(get_db)) -> ChunkRepository:
    return ChunkRepository(db)


def get_chunk_service(
    chunk_set_repository: ChunkSetRepository = Depends(get_chunk_set_repository),
    chunk_repository: ChunkRepository = Depends(get_chunk_repository),
    document_repository: DocumentRepository = Depends(get_document_repository),
    repository_repository: RepositoryRepository = Depends(get_repository_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> ChunkService:
    return ChunkService(
        chunk_set_repository,
        chunk_repository,
        document_repository,
        repository_repository,
        audit_log_repository,
    )
