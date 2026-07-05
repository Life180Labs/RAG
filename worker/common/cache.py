"""Retrieval cache (docs/02-architecture.md section 100; docs/05-task.md
Phase 17): "Store retrieval results for frequently executed searches...
if nothing changed in the index, reuse retrieval results."

Redis-backed, sync client — `retrieval_worker.execute_retrieval` runs
inside a Celery prefork worker, synchronously, same as every other
worker task. Key format and metrics-key names must exactly match
`backend/app/core/cache/metrics.py`'s, since both processes read/write
the same Redis instance; there is no shared import between them (a
worker package never imports backend code), so this is deliberately
duplicated rather than shared, the same convention `EMBEDDING_DIM_MAX`
already established between the two.

Invalidation is implicit, not an explicit "clear on rebuild" call: the
cache key includes `embed_version`/`index_version` (the same
`embedding_versions.version`/`vector_indexes.version` counters Phase 7/8
already bump on every regeneration), so a real re-embed or index rebuild
naturally produces a new key and every old entry simply stops being
looked up — no stale-entry bookkeeping needed, and old entries just
expire via their own TTL.
"""

import hashlib
import json

import redis

from common.config import get_worker_settings

METRICS_KEY_PREFIX = "cache:metrics"
CACHE_KEY_PREFIX = "cache:retrieval"


def _client() -> redis.Redis:
    settings = get_worker_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def build_key(**fields: object) -> str:
    """Hash of every field that can change the result set — anything not
    passed here is implicitly assumed identical between requests, so
    callers must include every retrieval option that affects output.
    """
    serialized = json.dumps(fields, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_cached(key: str) -> dict | None:
    client = _client()
    raw = client.get(f"{CACHE_KEY_PREFIX}:{key}")
    if raw is None:
        client.incr(f"{METRICS_KEY_PREFIX}:retrieval:misses")
        return None
    client.incr(f"{METRICS_KEY_PREFIX}:retrieval:hits")
    return json.loads(raw)


def set_cached(key: str, value: dict) -> None:
    settings = get_worker_settings()
    client = _client()
    client.set(
        f"{CACHE_KEY_PREFIX}:{key}", json.dumps(value), ex=settings.retrieval_cache_ttl_seconds
    )
