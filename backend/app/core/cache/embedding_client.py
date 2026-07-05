"""Synchronous-from-the-caller's-view query embedding, backed by a real
Celery round trip to `retrieval_worker.embed_query_text` (docs/05-task.md
Phase 17's Semantic Cache).

Bounded polling on `AsyncResult.ready()`, the same shape as
`ConversationService._wait_for_retrieval`'s bounded poll on a DB row —
here there's no DB row to poll (the computation is a pure function of
its arguments), so the Celery result backend stands in for it. Fails
open: any timeout, missing vector index, or provider error returns None
rather than raising, since the caller (semantic cache) must always be
able to fall back to running the full pipeline.
"""

import asyncio

from app.core.logging import get_logger
from app.core.task_queue import send_embed_query_text

logger = get_logger(__name__)

EMBED_QUERY_POLL_TIMEOUT_SECONDS = 10.0
EMBED_QUERY_POLL_INTERVAL_SECONDS = 0.2


async def embed_query_text(vector_index_id: str, query_text: str) -> list[float] | None:
    async_result = send_embed_query_text(vector_index_id, query_text)
    if async_result is None:
        return None

    elapsed = 0.0
    while not async_result.ready() and elapsed < EMBED_QUERY_POLL_TIMEOUT_SECONDS:
        await asyncio.sleep(EMBED_QUERY_POLL_INTERVAL_SECONDS)
        elapsed += EMBED_QUERY_POLL_INTERVAL_SECONDS

    if not async_result.ready():
        logger.warning("embed_query_text_timed_out", vector_index_id=vector_index_id)
        return None

    try:
        result = async_result.get(timeout=0)
    except Exception as exc:  # noqa: BLE001 - any worker-side failure is a cache-miss signal
        logger.warning("embed_query_text_failed", vector_index_id=vector_index_id, error=str(exc))
        return None

    if result.get("status") != "ok":
        logger.info(
            "embed_query_text_error",
            vector_index_id=vector_index_id,
            message=result.get("message"),
        )
        return None

    return result["vector"]
