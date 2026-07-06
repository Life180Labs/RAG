"""Per-organization provider API key endpoints.

All three routes are organization ADMIN+ only (same minimum as
invitations) — configuring which LLM/embedding/reranking/vector-index
keys the org uses is a tenant-administrative action, not something every
member should be able to change. The raw key is never echoed back in any
response, including immediately after creation.
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.tenancy_deps import get_provider_credential_service, require_organization_role
from app.models.membership import MemberRole
from app.models.organization import OrganizationMember
from app.schemas.common import SuccessResponse
from app.schemas.provider_credential import ProviderCredentialCreate, ProviderCredentialRead
from app.services.provider_credential_service import ProviderCredentialService

router = APIRouter(tags=["provider-credentials"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.post(
    "/organizations/{organization_id}/provider-credentials",
    response_model=SuccessResponse[ProviderCredentialRead],
)
async def upsert_provider_credential(
    payload: ProviderCredentialCreate,
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: ProviderCredentialService = Depends(get_provider_credential_service),
) -> SuccessResponse[ProviderCredentialRead]:
    credential = await service.upsert(
        organization_id=membership.organization_id,
        provider=payload.provider,
        api_key=payload.api_key,
        actor_id=membership.user_id,
    )
    return SuccessResponse(
        data=ProviderCredentialRead.model_validate(credential),
        request_id=_request_id(request),
    )


@router.get(
    "/organizations/{organization_id}/provider-credentials",
    response_model=SuccessResponse[list[ProviderCredentialRead]],
)
async def list_provider_credentials(
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: ProviderCredentialService = Depends(get_provider_credential_service),
) -> SuccessResponse[list[ProviderCredentialRead]]:
    credentials = await service.list_for_organization(membership.organization_id)
    return SuccessResponse(
        data=[ProviderCredentialRead.model_validate(c) for c in credentials],
        request_id=_request_id(request),
    )


@router.delete(
    "/organizations/{organization_id}/provider-credentials/{credential_id}",
    response_model=SuccessResponse[dict],
)
async def delete_provider_credential(
    credential_id: uuid.UUID,
    request: Request,
    membership: OrganizationMember = Depends(require_organization_role(MemberRole.ADMIN)),
    service: ProviderCredentialService = Depends(get_provider_credential_service),
) -> SuccessResponse[dict]:
    await service.delete(
        organization_id=membership.organization_id,
        credential_id=credential_id,
        actor_id=membership.user_id,
    )
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))
