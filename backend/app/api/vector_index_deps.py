"""DI wiring for vector index routes. Nested under document, chunk set,
and embedding version in the URL — RBAC reuses `require_document_role`
directly, same reasoning as chunk_deps.py/embedding_deps.py.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chunk_deps import get_chunk_set_repository
from app.api.deps import get_audit_log_repository
from app.api.embedding_deps import get_embedding_version_repository
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.chunk_repository import ChunkSetRepository
from app.repositories.embedding_repository import EmbeddingVersionRepository
from app.repositories.vector_index_repository import VectorIndexRepository
from app.services.vector_index_service import VectorIndexService


def get_vector_index_repository(db: AsyncSession = Depends(get_db)) -> VectorIndexRepository:
    return VectorIndexRepository(db)


def get_vector_index_service(
    vector_index_repository: VectorIndexRepository = Depends(get_vector_index_repository),
    embedding_version_repository: EmbeddingVersionRepository = Depends(
        get_embedding_version_repository
    ),
    chunk_set_repository: ChunkSetRepository = Depends(get_chunk_set_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> VectorIndexService:
    return VectorIndexService(
        vector_index_repository,
        embedding_version_repository,
        chunk_set_repository,
        audit_log_repository,
    )
