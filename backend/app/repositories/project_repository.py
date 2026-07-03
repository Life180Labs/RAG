import uuid

from sqlalchemy import select

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_active_by_id(self, id_: uuid.UUID) -> Project | None:
        result = await self.session.execute(
            select(Project).where(Project.id == id_, Project.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_slug_in_workspace(self, workspace_id: uuid.UUID, slug: str) -> Project | None:
        result = await self.session.execute(
            select(Project).where(
                Project.workspace_id == workspace_id,
                Project.slug == slug,
                Project.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self, workspace_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.workspace_id == workspace_id, Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
