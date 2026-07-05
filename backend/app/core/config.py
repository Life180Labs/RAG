"""Centralized application settings loaded from environment variables.

Never hardcode secrets or connection strings elsewhere; every module that
needs configuration must depend on `Settings` via `get_settings()`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_env: str = "local"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Object storage
    storage_backend: str = "minio"  # "minio" | "local"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "ragadmin"
    minio_secret_key: str = "ragadminsecret"
    minio_bucket: str = "rag-documents"
    minio_secure: bool = False
    local_storage_path: str = "./data/storage"

    # Documents
    max_upload_size_bytes: int = 500 * 1024 * 1024  # 500 MB, per docs/01-project.md
    allowed_upload_extensions: list[str] = [
        "pdf",
        "docx",
        "txt",
        "md",
        "csv",
        "html",
        "json",
        "xml",
    ]

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # LLM Gateway (Phase 15) — cloud providers are optional; unset ones are
    # real integrations that simply aren't reachable in this environment,
    # the same "gated by an unset key" convention Phase 7/13's cloud
    # embedding/reranking providers already established.
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    # Ollama is self-hosted, not key-gated — it's a real integration that's
    # simply unreachable when no Ollama server runs at this address, the
    # same shape of gap as an unset cloud API key.
    ollama_base_url: str = "http://localhost:11434"


@lru_cache
def get_settings() -> Settings:
    return Settings()
