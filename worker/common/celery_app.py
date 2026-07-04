"""Shared Celery application.

Queue-specific workers (document_worker, chunk_worker, embedding_worker,
index_worker, evaluation_worker, benchmark_worker) register their tasks
against this app and are deployed as independent, horizontally-scalable
processes per docs/02-architecture.md section 182 (Worker Scaling).
"""

from celery import Celery

from common.config import get_worker_settings
from common.logging import configure_logging

settings = get_worker_settings()
configure_logging(settings.log_level)

celery_app = Celery("enterprise_rag_studio", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    broker_connection_retry_on_startup=True,
)

celery_app.autodiscover_tasks(
    [
        "common",
        "document_worker",
        "chunk_worker",
        "embedding_worker",
        "index_worker",
        "retrieval_worker",
        "evaluation_worker",
        "benchmark_worker",
    ]
)
