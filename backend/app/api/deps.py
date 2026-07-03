"""Dependency-injection wiring for controllers.

Controllers depend only on services (never repositories/DB directly),
per docs/06-rule.md Backend Rules. This module composes the DI graph.
"""

import uuid

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis import get_redis_client
from app.core.security import InvalidTokenError, TokenType, decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_session_repository(db: AsyncSession = Depends(get_db)) -> SessionRepository:
    return SessionRepository(db)


def get_audit_log_repository(db: AsyncSession = Depends(get_db)) -> AuditLogRepository:
    return AuditLogRepository(db)


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    session_repository: SessionRepository = Depends(get_session_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
    redis_client: Redis = Depends(get_redis_client),
) -> AuthService:
    return AuthService(user_repository, session_repository, audit_log_repository, redis_client)


def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(user_repository)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    user_service: UserService = Depends(get_user_service),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token.", code="UNAUTHORIZED")

    try:
        payload = decode_token(credentials.credentials, TokenType.ACCESS)
    except InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired access token.", code="INVALID_TOKEN") from exc

    user = await user_service.get_by_id(uuid.UUID(payload["sub"]))
    if not user.is_active:
        raise UnauthorizedError("User is no longer active.", code="INVALID_TOKEN")
    return user


def require_role(*allowed_roles: UserRole):
    """Route-guard dependency factory: `Depends(require_role(UserRole.ADMIN))`."""

    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                "You do not have permission to perform this action.", code="FORBIDDEN"
            )
        return current_user

    return _dependency
