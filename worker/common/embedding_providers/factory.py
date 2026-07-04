"""Embedding provider factory — maps a provider name to a configured
`EmbeddingProvider` instance (docs/05-task.md Phase 7).

Local providers (bge, e5, nomic) never fail to construct — they have no
external dependency beyond the ONNX weights being cached. Cloud
providers (openai, voyage, jina) raise `ProviderNotConfiguredError` when
their API key isn't set, which `embedding_worker.tasks` surfaces as a
`FAILED_EMBED` document status rather than crashing the whole batch.

Lives in `common` (not `embedding_worker`) so both `embedding_worker`
(batch embedding at ingest time) and `retrieval_worker` (Phase 9,
single-text query embedding at search time) can use it without either
one importing the other's package — the same promotion Phase 7 applied
to `common.tokenizer`.
"""

from common.config import get_worker_settings
from common.embedding_providers.base import EmbeddingProvider
from common.embedding_providers.cloud import (
    JinaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    VoyageEmbeddingProvider,
)
from common.embedding_providers.local import LOCAL_MODEL_NAMES, LocalEmbeddingProvider

DEFAULT_PROVIDER = "bge"

DEFAULT_MODELS: dict[str, str] = {
    "bge": LOCAL_MODEL_NAMES["bge"],
    "e5": LOCAL_MODEL_NAMES["e5"],
    "nomic": LOCAL_MODEL_NAMES["nomic"],
    "openai": "text-embedding-3-small",
    "voyage": "voyage-2",
    "jina": "jina-embeddings-v2-base-en",
}

_LOCAL_PROVIDERS = set(LOCAL_MODEL_NAMES)


def default_model(provider: str) -> str:
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unknown embedding provider '{provider}'.")
    return DEFAULT_MODELS[provider]


def get_provider(provider: str, model: str | None = None) -> EmbeddingProvider:
    resolved_model = model or default_model(provider)

    if provider in _LOCAL_PROVIDERS:
        return LocalEmbeddingProvider(provider, resolved_model)

    settings = get_worker_settings()
    if provider == "openai":
        return OpenAIEmbeddingProvider(resolved_model, settings.openai_api_key)
    if provider == "voyage":
        return VoyageEmbeddingProvider(resolved_model, settings.voyage_api_key)
    if provider == "jina":
        return JinaEmbeddingProvider(resolved_model, settings.jina_api_key)

    raise ValueError(f"Unknown embedding provider '{provider}'.")
