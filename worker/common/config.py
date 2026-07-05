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

    # Cloud embedding providers (Phase 7) — optional; a provider is only
    # usable once its key is set. Unset in this dev environment, so the
    # corresponding provider tests are skipped (see embedding_worker tests),
    # never mocked.
    openai_api_key: str | None = None
    voyage_api_key: str | None = None
    jina_api_key: str | None = None
    # Reranking (Phase 13) — Cohere Rerank is a new cloud provider, gated
    # the same optional/skip way as the Phase 7 cloud embedding providers.
    cohere_api_key: str | None = None

    # Vector index providers (Phase 8). Qdrant/Chroma are self-hosted via
    # docker-compose; the defaults below match docker-compose.yml's default
    # *host*-side port mappings (chroma's container port 8000 is mapped to
    # host 8001 there specifically to avoid colliding with the backend API's
    # own port 8000), for pytest runs executed directly on the host rather
    # than inside the worker container. Pinecone is cloud-only and requires
    # an API key, same optional/skip pattern as the Phase 7 cloud embedding
    # providers.
    qdrant_url: str = "http://localhost:6333"
    chroma_url: str = "http://localhost:8001"
    pinecone_api_key: str | None = None


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
