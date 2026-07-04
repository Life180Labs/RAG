"""DI wiring for retrieval routes. Nested under document and vector index
— RBAC reuses `require_document_role` directly, same reasoning as
chunk_deps.py/embedding_deps.py/vector_index_deps.py.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_repository
from app.api.vector_index_deps import get_vector_index_repository
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.retrieval_repository import RetrievalRepository, RetrievalResultRepository
from app.repositories.vector_index_repository import VectorIndexRepository
from app.services.retrieval_service import RetrievalService


def get_retrieval_repository(db: AsyncSession = Depends(get_db)) -> RetrievalRepository:
    return RetrievalRepository(db)


def get_retrieval_result_repository(
    db: AsyncSession = Depends(get_db),
) -> RetrievalResultRepository:
    return RetrievalResultRepository(db)


def get_retrieval_service(
    retrieval_repository: RetrievalRepository = Depends(get_retrieval_repository),
    retrieval_result_repository: RetrievalResultRepository = Depends(
        get_retrieval_result_repository
    ),
    vector_index_repository: VectorIndexRepository = Depends(get_vector_index_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> RetrievalService:
    return RetrievalService(
        retrieval_repository,
        retrieval_result_repository,
        vector_index_repository,
        audit_log_repository,
    )
