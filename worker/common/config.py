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


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
