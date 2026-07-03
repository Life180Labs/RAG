"""Project endpoints.

Creating a project requires workspace ADMIN+; every other route
requires project-level membership.
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.tenancy_deps import get_project_service, require_project_role, require_workspace_role
from app.models.membership import MemberRole
from app.models.project import ProjectMember
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.common import SuccessResponse
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(tags=["projects"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post("/workspaces/{workspace_id}/projects", response_model=SuccessResponse[ProjectRead])
async def create_project(
    payload: ProjectCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    membership: WorkspaceMember = Depends(require_workspace_role(MemberRole.ADMIN)),
    service: ProjectService = Depends(get_project_service),
) -> SuccessResponse[ProjectRead]:
    project = await service.create(
        workspace_id=membership.workspace_id,
        creator_id=current_user.id,
        name=payload.name,
        slug=payload.slug,
    )
    return SuccessResponse(
        data=ProjectRead.model_validate(project), request_id=_request_id(request)
    )


@router.get(
    "/workspaces/{workspace_id}/projects", response_model=SuccessResponse[list[ProjectRead]]
)
async def list_projects(
    request: Request,
    membership: WorkspaceMember = Depends(require_workspace_role(MemberRole.VIEWER)),
    service: ProjectService = Depends(get_project_service),
) -> SuccessResponse[list[ProjectRead]]:
    projects = await service.list_by_workspace(membership.workspace_id)
    return SuccessResponse(
        data=[ProjectRead.model_validate(p) for p in projects], request_id=_request_id(request)
    )


@router.get("/projects/{project_id}", response_model=SuccessResponse[ProjectRead])
async def get_project(
    request: Request,
    membership: ProjectMember = Depends(require_project_role(MemberRole.VIEWER)),
    service: ProjectService = Depends(get_project_service),
) -> SuccessResponse[ProjectRead]:
    project = await service.projects.get_active_by_id(membership.project_id)
    return SuccessResponse(
        data=ProjectRead.model_validate(project), request_id=_request_id(request)
    )


@router.patch("/projects/{project_id}", response_model=SuccessResponse[ProjectRead])
async def update_project(
    payload: ProjectUpdate,
    request: Request,
    membership: ProjectMember = Depends(require_project_role(MemberRole.ADMIN)),
    service: ProjectService = Depends(get_project_service),
) -> SuccessResponse[ProjectRead]:
    project = await service.projects.get_active_by_id(membership.project_id)
    updated = await service.update(project, name=payload.name, actor_id=membership.user_id)
    return SuccessResponse(
        data=ProjectRead.model_validate(updated), request_id=_request_id(request)
    )


@router.post("/projects/{project_id}/archive", response_model=SuccessResponse[ProjectRead])
async def archive_project(
    request: Request,
    membership: ProjectMember = Depends(require_project_role(MemberRole.ADMIN)),
    service: ProjectService = Depends(get_project_service),
) -> SuccessResponse[ProjectRead]:
    project = await service.projects.get_active_by_id(membership.project_id)
    archived = await service.archive(project, actor_id=membership.user_id)
    return SuccessResponse(
        data=ProjectRead.model_validate(archived), request_id=_request_id(request)
    )


@router.post("/projects/{project_id}/restore", response_model=SuccessResponse[ProjectRead])
async def restore_project(
    request: Request,
    membership: ProjectMember = Depends(require_project_role(MemberRole.ADMIN)),
    service: ProjectService = Depends(get_project_service),
) -> SuccessResponse[ProjectRead]:
    project = await service.projects.get_active_by_id(membership.project_id)
    restored = await service.restore(project, actor_id=membership.user_id)
    return SuccessResponse(
        data=ProjectRead.model_validate(restored), request_id=_request_id(request)
    )


@router.delete("/projects/{project_id}", response_model=SuccessResponse[dict])
async def delete_project(
    request: Request,
    membership: ProjectMember = Depends(require_project_role(MemberRole.OWNER)),
    service: ProjectService = Depends(get_project_service),
) -> SuccessResponse[dict]:
    project = await service.projects.get_active_by_id(membership.project_id)
    await service.soft_delete(project, actor_id=membership.user_id)
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))
