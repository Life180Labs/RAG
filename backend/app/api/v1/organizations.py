"""Organization endpoints.

Creating an organization requires only authentication (any user can
start one and becomes its OWNER); every other route requires the
tenant-scoped RBAC dependency for that organization.
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.tenancy_deps import get_organization_service, require_organization_role
from app.models.membership import MemberRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.organization import OrganizationCreate, OrganizationRead, OrganizationUpdate
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post("", response_model=SuccessResponse[OrganizationRead])
async def create_organization(
    payload: OrganizationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: OrganizationService = Depends(get_organization_service),
) -> SuccessResponse[OrganizationRead]:
    organization = await service.create(
        owner_id=current_user.id, name=payload.name, slug=payload.slug
    )
    return SuccessResponse(
        data=OrganizationRead.model_validate(organization), request_id=_request_id(request)
    )


@router.get("", response_model=SuccessResponse[list[OrganizationRead]])
async def list_organizations(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: OrganizationService = Depends(get_organization_service),
) -> SuccessResponse[list[OrganizationRead]]:
    organizations = await service.list_for_user(current_user.id)
    return SuccessResponse(
        data=[OrganizationRead.model_validate(org) for org in organizations],
        request_id=_request_id(request),
    )


@router.get("/{organization_id}", response_model=SuccessResponse[OrganizationRead])
async def get_organization(
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.VIEWER)),
    service: OrganizationService = Depends(get_organization_service),
) -> SuccessResponse[OrganizationRead]:
    organization = await service.organizations.get_active_by_id(membership.organization_id)
    return SuccessResponse(
        data=OrganizationRead.model_validate(organization), request_id=_request_id(request)
    )


@router.patch("/{organization_id}", response_model=SuccessResponse[OrganizationRead])
async def update_organization(
    payload: OrganizationUpdate,
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: OrganizationService = Depends(get_organization_service),
) -> SuccessResponse[OrganizationRead]:
    organization = await service.organizations.get_active_by_id(membership.organization_id)
    updated = await service.update(organization, name=payload.name, actor_id=membership.user_id)
    return SuccessResponse(
        data=OrganizationRead.model_validate(updated), request_id=_request_id(request)
    )


@router.post("/{organization_id}/archive", response_model=SuccessResponse[OrganizationRead])
async def archive_organization(
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: OrganizationService = Depends(get_organization_service),
) -> SuccessResponse[OrganizationRead]:
    organization = await service.organizations.get_active_by_id(membership.organization_id)
    archived = await service.archive(organization, actor_id=membership.user_id)
    return SuccessResponse(
        data=OrganizationRead.model_validate(archived), request_id=_request_id(request)
    )


@router.post("/{organization_id}/restore", response_model=SuccessResponse[OrganizationRead])
async def restore_organization(
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: OrganizationService = Depends(get_organization_service),
) -> SuccessResponse[OrganizationRead]:
    organization = await service.organizations.get_active_by_id(membership.organization_id)
    restored = await service.restore(organization, actor_id=membership.user_id)
    return SuccessResponse(
        data=OrganizationRead.model_validate(restored), request_id=_request_id(request)
    )


@router.delete("/{organization_id}", response_model=SuccessResponse[dict])
async def delete_organization(
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.VIEWER)),
    service: OrganizationService = Depends(get_organization_service),
) -> SuccessResponse[dict]:
    organization = await service.organizations.get_active_by_id(membership.organization_id)
    await service.soft_delete(
        organization, actor_id=membership.user_id, requester_role=membership.role
    )
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))
