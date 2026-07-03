"""Organization invitation business logic.

No email service exists yet (same situation as password reset in
Phase 1): the raw invite token is returned to the caller only when
`Settings.debug` is true; production must wire this to a real mail
sender before launch. Expiry is checked lazily (on accept/reject) rather
than via a scheduled job, since Celery Beat isn't wired up yet.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.models.audit_log import AuditLog
from app.models.invitation import Invitation
from app.models.membership import InvitationStatus, MemberRole
from app.models.organization import OrganizationMember
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.membership_repository import OrganizationMemberRepository
from app.repositories.user_repository import UserRepository

INVITATION_TTL_DAYS = 7


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class InvitationService:
    def __init__(
        self,
        invitation_repository: InvitationRepository,
        member_repository: OrganizationMemberRepository,
        user_repository: UserRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.invitations = invitation_repository
        self.members = member_repository
        self.users = user_repository
        self.audit_logs = audit_log_repository

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def invite(
        self, *, organization_id: uuid.UUID, inviter_id: uuid.UUID, email: str, role: MemberRole
    ) -> tuple[Invitation, str]:
        normalized_email = email.lower()

        existing_user = await self.users.get_by_email(normalized_email)
        if existing_user is not None:
            existing_membership = await self.members.get_membership(
                organization_id, existing_user.id
            )
            if existing_membership is not None:
                raise ConflictError(
                    "This user is already a member of the organization.", code="ALREADY_MEMBER"
                )

        pending = await self.invitations.get_pending_for_email(organization_id, normalized_email)
        if pending is not None:
            raise ConflictError(
                "An invitation is already pending for this email.", code="INVITE_ALREADY_PENDING"
            )

        raw_token = secrets.token_urlsafe(32)
        invitation = Invitation(
            organization_id=organization_id,
            email=normalized_email,
            role=role,
            invited_by=inviter_id,
            token_hash=_hash_token(raw_token),
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS),
        )
        await self.invitations.add(invitation)
        await self._record_audit(
            user_id=inviter_id, action="invitation.create", resource=str(invitation.id)
        )
        return invitation, raw_token

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[Invitation]:
        return await self.invitations.list_by_organization(organization_id)

    async def resend(self, invitation: Invitation, *, actor_id: uuid.UUID) -> str:
        raw_token = secrets.token_urlsafe(32)
        invitation.token_hash = _hash_token(raw_token)
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS)
        await self._record_audit(
            user_id=actor_id, action="invitation.resend", resource=str(invitation.id)
        )
        return raw_token

    async def _resolve_pending(self, token: str) -> Invitation:
        invitation = await self.invitations.get_by_token_hash(_hash_token(token))
        if invitation is None:
            raise UnauthorizedError("Invalid invitation token.", code="INVALID_TOKEN")

        if invitation.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            invitation.status = InvitationStatus.EXPIRED
            raise UnauthorizedError("This invitation has expired.", code="INVITATION_EXPIRED")

        if invitation.status != InvitationStatus.PENDING:
            raise ConflictError(
                f"This invitation is already {invitation.status.value}.",
                code="INVITATION_NOT_PENDING",
            )

        return invitation

    async def accept(self, *, token: str, current_user: User) -> OrganizationMember:
        invitation = await self._resolve_pending(token)

        if invitation.email != current_user.email.lower():
            raise ForbiddenError(
                "This invitation was sent to a different email address.", code="EMAIL_MISMATCH"
            )

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(UTC)

        membership = OrganizationMember(
            organization_id=invitation.organization_id,
            user_id=current_user.id,
            role=invitation.role,
            invited_by=invitation.invited_by,
            joined_at=datetime.now(UTC),
        )
        await self.members.add(membership)
        await self._record_audit(
            user_id=current_user.id, action="invitation.accept", resource=str(invitation.id)
        )
        return membership

    async def reject(self, *, token: str, current_user: User) -> None:
        invitation = await self._resolve_pending(token)

        if invitation.email != current_user.email.lower():
            raise ForbiddenError(
                "This invitation was sent to a different email address.", code="EMAIL_MISMATCH"
            )

        invitation.status = InvitationStatus.REJECTED
        await self._record_audit(
            user_id=current_user.id, action="invitation.reject", resource=str(invitation.id)
        )
