"""Async Redis client factory.

Deliberately not cached: `Redis.from_url()` does not eagerly open a
connection (connections are established lazily per command via the
client's own pool), so constructing one per call is cheap and — unlike a
process-lifetime singleton — never binds a connection to an event loop
that a later `asyncio.run()` (e.g. a new test) has since closed.
"""

from redis.asyncio import Redis

from app.core.config import get_settings


def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)
