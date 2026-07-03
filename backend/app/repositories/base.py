"""Generic repository base.

Repositories are limited to CRUD, pagination, and filtering. Business
rules and validation must never live here (docs/06-rule.md Backend Rules).
"""

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id_: uuid.UUID) -> ModelT | None:
        result = await self.session.execute(select(self.model).where(self.model.id == id_))
        return result.scalar_one_or_none()

    async def list(self, limit: int = 50, offset: int = 0) -> list[ModelT]:
        result = await self.session.execute(select(self.model).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
