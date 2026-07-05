"""Prompt template + prompt endpoints (docs/05-task.md Phase 14).

Prompt templates are repository-scoped (docs/02-architecture.md section
79 — versions must coexist for experiment comparison), so they follow
the same create-requires-repository-ADMIN+/read-requires-VIEWER+ pattern
as `documents.py`. There is no PATCH/PUT for an existing version — POST
always creates a new version (see `prompt_template_service.py`).

Prompts are nested under a retrieval (document/vector-index/retrieval),
mirroring `retrievals.py`: building a prompt is a read-oriented action
over an already-completed retrieval, so it requires Document VIEWER+
like creating a retrieval does, not ADMIN+.

`list_prompt_templates` is also this app's Metadata/API Cache example
(docs/02-architecture.md section 148, Phase 17) — a real, frequently-hit
DB read (every Prompt Playground load) cached for
`metadata_cache_ttl_seconds` and explicitly invalidated by the two write
paths below (`create_prompt_template`/`archive_prompt_template`) rather
than left to expire stale.
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.document_deps import DocumentAccess, require_document_role
from app.api.prompt_deps import get_prompt_service, get_prompt_template_service
from app.api.tenancy_deps import require_repository_role
from app.core.cache.store import CacheStore
from app.core.config import get_settings
from app.models.membership import MemberRole
from app.models.repository import RepositoryMember
from app.schemas.common import SuccessResponse
from app.schemas.prompt import (
    CreatePromptRequest,
    CreatePromptTemplateRequest,
    PromptRead,
    PromptTemplateRead,
)
from app.services.prompt_service import PromptService
from app.services.prompt_template_service import PromptTemplateService

router = APIRouter(tags=["prompts"])

_PROMPT_TEMPLATES_CACHE_TYPE = "metadata"


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def _prompt_templates_cache_key(repository_id: uuid.UUID) -> str:
    return f"prompt-templates:{repository_id}"


@router.post(
    "/repositories/{repository_id}/prompt-templates",
    response_model=SuccessResponse[PromptTemplateRead],
)
async def create_prompt_template(
    payload: CreatePromptTemplateRequest,
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.ADMIN)),
    service: PromptTemplateService = Depends(get_prompt_template_service),
) -> SuccessResponse[PromptTemplateRead]:
    template = await service.create_version(
        repository_id=membership.repository_id,
        name=payload.name,
        system_prompt=payload.system_prompt,
        formatting_instructions=payload.formatting_instructions,
        output_schema=payload.output_schema,
        actor_id=membership.user_id,
    )
    settings = get_settings()
    if settings.cache_enabled:
        cache_store = CacheStore(_PROMPT_TEMPLATES_CACHE_TYPE, settings.metadata_cache_ttl_seconds)
        await cache_store.delete(_prompt_templates_cache_key(membership.repository_id))
    return SuccessResponse(
        data=PromptTemplateRead.model_validate(template), request_id=_request_id(request)
    )


@router.get(
    "/repositories/{repository_id}/prompt-templates",
    response_model=SuccessResponse[list[PromptTemplateRead]],
)
async def list_prompt_templates(
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.VIEWER)),
    service: PromptTemplateService = Depends(get_prompt_template_service),
) -> SuccessResponse[list[PromptTemplateRead]]:
    settings = get_settings()
    cache_store = CacheStore(_PROMPT_TEMPLATES_CACHE_TYPE, settings.metadata_cache_ttl_seconds)
    cache_key = _prompt_templates_cache_key(membership.repository_id)

    if settings.cache_enabled:
        cached = await cache_store.get(cache_key)
        if cached is not None:
            return SuccessResponse(
                data=[PromptTemplateRead.model_validate(d) for d in cached],
                request_id=_request_id(request),
            )

    templates = await service.list_by_repository(membership.repository_id)
    data = [PromptTemplateRead.model_validate(t) for t in templates]

    if settings.cache_enabled:
        await cache_store.set(cache_key, [d.model_dump(mode="json") for d in data])

    return SuccessResponse(data=data, request_id=_request_id(request))


@router.get(
    "/repositories/{repository_id}/prompt-templates/{name}/versions",
    response_model=SuccessResponse[list[PromptTemplateRead]],
)
async def list_prompt_template_versions(
    name: str,
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.VIEWER)),
    service: PromptTemplateService = Depends(get_prompt_template_service),
) -> SuccessResponse[list[PromptTemplateRead]]:
    versions = await service.list_versions(membership.repository_id, name)
    return SuccessResponse(
        data=[PromptTemplateRead.model_validate(v) for v in versions],
        request_id=_request_id(request),
    )


@router.get(
    "/repositories/{repository_id}/prompt-templates/{template_id}",
    response_model=SuccessResponse[PromptTemplateRead],
)
async def get_prompt_template(
    template_id: uuid.UUID,
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.VIEWER)),
    service: PromptTemplateService = Depends(get_prompt_template_service),
) -> SuccessResponse[PromptTemplateRead]:
    template = await service.get(membership.repository_id, template_id)
    return SuccessResponse(
        data=PromptTemplateRead.model_validate(template), request_id=_request_id(request)
    )


@router.post(
    "/repositories/{repository_id}/prompt-templates/{template_id}/archive",
    response_model=SuccessResponse[PromptTemplateRead],
)
async def archive_prompt_template(
    template_id: uuid.UUID,
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.ADMIN)),
    service: PromptTemplateService = Depends(get_prompt_template_service),
) -> SuccessResponse[PromptTemplateRead]:
    template = await service.set_active(
        membership.repository_id, template_id, is_active=False, actor_id=membership.user_id
    )
    settings = get_settings()
    if settings.cache_enabled:
        cache_store = CacheStore(_PROMPT_TEMPLATES_CACHE_TYPE, settings.metadata_cache_ttl_seconds)
        await cache_store.delete(_prompt_templates_cache_key(membership.repository_id))
    return SuccessResponse(
        data=PromptTemplateRead.model_validate(template), request_id=_request_id(request)
    )


@router.post(
    "/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals/{retrieval_id}/prompts",
    response_model=SuccessResponse[PromptRead],
)
async def build_prompt(
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    payload: CreatePromptRequest,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: PromptService = Depends(get_prompt_service),
) -> SuccessResponse[PromptRead]:
    prompt = await service.build_prompt(
        access.document,
        vector_index_id,
        retrieval_id,
        payload,
        actor_id=access.membership.user_id,
    )
    return SuccessResponse(data=PromptRead.model_validate(prompt), request_id=_request_id(request))


@router.get(
    "/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals/{retrieval_id}/prompts",
    response_model=SuccessResponse[list[PromptRead]],
)
async def list_prompts(
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: PromptService = Depends(get_prompt_service),
) -> SuccessResponse[list[PromptRead]]:
    prompts = await service.list_by_retrieval(access.document.id, vector_index_id, retrieval_id)
    return SuccessResponse(
        data=[PromptRead.model_validate(p) for p in prompts], request_id=_request_id(request)
    )


@router.get(
    "/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals/{retrieval_id}"
    "/prompts/{prompt_id}",
    response_model=SuccessResponse[PromptRead],
)
async def get_prompt(
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    prompt_id: uuid.UUID,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: PromptService = Depends(get_prompt_service),
) -> SuccessResponse[PromptRead]:
    prompt = await service.get(access.document.id, vector_index_id, retrieval_id, prompt_id)
    return SuccessResponse(data=PromptRead.model_validate(prompt), request_id=_request_id(request))
