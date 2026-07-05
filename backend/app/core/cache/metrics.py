"""Cache hit/miss counters (docs/02-architecture.md section 148's "Cache
Hit Ratio" metric, section 168's monitoring dashboards).

Persisted in Redis, not Postgres — these are ephemeral operational
counters describing the caches themselves, not tenant data; they reset
if Redis is flushed, the same lifetime class as the cache entries they
describe. Never tenant-scoped (there is no `repository_id` here) since
they report on the caching *system's* effectiveness, not any one
customer's usage.
"""

from app.core.redis import get_redis_client

METRICS_KEY_PREFIX = "cache:metrics"

CACHE_TYPES = ["retrieval", "prompt", "semantic", "metadata"]


async def record_hit(cache_type: str) -> None:
    redis_client = get_redis_client()
    await redis_client.incr(f"{METRICS_KEY_PREFIX}:{cache_type}:hits")


async def record_miss(cache_type: str) -> None:
    redis_client = get_redis_client()
    await redis_client.incr(f"{METRICS_KEY_PREFIX}:{cache_type}:misses")


async def get_stats() -> dict[str, dict[str, int | float]]:
    redis_client = get_redis_client()
    stats: dict[str, dict[str, int | float]] = {}
    for cache_type in CACHE_TYPES:
        hits = int(await redis_client.get(f"{METRICS_KEY_PREFIX}:{cache_type}:hits") or 0)
        misses = int(await redis_client.get(f"{METRICS_KEY_PREFIX}:{cache_type}:misses") or 0)
        total = hits + misses
        stats[cache_type] = {
            "hits": hits,
            "misses": misses,
            "hit_ratio": round(hits / total, 4) if total else 0.0,
        }
    return stats
