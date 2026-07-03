import os

# Auth/API tests exercise the real Postgres + Redis containers from
# docker/docker-compose.yml (not sqlite/mocks) so UUID/enum/pgvector
# behavior matches production. Must run before any `app.*` import, since
# Settings are read (and cached) at first import.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://rag:rag@localhost:5433/rag")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
# Exposes the dev-only reset_token in /auth/forgot-password responses so
# tests can exercise the reset flow without a real mail sender.
os.environ.setdefault("DEBUG", "true")

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.redis import get_redis_client
from app.db.session import AsyncSessionLocal
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """One event loop for the whole test session so module-level async
    singletons (the SQLAlchemy engine/session factory) stay bound to a
    live loop across tests instead of the per-test loop pytest-asyncio
    otherwise creates and closes."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def _clean_auth_tables():
    """Every auth/user test starts from an empty slate so registration and
    lockout counters never leak across tests."""
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(text("TRUNCATE sessions, audit_logs, users CASCADE"))
        await session.commit()
    redis_client = get_redis_client()
    async for key in redis_client.scan_iter(match="password_reset:*"):
        await redis_client.delete(key)
    async for key in redis_client.scan_iter(match="rate_limit:*"):
        await redis_client.delete(key)
