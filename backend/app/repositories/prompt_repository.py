import uuid

from sqlalchemy import select

from app.models.prompt import Prompt
from app.repositories.base import BaseRepository


class PromptRepository(BaseRepository[Prompt]):
    model = Prompt

    async def list_by_retrieval(
        self, retrieval_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Prompt]:
        result = await self.session.execute(
            select(Prompt)
            .where(Prompt.retrieval_id == retrieval_id)
            .order_by(Prompt.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
