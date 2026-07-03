"""Repository endpoints.

Creating a repository requires project ADMIN+; every other route
requires repository-level membership (same explicit-membership pattern
as workspaces/projects — see docs/03-database.md section 6).
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_current_user
from app.api.tenancy_deps import (
    get_repository_service,
    require_project_role,
    require_repository_role,
)
from app.models.membership import MemberRole
from app.models.project import ProjectMember
from app.models.repository import RepositoryMember
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.repository import (
    RepositoryActivityEntry,
    RepositoryCreate,
    RepositoryRead,
    RepositorySettingsUpdate,
    RepositoryUpdate,
)
from app.services.repository_service import RepositoryService

router = APIRouter(tags=["repositories"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(
    "/projects/{project_id}/repositories", response_model=SuccessResponse[RepositoryRead]
)
async def create_repository(
    payload: RepositoryCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    membership: ProjectMember = Depends(require_project_role(MemberRole.ADMIN)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[RepositoryRead]:
    repository = await service.create(
        project_id=membership.project_id,
        creator_id=current_user.id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )
    return SuccessResponse(
        data=RepositoryRead.model_validate(repository), request_id=_request_id(request)
    )


@router.get(
    "/projects/{project_id}/repositories", response_model=SuccessResponse[list[RepositoryRead]]
)
async def list_repositories(
    request: Request,
    membership: ProjectMember = Depends(require_project_role(MemberRole.VIEWER)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[list[RepositoryRead]]:
    repositories = await service.list_by_project(membership.project_id)
    return SuccessResponse(
        data=[RepositoryRead.model_validate(r) for r in repositories],
        request_id=_request_id(request),
    )


@router.get(
    "/projects/{project_id}/repositories/search",
    response_model=SuccessResponse[list[RepositoryRead]],
)
async def search_repositories(
    request: Request,
    q: str = Query(..., min_length=1),
    membership: ProjectMember = Depends(require_project_role(MemberRole.VIEWER)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[list[RepositoryRead]]:
    repositories = await service.search(membership.project_id, q)
    return SuccessResponse(
        data=[RepositoryRead.model_validate(r) for r in repositories],
        request_id=_request_id(request),
    )


@router.get("/repositories/{repository_id}", response_model=SuccessResponse[RepositoryRead])
async def get_repository(
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.VIEWER)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[RepositoryRead]:
    repository = await service.repositories.get_active_by_id(membership.repository_id)
    return SuccessResponse(
        data=RepositoryRead.model_validate(repository), request_id=_request_id(request)
    )


@router.patch("/repositories/{repository_id}", response_model=SuccessResponse[RepositoryRead])
async def update_repository(
    payload: RepositoryUpdate,
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.ADMIN)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[RepositoryRead]:
    repository = await service.repositories.get_active_by_id(membership.repository_id)
    updated = await service.update(
        repository,
        name=payload.name,
        description=payload.description,
        actor_id=membership.user_id,
    )
    return SuccessResponse(
        data=RepositoryRead.model_validate(updated), request_id=_request_id(request)
    )


@router.patch(
    "/repositories/{repository_id}/settings", response_model=SuccessResponse[RepositoryRead]
)
async def update_repository_settings(
    payload: RepositorySettingsUpdate,
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.ADMIN)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[RepositoryRead]:
    repository = await service.repositories.get_active_by_id(membership.repository_id)
    updated = await service.update_settings(
        repository,
        default_chunk_strategy=payload.default_chunk_strategy,
        default_embedding_model=payload.default_embedding_model,
        default_retriever=payload.default_retriever,
        default_reranker=payload.default_reranker,
        default_prompt_version=payload.default_prompt_version,
        actor_id=membership.user_id,
    )
    return SuccessResponse(
        data=RepositoryRead.model_validate(updated), request_id=_request_id(request)
    )


@router.post(
    "/repositories/{repository_id}/archive", response_model=SuccessResponse[RepositoryRead]
)
async def archive_repository(
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.ADMIN)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[RepositoryRead]:
    repository = await service.repositories.get_active_by_id(membership.repository_id)
    archived = await service.archive(repository, actor_id=membership.user_id)
    return SuccessResponse(
        data=RepositoryRead.model_validate(archived), request_id=_request_id(request)
    )


@router.post(
    "/repositories/{repository_id}/restore", response_model=SuccessResponse[RepositoryRead]
)
async def restore_repository(
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.ADMIN)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[RepositoryRead]:
    repository = await service.repositories.get_active_by_id(membership.repository_id)
    restored = await service.restore(repository, actor_id=membership.user_id)
    return SuccessResponse(
        data=RepositoryRead.model_validate(restored), request_id=_request_id(request)
    )


@router.delete("/repositories/{repository_id}", response_model=SuccessResponse[dict])
async def delete_repository(
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.OWNER)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[dict]:
    repository = await service.repositories.get_active_by_id(membership.repository_id)
    await service.soft_delete(repository, actor_id=membership.user_id)
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))


@router.get(
    "/repositories/{repository_id}/activity",
    response_model=SuccessResponse[list[RepositoryActivityEntry]],
)
async def repository_activity(
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.VIEWER)),
    service: RepositoryService = Depends(get_repository_service),
) -> SuccessResponse[list[RepositoryActivityEntry]]:
    entries = await service.activity(membership.repository_id)
    return SuccessResponse(
        data=[RepositoryActivityEntry.model_validate(e) for e in entries],
        request_id=_request_id(request),
    )
