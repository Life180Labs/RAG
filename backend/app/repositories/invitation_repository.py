import uuid

from sqlalchemy import select

from app.models.invitation import Invitation
from app.models.membership import InvitationStatus
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository[Invitation]):
    model = Invitation

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        result = await self.session.execute(
            select(Invitation).where(Invitation.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_pending_for_email(
        self, organization_id: uuid.UUID, email: str
    ) -> Invitation | None:
        result = await self.session.execute(
            select(Invitation).where(
                Invitation.organization_id == organization_id,
                Invitation.email == email,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[Invitation]:
        result = await self.session.execute(
            select(Invitation)
            .where(Invitation.organization_id == organization_id)
            .order_by(Invitation.created_at.desc())
        )
        return list(result.scalars().all())
