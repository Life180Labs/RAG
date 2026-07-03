from sqlalchemy import select

from app.models.session import Session as SessionModel
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[SessionModel]):
    model = SessionModel

    async def get_by_refresh_token_hash(self, token_hash: str) -> SessionModel | None:
        result = await self.session.execute(
            select(SessionModel).where(SessionModel.refresh_token_hash == token_hash)
        )
        return result.scalar_one_or_none()
