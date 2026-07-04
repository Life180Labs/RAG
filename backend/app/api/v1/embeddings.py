"""Embedding endpoints (docs/05-task.md Phase 7). Nested under their
document and chunk set; generation/regeneration require Document ADMIN+
(same create-requires-parent-ADMIN pattern as chunk generation), reads
require VIEWER+, delete requires ADMIN+.

Embedding generation always runs in `embedding_worker` — these routes
only enqueue it and read back whatever's already been persisted; there's
no synchronous "wait for the embeddings" response.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.api.document_deps import DocumentAccess, require_document_role
from app.api.embedding_deps import get_embedding_service
from app.core.task_queue import enqueue_embed_chunk_set
from app.models.membership import MemberRole
from app.schemas.common import SuccessResponse
from app.schemas.embedding import (
    EmbeddingRead,
    EmbeddingVersionComparison,
    EmbeddingVersionRead,
    GenerateEmbeddingsRequest,
)
from app.services.embedding_service import EmbeddingService

router = APIRouter(tags=["embeddings"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings",
    response_model=SuccessResponse[dict],
)
async def generate_embeddings(
    request: Request,
    chunk_set_id: uuid.UUID,
    payload: GenerateEmbeddingsRequest,
    background_tasks: BackgroundTasks,
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN)),
    service: EmbeddingService = Depends(get_embedding_service),
) -> SuccessResponse[dict]:
    await service.request_generation(
        access.document.id, chunk_set_id, payload.provider, actor_id=access.membership.user_id
    )
    background_tasks.add_task(
        enqueue_embed_chunk_set, str(chunk_set_id), payload.provider, payload.model
    )
    return SuccessResponse(
        data={"enqueued": True, "provider": payload.provider, "model": payload.model},
        request_id=_request_id(request),
    )


@router.get(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings",
    response_model=SuccessResponse[list[EmbeddingVersionRead]],
)
async def list_embedding_versions(
    request: Request,
    chunk_set_id: uuid.UUID,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: EmbeddingService = Depends(get_embedding_service),
) -> SuccessResponse[list[EmbeddingVersionRead]]:
    versions = await service.list_embedding_versions(access.document.id, chunk_set_id)
    return SuccessResponse(
        data=[EmbeddingVersionRead.model_validate(v) for v in versions],
        request_id=_request_id(request),
    )


@router.get(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/compare",
    response_model=SuccessResponse[EmbeddingVersionComparison],
)
async def compare_embedding_versions(
    request: Request,
    chunk_set_id: uuid.UUID,
    provider_a: str = Query(...),
    provider_b: str = Query(...),
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: EmbeddingService = Depends(get_embedding_service),
) -> SuccessResponse[EmbeddingVersionComparison]:
    version_a, embeddings_a, version_b, embeddings_b = await service.compare(
        access.document.id, chunk_set_id, provider_a, provider_b
    )
    return SuccessResponse(
        data=EmbeddingVersionComparison(
            version_a=EmbeddingVersionRead.model_validate(version_a),
            embeddings_a=[EmbeddingRead.model_validate(e) for e in embeddings_a],
            version_b=EmbeddingVersionRead.model_validate(version_b),
            embeddings_b=[EmbeddingRead.model_validate(e) for e in embeddings_b],
        ),
        request_id=_request_id(request),
    )


@router.get(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}/vectors",
    response_model=SuccessResponse[list[EmbeddingRead]],
)
async def list_embeddings(
    request: Request,
    chunk_set_id: uuid.UUID,
    embedding_version_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: EmbeddingService = Depends(get_embedding_service),
) -> SuccessResponse[list[EmbeddingRead]]:
    _version, embeddings = await service.list_embeddings(
        access.document.id, chunk_set_id, embedding_version_id, limit=limit, offset=offset
    )
    return SuccessResponse(
        data=[EmbeddingRead.model_validate(e) for e in embeddings], request_id=_request_id(request)
    )


@router.delete(
    "/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{embedding_version_id}",
    response_model=SuccessResponse[dict],
)
async def delete_embedding_version(
    request: Request,
    chunk_set_id: uuid.UUID,
    embedding_version_id: uuid.UUID,
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN)),
    service: EmbeddingService = Depends(get_embedding_service),
) -> SuccessResponse[dict]:
    await service.delete_embedding_version(
        access.document.id,
        chunk_set_id,
        embedding_version_id,
        actor_id=access.membership.user_id,
    )
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))
