"""Organization invitation endpoints.

Invite/list/resend are organization ADMIN+ actions; accept/reject only
require the caller to be authenticated and hold the matching invite
token — the service verifies the token's email matches the caller.
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.tenancy_deps import get_invitation_service, require_organization_role
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.membership import MemberRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.invitation import (
    InvitationAccept,
    InvitationCreate,
    InvitationRead,
    InvitationReject,
)
from app.services.invitation_service import InvitationService

router = APIRouter(tags=["invitations"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(
    "/organizations/{organization_id}/invitations", response_model=SuccessResponse[dict]
)
async def invite_member(
    payload: InvitationCreate,
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: InvitationService = Depends(get_invitation_service),
) -> SuccessResponse[dict]:
    settings = get_settings()
    invitation, raw_token = await service.invite(
        organization_id=membership.organization_id,
        inviter_id=membership.user_id,
        email=payload.email,
        role=payload.role,
    )
    data: dict = {"invitation": InvitationRead.model_validate(invitation).model_dump(mode="json")}
    if settings.debug:
        # Dev/local convenience only — no email service exists yet.
        data["invite_token"] = raw_token
    return SuccessResponse(data=data, request_id=_request_id(request))


@router.get(
    "/organizations/{organization_id}/invitations",
    response_model=SuccessResponse[list[InvitationRead]],
)
async def list_invitations(
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: InvitationService = Depends(get_invitation_service),
) -> SuccessResponse[list[InvitationRead]]:
    invitations = await service.list_for_organization(membership.organization_id)
    return SuccessResponse(
        data=[InvitationRead.model_validate(i) for i in invitations],
        request_id=_request_id(request),
    )


@router.post(
    "/organizations/{organization_id}/invitations/{invitation_id}/resend",
    response_model=SuccessResponse[dict],
)
async def resend_invitation(
    invitation_id: uuid.UUID,
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: InvitationService = Depends(get_invitation_service),
) -> SuccessResponse[dict]:
    settings = get_settings()
    invitation = await service.invitations.get_by_id(invitation_id)
    if invitation is None or invitation.organization_id != membership.organization_id:
        raise NotFoundError("Invitation not found.", code="INVITATION_NOT_FOUND")

    raw_token = await service.resend(invitation, actor_id=membership.user_id)
    data: dict = {"resent": True}
    if settings.debug:
        data["invite_token"] = raw_token
    return SuccessResponse(data=data, request_id=_request_id(request))


@router.post("/invitations/accept", response_model=SuccessResponse[dict])
async def accept_invitation(
    payload: InvitationAccept,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: InvitationService = Depends(get_invitation_service),
) -> SuccessResponse[dict]:
    await service.accept(token=payload.token, current_user=current_user)
    return SuccessResponse(data={"accepted": True}, request_id=_request_id(request))


@router.post("/invitations/reject", response_model=SuccessResponse[dict])
async def reject_invitation(
    payload: InvitationReject,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: InvitationService = Depends(get_invitation_service),
) -> SuccessResponse[dict]:
    await service.reject(token=payload.token, current_user=current_user)
    return SuccessResponse(data={"rejected": True}, request_id=_request_id(request))
