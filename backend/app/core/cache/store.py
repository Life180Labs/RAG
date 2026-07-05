"""Generic Redis-backed JSON cache store, shared by every Phase 17 cache
type backend itself owns: the Prompt Cache (`LLMService`) and the
Metadata/API Cache (a handful of hot, low-write repository-scoped list
endpoints — e.g. `GET .../prompt-templates`). The Retrieval Cache lives
entirely inside `worker/common/cache.py`, and the Semantic Cache is
pgvector-backed, not Redis-backed.

One small class rather than a bespoke implementation per cache type:
every Redis-backed cache here needs the same operations (get,
set-with-TTL, delete-on-write for invalidation, record hit/miss for
`metrics.get_stats`'s "Cache Hit Ratio").
"""

import json
from typing import Any

from app.core.cache import metrics
from app.core.redis import get_redis_client

CACHE_KEY_PREFIX = "cache"


class CacheStore:
    def __init__(self, cache_type: str, ttl_seconds: int):
        self.cache_type = cache_type
        self.ttl_seconds = ttl_seconds

    def _key(self, key: str) -> str:
        return f"{CACHE_KEY_PREFIX}:{self.cache_type}:{key}"

    async def get(self, key: str) -> Any | None:
        redis_client = get_redis_client()
        raw = await redis_client.get(self._key(key))
        if raw is None:
            await metrics.record_miss(self.cache_type)
            return None
        await metrics.record_hit(self.cache_type)
        return json.loads(raw)

    async def set(self, key: str, value: Any) -> None:
        redis_client = get_redis_client()
        await redis_client.set(self._key(key), json.dumps(value), ex=self.ttl_seconds)

    async def delete(self, key: str) -> None:
        redis_client = get_redis_client()
        await redis_client.delete(self._key(key))
