"""Redis-backed fixed-window rate limiter.

Applied as a FastAPI dependency on sensitive endpoints (login, register)
per docs/06-rule.md Security Rules. Not a global middleware because limits
vary per endpoint (docs/02-architecture.md section 136).
"""

from fastapi import Request

from app.core.exceptions import AppError
from app.core.redis import get_redis_client


class RateLimitExceededError(AppError):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"


def rate_limiter(key_prefix: str, limit: int, window_seconds: int):
    """Return a FastAPI dependency enforcing `limit` requests per `window_seconds`
    per client IP, using a Redis counter key that expires with the window.
    """

    async def _dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        redis_client = get_redis_client()
        key = f"rate_limit:{key_prefix}:{client_ip}"

        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, window_seconds)

        if current > limit:
            raise RateLimitExceededError(
                f"Too many requests. Limit is {limit} per {window_seconds} seconds."
            )

    return _dependency
