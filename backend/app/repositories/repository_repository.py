"""Data access for the Repository resource.

Named `RepositoryRepository` to stay consistent with this codebase's
Repository-pattern convention (`backend/app/repositories/`) even though
the domain entity is also called "Repository" — the two are unrelated
concepts that happen to share a name (see docs/03-database.md section 11).
"""

import uuid

from sqlalchemy import or_, select

from app.models.repository import Repository
from app.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository]):
    model = Repository

    async def get_active_by_id(self, id_: uuid.UUID) -> Repository | None:
        result = await self.session.execute(
            select(Repository).where(Repository.id == id_, Repository.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_slug_in_project(self, project_id: uuid.UUID, slug: str) -> Repository | None:
        result = await self.session.execute(
            select(Repository).where(
                Repository.project_id == project_id,
                Repository.slug == slug,
                Repository.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_project(
        self, project_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Repository]:
        result = await self.session.execute(
            select(Repository)
            .where(Repository.project_id == project_id, Repository.deleted_at.is_(None))
            .order_by(Repository.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def search_by_project(
        self, project_id: uuid.UUID, query: str, limit: int = 50
    ) -> list[Repository]:
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(Repository)
            .where(
                Repository.project_id == project_id,
                Repository.deleted_at.is_(None),
                or_(Repository.name.ilike(pattern), Repository.description.ilike(pattern)),
            )
            .order_by(Repository.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
