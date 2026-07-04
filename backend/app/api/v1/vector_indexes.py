"""Vector index endpoints (docs/05-task.md Phase 8). Nested under
document, chunk set, and embedding version; create/delete require
Document ADMIN+, reads require VIEWER+.

Both index build and delete always run in `index_worker` — these routes
only enqueue and read back whatever's already persisted. Delete in
particular never synchronously removes the tracking row here (see
vector_index_service.py) since the actual vectors may live in an
external store that only the worker knows how to reach.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.api.document_deps import DocumentAccess, require_document_role
from app.api.vector_index_deps import get_vector_index_service
from app.core.task_queue import enqueue_build_index, enqueue_delete_index
from app.models.membership import MemberRole
from app.schemas.common import SuccessResponse
from app.schemas.vector_index import CreateVectorIndexRequest, VectorIndexRead
from app.services.vector_index_service import VectorIndexService

router = APIRouter(tags=["vector-indexes"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}/index",
    response_model=SuccessResponse[dict],
)
async def create_or_rebuild_index(
    request: Request,
    chunk_set_id: uuid.UUID,
    embedding_version_id: uuid.UUID,
    payload: CreateVectorIndexRequest,
    background_tasks: BackgroundTasks,
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN)),
    service: VectorIndexService = Depends(get_vector_index_service),
) -> SuccessResponse[dict]:
    await service.request_create(
        access.document.id,
        chunk_set_id,
        embedding_version_id,
        payload.provider,
        actor_id=access.membership.user_id,
    )
    background_tasks.add_task(
        enqueue_build_index, str(embedding_version_id), payload.provider, payload.index_type
    )
    return SuccessResponse(
        data={
            "enqueued": True,
            "provider": payload.provider,
            "index_type": payload.index_type,
        },
        request_id=_request_id(request),
    )


@router.get(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}/index",
    response_model=SuccessResponse[list[VectorIndexRead]],
)
async def list_vector_indexes(
    request: Request,
    chunk_set_id: uuid.UUID,
    embedding_version_id: uuid.UUID,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: VectorIndexService = Depends(get_vector_index_service),
) -> SuccessResponse[list[VectorIndexRead]]:
    indexes = await service.list_vector_indexes(
        access.document.id, chunk_set_id, embedding_version_id
    )
    return SuccessResponse(
        data=[VectorIndexRead.model_validate(i) for i in indexes], request_id=_request_id(request)
    )


@router.get(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}"
    "/index/{vector_index_id}",
    response_model=SuccessResponse[VectorIndexRead],
)
async def get_vector_index(
    request: Request,
    chunk_set_id: uuid.UUID,
    embedding_version_id: uuid.UUID,
    vector_index_id: uuid.UUID,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: VectorIndexService = Depends(get_vector_index_service),
) -> SuccessResponse[VectorIndexRead]:
    index = await service.get_vector_index(
        access.document.id, chunk_set_id, embedding_version_id, vector_index_id
    )
    return SuccessResponse(
        data=VectorIndexRead.model_validate(index), request_id=_request_id(request)
    )


@router.delete(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}"
    "/index/{vector_index_id}",
    response_model=SuccessResponse[dict],
)
async def delete_vector_index(
    request: Request,
    chunk_set_id: uuid.UUID,
    embedding_version_id: uuid.UUID,
    vector_index_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN)),
    service: VectorIndexService = Depends(get_vector_index_service),
) -> SuccessResponse[dict]:
    await service.request_delete(
        access.document.id,
        chunk_set_id,
        embedding_version_id,
        vector_index_id,
        actor_id=access.membership.user_id,
    )
    background_tasks.add_task(enqueue_delete_index, str(vector_index_id))
    return SuccessResponse(data={"enqueued": True}, request_id=_request_id(request))
