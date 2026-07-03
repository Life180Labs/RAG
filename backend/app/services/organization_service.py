"""Organization business logic.

Creating an organization always makes the creator its OWNER — there is
no such thing as an organization with zero owners.
"""

import uuid
from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError
from app.models.audit_log import AuditLog
from app.models.membership import MemberRole, ResourceStatus
from app.models.organization import Organization, OrganizationMember
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.membership_repository import OrganizationMemberRepository
from app.repositories.organization_repository import OrganizationRepository


class OrganizationService:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        member_repository: OrganizationMemberRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.organizations = organization_repository
        self.members = member_repository
        self.audit_logs = audit_log_repository

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def create(self, *, owner_id: uuid.UUID, name: str, slug: str) -> Organization:
        existing = await self.organizations.get_by_slug(slug)
        if existing is not None:
            raise ConflictError("An organization with this slug already exists.", code="SLUG_TAKEN")

        organization = Organization(
            name=name,
            slug=slug,
            status=ResourceStatus.ACTIVE,
            created_by=owner_id,
            updated_by=owner_id,
        )
        await self.organizations.add(organization)

        membership = OrganizationMember(
            organization_id=organization.id,
            user_id=owner_id,
            role=MemberRole.OWNER,
            joined_at=datetime.now(UTC),
        )
        await self.members.add(membership)

        await self._record_audit(
            user_id=owner_id, action="organization.create", resource=str(organization.id)
        )
        return organization

    async def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        return await self.organizations.list_for_user(user_id)

    async def update(
        self, organization: Organization, *, name: str, actor_id: uuid.UUID
    ) -> Organization:
        organization.name = name
        organization.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="organization.update", resource=str(organization.id)
        )
        return organization

    async def archive(self, organization: Organization, *, actor_id: uuid.UUID) -> Organization:
        organization.status = ResourceStatus.ARCHIVED
        organization.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="organization.archive", resource=str(organization.id)
        )
        return organization

    async def restore(self, organization: Organization, *, actor_id: uuid.UUID) -> Organization:
        organization.status = ResourceStatus.ACTIVE
        organization.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="organization.restore", resource=str(organization.id)
        )
        return organization

    async def soft_delete(
        self, organization: Organization, *, actor_id: uuid.UUID, requester_role: MemberRole
    ) -> None:
        if requester_role != MemberRole.OWNER:
            raise ForbiddenError(
                "Only the organization owner can delete it.", code="OWNER_REQUIRED"
            )
        organization.deleted_at = datetime.now(UTC)
        organization.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="organization.delete", resource=str(organization.id)
        )
