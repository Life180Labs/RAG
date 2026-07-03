"""FastAPI application factory.

The backend never performs heavy AI workloads directly (docs/02-architecture.md
section 6); those are delegated to the worker service via Redis/Celery.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.storage import ensure_bucket_exists, get_storage_client
from app.middleware.metrics import MetricsMiddleware
from app.middleware.request_context import RequestContextMiddleware

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", environment=settings.app_env)
    try:
        ensure_bucket_exists(get_storage_client(), settings.minio_bucket)
    except Exception as exc:  # noqa: BLE001 - object storage may not be up yet
        logger.warning("object_storage_bootstrap_failed", error=str(exc))
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise RAG Studio API",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
