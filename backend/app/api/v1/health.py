"""Health, readiness, and liveness endpoints.

Used by Docker/Kubernetes health checks and load balancers, per
docs/02-architecture.md section 142.
"""

import uuid

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client
from app.core.storage import get_storage_client
from app.db.session import AsyncSessionLocal

router = APIRouter()
logger = get_logger(__name__)


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    checks: dict[str, str] = {}
    healthy = True

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - health check must never raise
        checks["database"] = "unavailable"
        healthy = False
        logger.error("readiness_check_failed", dependency="database", error=str(exc))

    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = "unavailable"
        healthy = False
        logger.error("readiness_check_failed", dependency="redis", error=str(exc))

    try:
        settings = get_settings()
        storage_client = get_storage_client()
        storage_client.bucket_exists(settings.minio_bucket)
        checks["object_storage"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["object_storage"] = "unavailable"
        healthy = False
        logger.error("readiness_check_failed", dependency="object_storage", error=str(exc))

    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ready" if healthy else "not_ready", "checks": checks}


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
    }
