import uuid

from sqlalchemy import select

from app.models.organization import Organization, OrganizationMember
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_active_by_id(self, id_: uuid.UUID) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.id == id_, Organization.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(
                Organization.slug == slug, Organization.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Organization]:
        result = await self.session.execute(
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(OrganizationMember.user_id == user_id, Organization.deleted_at.is_(None))
            .order_by(Organization.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
