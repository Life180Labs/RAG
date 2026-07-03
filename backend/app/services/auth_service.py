"""Authentication business logic.

Handles registration, login (with account lockout), refresh-token
rotation, logout, and password reset. Controllers only call this service;
they never touch repositories or JWT/hashing primitives directly
(docs/06-rule.md Backend Rules).
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.audit_log import AuditLog
from app.models.session import Session as SessionModel
from app.models.user import User, UserRole
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)

MAX_FAILED_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_MINUTES = 15
PASSWORD_RESET_TOKEN_TTL_SECONDS = 30 * 60
PASSWORD_RESET_REDIS_PREFIX = "password_reset"


class AccountLockedError(ForbiddenError):
    code = "ACCOUNT_LOCKED"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        audit_log_repository: AuditLogRepository,
        redis_client: Redis,
    ):
        self.users = user_repository
        self.sessions = session_repository
        self.audit_logs = audit_log_repository
        self.redis = redis_client

    async def _record_audit(
        self, *, user_id: uuid.UUID | None, action: str, result: str, ip_address: str | None
    ) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, result=result, ip_address=ip_address)
        )

    async def register(self, *, email: str, password: str, full_name: str) -> User:
        normalized_email = email.lower()
        existing = await self.users.get_by_email(normalized_email)
        if existing is not None:
            raise ConflictError("An account with this email already exists.", code="EMAIL_TAKEN")

        user = User(
            email=normalized_email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.VIEWER,
            is_active=True,
        )
        await self.users.add(user)
        await self._record_audit(
            user_id=user.id, action="register", result="success", ip_address=None
        )
        return user

    async def authenticate(
        self, *, email: str, password: str, ip_address: str | None, user_agent: str | None
    ) -> tuple[User, str, str]:
        settings = get_settings()
        user = await self.users.get_by_email(email)

        if user is None:
            await self._record_audit(
                user_id=None, action="login", result="failure", ip_address=ip_address
            )
            raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS")

        now = datetime.now(UTC)
        if user.locked_until is not None and user.locked_until > now:
            await self._record_audit(
                user_id=user.id, action="login", result="locked", ip_address=ip_address
            )
            raise AccountLockedError(
                "Account is temporarily locked due to repeated failed login attempts."
            )

        if not user.is_active or not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=ACCOUNT_LOCKOUT_MINUTES)
            await self._record_audit(
                user_id=user.id, action="login", result="failure", ip_address=ip_address
            )
            raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now

        session = SessionModel(
            user_id=user.id,
            refresh_token_hash="",
            device=None,
            ip_address=ip_address,
            user_agent=user_agent,
            last_activity_at=now,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
        await self.sessions.add(session)

        access_token = create_access_token(
            user_id=user.id, role=user.role.value, session_id=session.id
        )
        refresh_token = create_refresh_token(user_id=user.id, session_id=session.id)
        session.refresh_token_hash = _hash_token(refresh_token)

        await self._record_audit(
            user_id=user.id, action="login", result="success", ip_address=ip_address
        )
        return user, access_token, refresh_token

    async def refresh(self, *, refresh_token: str) -> tuple[str, str]:
        try:
            payload = decode_token(refresh_token, TokenType.REFRESH)
        except InvalidTokenError as exc:
            raise UnauthorizedError(
                "Invalid or expired refresh token.", code="INVALID_TOKEN"
            ) from exc

        session = await self.sessions.get_by_refresh_token_hash(_hash_token(refresh_token))
        if session is None or session.revoked_at is not None:
            raise UnauthorizedError("Session has been revoked.", code="SESSION_REVOKED")

        now = datetime.now(UTC)
        if session.expires_at.replace(tzinfo=UTC) < now:
            raise UnauthorizedError("Session has expired.", code="SESSION_EXPIRED")

        user = await self.users.get_by_id(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedError("User is no longer active.", code="INVALID_TOKEN")

        new_access_token = create_access_token(
            user_id=user.id, role=user.role.value, session_id=session.id
        )
        new_refresh_token = create_refresh_token(user_id=user.id, session_id=session.id)

        session.refresh_token_hash = _hash_token(new_refresh_token)
        session.last_activity_at = now

        return new_access_token, new_refresh_token

    async def logout(self, *, refresh_token: str) -> None:
        session = await self.sessions.get_by_refresh_token_hash(_hash_token(refresh_token))
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            await self._record_audit(
                user_id=session.user_id, action="logout", result="success", ip_address=None
            )

    async def request_password_reset(self, *, email: str) -> str | None:
        """Issues a single-use reset token, storing only its hash in Redis
        (TTL-bound, keyed by the hash so the raw token is never persisted).

        Returns the raw token only so the caller can decide whether to expose
        it (debug/local only — no email service exists yet; production must
        wire this to a real mail sender rather than ever returning it via the
        API). Always returns None for unknown emails so the API never reveals
        whether an address is registered.
        """
        user = await self.users.get_by_email(email)
        if user is None:
            return None

        reset_token = secrets.token_urlsafe(32)
        redis_key = f"{PASSWORD_RESET_REDIS_PREFIX}:{_hash_token(reset_token)}"
        await self.redis.set(redis_key, str(user.id), ex=PASSWORD_RESET_TOKEN_TTL_SECONDS)
        return reset_token

    async def reset_password(self, *, reset_token: str, new_password: str) -> None:
        redis_key = f"{PASSWORD_RESET_REDIS_PREFIX}:{_hash_token(reset_token)}"
        user_id_str = await self.redis.get(redis_key)
        if user_id_str is None:
            raise UnauthorizedError("Invalid or expired reset token.", code="INVALID_TOKEN")

        user = await self.users.get_by_id(uuid.UUID(user_id_str))
        if user is None:
            raise UnauthorizedError("Invalid or expired reset token.", code="INVALID_TOKEN")

        # Single-use: invalidate immediately so the same token cannot be replayed.
        await self.redis.delete(redis_key)

        user.hashed_password = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self._record_audit(
            user_id=user.id, action="password_reset", result="success", ip_address=None
        )
