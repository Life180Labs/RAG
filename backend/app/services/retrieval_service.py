"""Retrieval query business logic (docs/05-task.md Phase 9).

Unlike chunk/embedding/index rows (which only exist once the worker
upserts a computed result), a Retrieval represents a user's *request*
before any AI computation happens — the same shape as `Document` on
upload: the backend creates the row synchronously (status=PENDING) with
just the caller-supplied query parameters, then enqueues
`retrieval_worker.execute_retrieval(retrieval_id)`, which fills in the
actual search results and flips the row to COMPLETED/FAILED. This is why
retrieval creation is a plain repository `.add()` here rather than an
enqueue-only "request" method like Phase 8's vector index create.
"""

import uuid

from app.core.exceptions import NotFoundError
from app.models.audit_log import AuditLog
from app.models.retrieval import Retrieval, RetrievalResult, RetrievalStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.retrieval_repository import RetrievalRepository, RetrievalResultRepository
from app.repositories.vector_index_repository import VectorIndexRepository
from app.schemas.retrieval import CreateRetrievalRequest


class RetrievalService:
    def __init__(
        self,
        retrieval_repository: RetrievalRepository,
        retrieval_result_repository: RetrievalResultRepository,
        vector_index_repository: VectorIndexRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.retrievals = retrieval_repository
        self.retrieval_results = retrieval_result_repository
        self.vector_indexes = vector_index_repository
        self.audit_logs = audit_log_repository

    async def _get_vector_index(
        self, document_id: uuid.UUID, vector_index_id: uuid.UUID
    ):
        index = await self.vector_indexes.get_by_id(vector_index_id)
        if index is None or index.document_id != document_id:
            raise NotFoundError("Vector index not found.", code="VECTOR_INDEX_NOT_FOUND")
        return index

    async def create_retrieval(
        self,
        document_id: uuid.UUID,
        vector_index_id: uuid.UUID,
        payload: CreateRetrievalRequest,
        *,
        actor_id: uuid.UUID,
    ) -> Retrieval:
        await self._get_vector_index(document_id, vector_index_id)

        retrieval = await self.retrievals.add(
            Retrieval(
                vector_index_id=vector_index_id,
                document_id=document_id,
                query_text=payload.query_text,
                top_k=payload.top_k,
                score_threshold=payload.score_threshold,
                similarity_metric=payload.similarity_metric,
                metadata_filter=payload.metadata_filter,
                retrieval_mode=payload.retrieval_mode,
                fusion_method=payload.fusion_method,
                dense_weight=payload.dense_weight,
                sparse_weight=payload.sparse_weight,
                rrf_k=payload.rrf_k,
                status=RetrievalStatus.PENDING,
                created_by=actor_id,
            )
        )
        await self.audit_logs.add(
            AuditLog(
                user_id=actor_id,
                action="retrieval.created",
                resource=str(retrieval.id),
                result="success",
            )
        )
        return retrieval

    async def list_retrievals(
        self, document_id: uuid.UUID, vector_index_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Retrieval]:
        await self._get_vector_index(document_id, vector_index_id)
        return await self.retrievals.list_by_vector_index(vector_index_id, limit, offset)

    async def get_retrieval(
        self, document_id: uuid.UUID, vector_index_id: uuid.UUID, retrieval_id: uuid.UUID
    ) -> Retrieval:
        await self._get_vector_index(document_id, vector_index_id)
        retrieval = await self.retrievals.get_by_id(retrieval_id)
        if retrieval is None or retrieval.vector_index_id != vector_index_id:
            raise NotFoundError("Retrieval not found.", code="RETRIEVAL_NOT_FOUND")
        return retrieval

    async def get_results(
        self, document_id: uuid.UUID, vector_index_id: uuid.UUID, retrieval_id: uuid.UUID
    ) -> list[tuple[RetrievalResult, object]]:
        await self.get_retrieval(document_id, vector_index_id, retrieval_id)
        return await self.retrieval_results.list_with_chunks(retrieval_id)
