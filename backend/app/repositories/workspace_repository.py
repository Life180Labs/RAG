import uuid

from sqlalchemy import select

from app.models.workspace import Workspace
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def get_active_by_id(self, id_: uuid.UUID) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(Workspace.id == id_, Workspace.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_slug_in_organization(
        self, organization_id: uuid.UUID, slug: str
    ) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(
                Workspace.organization_id == organization_id,
                Workspace.slug == slug,
                Workspace.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Workspace]:
        result = await self.session.execute(
            select(Workspace)
            .where(Workspace.organization_id == organization_id, Workspace.deleted_at.is_(None))
            .order_by(Workspace.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
