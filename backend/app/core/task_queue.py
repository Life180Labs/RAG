"""Enqueues background tasks without importing the worker's task modules.

The backend and worker are separate deployables; they only share a
contract (task name + arguments), never Python code. `send_task` submits
by name over the same Redis broker the worker already consumes from.
"""

from celery import Celery

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _build_client() -> Celery:
    settings = get_settings()
    client = Celery("enterprise_rag_studio_client", broker=settings.redis_url)
    # Must match the worker's `task_default_queue` (common/celery_app.py) —
    # otherwise `send_task` publishes to Celery's built-in "celery" queue,
    # which nothing consumes, and the task silently never runs.
    client.conf.task_default_queue = "default"
    return client


def enqueue_finalize_upload(document_id: str) -> None:
    client = _build_client()
    try:
        client.send_task("document_worker.finalize_upload", args=[document_id])
    except Exception as exc:  # noqa: BLE001 - enqueue failure must never break the upload response
        logger.error("enqueue_finalize_upload_failed", document_id=document_id, error=str(exc))


def enqueue_chunk_document(document_id: str, strategy: str) -> None:
    client = _build_client()
    try:
        client.send_task("chunk_worker.chunk_document", args=[document_id, strategy])
    except Exception as exc:  # noqa: BLE001 - enqueue failure must never break the response
        logger.error(
            "enqueue_chunk_document_failed",
            document_id=document_id,
            strategy=strategy,
            error=str(exc),
        )


def enqueue_embed_chunk_set(chunk_set_id: str, provider: str, model: str | None) -> None:
    client = _build_client()
    try:
        client.send_task(
            "embedding_worker.embed_chunk_set", args=[chunk_set_id, provider, model]
        )
    except Exception as exc:  # noqa: BLE001 - enqueue failure must never break the response
        logger.error(
            "enqueue_embed_chunk_set_failed",
            chunk_set_id=chunk_set_id,
            provider=provider,
            error=str(exc),
        )
