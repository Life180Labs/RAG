"""Workspace endpoints.

Creating a workspace requires organization ADMIN+; every other route
requires workspace-level membership (see docs/03-database.md section 6
for why organization role alone isn't sufficient here).
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.tenancy_deps import (
    get_workspace_service,
    require_organization_role,
    require_workspace_role,
)
from app.models.membership import MemberRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.common import SuccessResponse
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["workspaces"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(
    "/organizations/{organization_id}/workspaces", response_model=SuccessResponse[WorkspaceRead]
)
async def create_workspace(
    payload: WorkspaceCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> SuccessResponse[WorkspaceRead]:
    workspace = await service.create(
        organization_id=membership.organization_id,
        creator_id=current_user.id,
        name=payload.name,
        slug=payload.slug,
    )
    return SuccessResponse(
        data=WorkspaceRead.model_validate(workspace), request_id=_request_id(request)
    )


@router.get(
    "/organizations/{organization_id}/workspaces",
    response_model=SuccessResponse[list[WorkspaceRead]],
)
async def list_workspaces(
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.VIEWER)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> SuccessResponse[list[WorkspaceRead]]:
    workspaces = await service.list_by_organization(membership.organization_id)
    return SuccessResponse(
        data=[WorkspaceRead.model_validate(w) for w in workspaces], request_id=_request_id(request)
    )


@router.get("/workspaces/{workspace_id}", response_model=SuccessResponse[WorkspaceRead])
async def get_workspace(
    request: Request,
    membership: WorkspaceMember = Depends(require_workspace_role(MemberRole.VIEWER)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> SuccessResponse[WorkspaceRead]:
    workspace = await service.workspaces.get_active_by_id(membership.workspace_id)
    return SuccessResponse(
        data=WorkspaceRead.model_validate(workspace), request_id=_request_id(request)
    )


@router.patch("/workspaces/{workspace_id}", response_model=SuccessResponse[WorkspaceRead])
async def update_workspace(
    payload: WorkspaceUpdate,
    request: Request,
    membership: WorkspaceMember = Depends(require_workspace_role(MemberRole.ADMIN)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> SuccessResponse[WorkspaceRead]:
    workspace = await service.workspaces.get_active_by_id(membership.workspace_id)
    updated = await service.update(workspace, name=payload.name, actor_id=membership.user_id)
    return SuccessResponse(
        data=WorkspaceRead.model_validate(updated), request_id=_request_id(request)
    )


@router.post("/workspaces/{workspace_id}/archive", response_model=SuccessResponse[WorkspaceRead])
async def archive_workspace(
    request: Request,
    membership: WorkspaceMember = Depends(require_workspace_role(MemberRole.ADMIN)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> SuccessResponse[WorkspaceRead]:
    workspace = await service.workspaces.get_active_by_id(membership.workspace_id)
    archived = await service.archive(workspace, actor_id=membership.user_id)
    return SuccessResponse(
        data=WorkspaceRead.model_validate(archived), request_id=_request_id(request)
    )


@router.post("/workspaces/{workspace_id}/restore", response_model=SuccessResponse[WorkspaceRead])
async def restore_workspace(
    request: Request,
    membership: WorkspaceMember = Depends(require_workspace_role(MemberRole.ADMIN)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> SuccessResponse[WorkspaceRead]:
    workspace = await service.workspaces.get_active_by_id(membership.workspace_id)
    restored = await service.restore(workspace, actor_id=membership.user_id)
    return SuccessResponse(
        data=WorkspaceRead.model_validate(restored), request_id=_request_id(request)
    )


@router.delete("/workspaces/{workspace_id}", response_model=SuccessResponse[dict])
async def delete_workspace(
    request: Request,
    membership: WorkspaceMember = Depends(require_workspace_role(MemberRole.OWNER)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> SuccessResponse[dict]:
    workspace = await service.workspaces.get_active_by_id(membership.workspace_id)
    await service.soft_delete(workspace, actor_id=membership.user_id)
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))
