"""Chunk endpoints (docs/05-task.md Phase 6). Nested under their
document; generation/regeneration require Document ADMIN+ (same
create-requires-parent-ADMIN pattern as uploads), reads require
VIEWER+, delete requires ADMIN+.

Chunk generation always runs in `chunk_worker` — these routes only
enqueue it and read back whatever's already been persisted; there's no
synchronous "wait for the chunks" response.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.api.chunk_deps import get_chunk_service
from app.api.document_deps import DocumentAccess, require_document_role
from app.core.task_queue import enqueue_chunk_document
from app.models.membership import MemberRole
from app.schemas.chunk import (
    ChunkRead,
    ChunkSetComparison,
    ChunkSetRead,
    GenerateChunksRequest,
)
from app.schemas.common import SuccessResponse
from app.services.chunk_service import ChunkService

router = APIRouter(tags=["chunks"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(
    "/documents/{document_id}/chunk-sets", response_model=SuccessResponse[dict]
)
async def generate_chunks(
    request: Request,
    payload: GenerateChunksRequest,
    background_tasks: BackgroundTasks,
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN)),
    service: ChunkService = Depends(get_chunk_service),
) -> SuccessResponse[dict]:
    await service.request_generation(
        access.document.id, payload.strategy, actor_id=access.membership.user_id
    )
    background_tasks.add_task(enqueue_chunk_document, str(access.document.id), payload.strategy)
    return SuccessResponse(
        data={"enqueued": True, "strategy": payload.strategy}, request_id=_request_id(request)
    )


@router.get(
    "/documents/{document_id}/chunk-sets", response_model=SuccessResponse[list[ChunkSetRead]]
)
async def list_chunk_sets(
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ChunkService = Depends(get_chunk_service),
) -> SuccessResponse[list[ChunkSetRead]]:
    chunk_sets = await service.list_chunk_sets(access.document.id)
    return SuccessResponse(
        data=[ChunkSetRead.model_validate(cs) for cs in chunk_sets],
        request_id=_request_id(request),
    )


@router.get(
    "/documents/{document_id}/chunk-sets/compare",
    response_model=SuccessResponse[ChunkSetComparison],
)
async def compare_chunk_sets(
    request: Request,
    strategy_a: str = Query(...),
    strategy_b: str = Query(...),
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ChunkService = Depends(get_chunk_service),
) -> SuccessResponse[ChunkSetComparison]:
    set_a, chunks_a, set_b, chunks_b = await service.compare(
        access.document.id, strategy_a, strategy_b
    )
    return SuccessResponse(
        data=ChunkSetComparison(
            strategy_a=ChunkSetRead.model_validate(set_a),
            chunks_a=[ChunkRead.model_validate(c) for c in chunks_a],
            strategy_b=ChunkSetRead.model_validate(set_b),
            chunks_b=[ChunkRead.model_validate(c) for c in chunks_b],
        ),
        request_id=_request_id(request),
    )


@router.get(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/chunks",
    response_model=SuccessResponse[list[ChunkRead]],
)
async def list_chunks(
    request: Request,
    chunk_set_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: ChunkService = Depends(get_chunk_service),
) -> SuccessResponse[list[ChunkRead]]:
    _chunk_set, chunks = await service.list_chunks(
        access.document.id, chunk_set_id, limit=limit, offset=offset
    )
    return SuccessResponse(
        data=[ChunkRead.model_validate(c) for c in chunks], request_id=_request_id(request)
    )


@router.delete(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}", response_model=SuccessResponse[dict]
)
async def delete_chunk_set(
    request: Request,
    chunk_set_id: uuid.UUID,
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN)),
    service: ChunkService = Depends(get_chunk_service),
) -> SuccessResponse[dict]:
    await service.delete_chunk_set(
        access.document.id, chunk_set_id, actor_id=access.membership.user_id
    )
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))
