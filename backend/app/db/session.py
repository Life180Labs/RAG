"""Async SQLAlchemy engine and session factory.

Repositories depend on `get_db` for a session; controllers and services
never open a session directly.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.exceptions import AppError

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Unit-of-work per request: commits on success, rolls back on error.

    Services/repositories only `flush()`; they never call commit/rollback
    themselves so a single request is always one atomic transaction.

    `AppError` (invalid credentials, lockout, not-found, ...) is an
    *expected* business outcome mapped to a specific HTTP status — its
    side effects (e.g. an incremented failed-login counter) must still be
    persisted even though the request ultimately returns an error to the
    client. Only genuinely unexpected exceptions roll back.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except AppError:
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
