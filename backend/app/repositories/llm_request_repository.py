import uuid

from sqlalchemy import select

from app.models.llm_request import LLMRequest
from app.repositories.base import BaseRepository


class LLMRequestRepository(BaseRepository[LLMRequest]):
    model = LLMRequest

    async def list_by_prompt(
        self, prompt_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[LLMRequest]:
        result = await self.session.execute(
            select(LLMRequest)
            .where(LLMRequest.prompt_id == prompt_id)
            .order_by(LLMRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
