"""Shared worker settings.

Every queue-specific worker package (document_worker, chunk_worker, ...)
imports its Celery app configuration from here rather than duplicating it,
per docs/06-rule.md (never duplicate business logic / configuration).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"

    # Sync driver (psycopg3), distinct from the backend's async asyncpg URL —
    # Celery's prefork workers run task bodies synchronously.
    database_url: str = "postgresql+psycopg://rag:rag@localhost:5432/rag"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "ragadmin"
    minio_secret_key: str = "ragadminsecret"
    minio_bucket: str = "rag-documents"
    minio_secure: bool = False


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
