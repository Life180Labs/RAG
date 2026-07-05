"""Retrieval endpoints (docs/05-task.md Phase 9). Nested under document
and vector index; create requires Document VIEWER+ (running a search is
a read-oriented action, unlike building/deleting an index), reads
require VIEWER+.

Creating a retrieval synchronously inserts its row (status=PENDING) —
see retrieval_service.py's docstring for why this differs from Phase
8's enqueue-only vector index create — then enqueues
`retrieval_worker.execute_retrieval` to actually run the search.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.api.document_deps import DocumentAccess, require_document_role
from app.api.retrieval_deps import get_retrieval_service
from app.core.task_queue import enqueue_execute_retrieval
from app.models.membership import MemberRole
from app.schemas.common import SuccessResponse
from app.schemas.retrieval import CreateRetrievalRequest, RetrievalRead, RetrievalResultRead
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["retrievals"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(
    "/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
    response_model=SuccessResponse[RetrievalRead],
)
async def create_retrieval(
    request: Request,
    vector_index_id: uuid.UUID,
    payload: CreateRetrievalRequest,
    background_tasks: BackgroundTasks,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: RetrievalService = Depends(get_retrieval_service),
) -> SuccessResponse[RetrievalRead]:
    retrieval = await service.create_retrieval(
        access.document.id, vector_index_id, payload, actor_id=access.membership.user_id
    )
    background_tasks.add_task(enqueue_execute_retrieval, str(retrieval.id))
    return SuccessResponse(
        data=RetrievalRead.model_validate(retrieval), request_id=_request_id(request)
    )


@router.get(
    "/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
    response_model=SuccessResponse[list[RetrievalRead]],
)
async def list_retrievals(
    request: Request,
    vector_index_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: RetrievalService = Depends(get_retrieval_service),
) -> SuccessResponse[list[RetrievalRead]]:
    retrievals = await service.list_retrievals(access.document.id, vector_index_id, limit, offset)
    return SuccessResponse(
        data=[RetrievalRead.model_validate(r) for r in retrievals], request_id=_request_id(request)
    )


@router.get(
    "/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals/{retrieval_id}",
    response_model=SuccessResponse[RetrievalRead],
)
async def get_retrieval(
    request: Request,
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: RetrievalService = Depends(get_retrieval_service),
) -> SuccessResponse[RetrievalRead]:
    retrieval = await service.get_retrieval(access.document.id, vector_index_id, retrieval_id)
    return SuccessResponse(
        data=RetrievalRead.model_validate(retrieval), request_id=_request_id(request)
    )


@router.get(
    "/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals/{retrieval_id}/results",
    response_model=SuccessResponse[list[RetrievalResultRead]],
)
async def get_retrieval_results(
    request: Request,
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: RetrievalService = Depends(get_retrieval_service),
) -> SuccessResponse[list[RetrievalResultRead]]:
    rows = await service.get_results(access.document.id, vector_index_id, retrieval_id)
    data = [
        RetrievalResultRead(
            id=result.id,
            chunk_id=result.chunk_id,
            rank=result.rank,
            score=result.score,
            dense_score=result.dense_score,
            sparse_score=result.sparse_score,
            compressed_text=result.compressed_text,
            rerank_score=result.rerank_score,
            chunk_text=chunk.text,
            chunk_heading=chunk.heading,
            chunk_page=chunk.page,
        )
        for result, chunk in rows
    ]
    return SuccessResponse(data=data, request_id=_request_id(request))
