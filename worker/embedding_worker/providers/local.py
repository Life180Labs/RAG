"""Local ONNX-backed embedding providers (docs/05-task.md Phase 7).

Runs BGE, E5, and Nomic models fully locally via `fastembed`
(ONNX Runtime) — no API key, no network access after the model weights
are cached, and no torch dependency (fastembed ships quantized ONNX
weights, which keeps the worker image far smaller than a
sentence-transformers/torch install would). This is the one real,
fully-tested embedding path for this phase; OpenAI/Voyage/Jina
(providers.cloud) are real HTTP integrations too but require API keys
this environment doesn't have configured, so they're exercised in CI
only when the corresponding key is present (see providers.cloud).

Model weights are pre-cached at Docker build time (see worker/Dockerfile*)
the same way Phase 6 pre-cached tiktoken's cl100k_base file, so the
worker doesn't need network access on first use in a running container.
"""

import time
from functools import lru_cache

from fastembed import TextEmbedding

from common.tokenizer import count_tokens
from embedding_worker.providers.base import EmbeddingProvider, EmbeddingResult

# fastembed's exact supported model name per our three local providers,
# per `TextEmbedding.list_supported_models()` on the pinned fastembed
# version — not every BGE/E5/Nomic variant is available, so these are the
# specific ones this fastembed version actually ships.
LOCAL_MODEL_NAMES: dict[str, str] = {
    "bge": "BAAI/bge-small-en-v1.5",
    "e5": "intfloat/multilingual-e5-large",
    "nomic": "nomic-ai/nomic-embed-text-v1.5",
}


@lru_cache(maxsize=len(LOCAL_MODEL_NAMES))
def _load_model(model_name: str) -> TextEmbedding:
    return TextEmbedding(model_name=model_name)


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, provider_name: str, model_name: str | None = None) -> None:
        if provider_name not in LOCAL_MODEL_NAMES:
            raise ValueError(f"Unknown local embedding provider '{provider_name}'.")
        self.provider_name = provider_name
        self.model_name = model_name or LOCAL_MODEL_NAMES[provider_name]

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        model = _load_model(self.model_name)
        token_counts = [count_tokens(text) for text in texts]

        start = time.perf_counter()
        vectors = list(model.embed(texts))
        elapsed_ms = (time.perf_counter() - start) * 1000
        # fastembed doesn't report per-text timing; split the batch's
        # measured latency evenly as a reasonable approximation.
        per_text_latency_ms = max(1, int(elapsed_ms / max(len(texts), 1)))

        return [
            EmbeddingResult(
                vector=[float(x) for x in vector],
                dimensions=len(vector),
                token_count=token_counts[i],
                latency_ms=per_text_latency_ms,
                cost_usd=None,  # local inference — no per-call provider cost
            )
            for i, vector in enumerate(vectors)
        ]
