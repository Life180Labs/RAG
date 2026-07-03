"""Cross-cutting tasks shared by every queue (health checks, etc.)."""

from common.celery_app import celery_app
from common.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="common.health_check", queue="default")
def health_check() -> dict[str, str]:
    """Idempotent task used to verify the worker can receive and execute jobs."""
    logger.info("health_check_executed")
    return {"status": "ok"}
