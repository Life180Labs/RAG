import uuid

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.users = user_repository

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user

    async def update_profile(self, user_id: uuid.UUID, *, full_name: str) -> User:
        user = await self.get_by_id(user_id)
        user.full_name = full_name.strip()
        return user
