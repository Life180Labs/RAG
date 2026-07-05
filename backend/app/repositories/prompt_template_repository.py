import uuid

from sqlalchemy import func, select

from app.models.prompt import PromptTemplate
from app.repositories.base import BaseRepository


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    model = PromptTemplate

    async def list_by_repository(
        self, repository_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[PromptTemplate]:
        result = await self.session.execute(
            select(PromptTemplate)
            .where(PromptTemplate.repository_id == repository_id)
            .order_by(PromptTemplate.name, PromptTemplate.version.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_latest_version(
        self, repository_id: uuid.UUID, name: str
    ) -> PromptTemplate | None:
        result = await self.session.execute(
            select(PromptTemplate)
            .where(PromptTemplate.repository_id == repository_id, PromptTemplate.name == name)
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_max_version(self, repository_id: uuid.UUID, name: str) -> int:
        result = await self.session.execute(
            select(func.max(PromptTemplate.version)).where(
                PromptTemplate.repository_id == repository_id, PromptTemplate.name == name
            )
        )
        return result.scalar_one_or_none() or 0

    async def list_versions(self, repository_id: uuid.UUID, name: str) -> list[PromptTemplate]:
        result = await self.session.execute(
            select(PromptTemplate)
            .where(PromptTemplate.repository_id == repository_id, PromptTemplate.name == name)
            .order_by(PromptTemplate.version)
        )
        return list(result.scalars().all())
