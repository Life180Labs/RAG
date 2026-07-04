"""Cloud embedding providers (docs/05-task.md Phase 7).

Real HTTP integrations against each provider's documented embeddings
API — not stubs — but this dev environment has no paid API keys
configured for any of them, so they're exercised live only when the
corresponding `{PROVIDER}_API_KEY` env var is set (see
worker/tests, which skip via `pytest.mark.skipif` rather than
mocking the HTTP layer, the same convention `test_ocr.py` uses for
missing local binaries).

Pricing is hardcoded per model from each provider's published rate at
the time of writing and should be revisited if a provider changes
pricing — this is the same "best real number available" approach
`docs/03-database.md`'s cost tracking already documents as approximate.
"""

import time

import httpx
from openai import OpenAI

from common.embedding_providers.base import (
    EmbeddingProvider,
    EmbeddingResult,
    ProviderNotConfiguredError,
)
from common.tokenizer import count_tokens

# USD per 1,000 tokens, per model.
OPENAI_PRICING_PER_1K: dict[str, float] = {
    "text-embedding-3-small": 0.00002,
    "text-embedding-3-large": 0.00013,
    "text-embedding-ada-002": 0.0001,
}
VOYAGE_PRICING_PER_1K: dict[str, float] = {
    "voyage-2": 0.0001,
    "voyage-large-2": 0.00012,
}
JINA_PRICING_PER_1K: dict[str, float] = {
    "jina-embeddings-v2-base-en": 0.00002,
    "jina-embeddings-v3": 0.00002,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    provider_name = "openai"

    def __init__(self, model_name: str, api_key: str | None) -> None:
        if not api_key:
            raise ProviderNotConfiguredError("OPENAI_API_KEY is not configured.")
        self.model_name = model_name
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        start = time.perf_counter()
        response = self._client.embeddings.create(model=self.model_name, input=texts)
        elapsed_ms = (time.perf_counter() - start) * 1000
        per_text_latency_ms = max(1, int(elapsed_ms / max(len(texts), 1)))
        price_per_1k = OPENAI_PRICING_PER_1K.get(self.model_name, 0.0)

        results = []
        for i, item in enumerate(response.data):
            tokens = count_tokens(texts[i])
            results.append(
                EmbeddingResult(
                    vector=list(item.embedding),
                    dimensions=len(item.embedding),
                    token_count=tokens,
                    latency_ms=per_text_latency_ms,
                    cost_usd=round(tokens / 1000 * price_per_1k, 8),
                )
            )
        return results


class _RestEmbeddingProvider(EmbeddingProvider):
    """Shared HTTP-call shape for Voyage and Jina, whose embeddings APIs
    both follow the same `{"input": [...], "model": "..."}` ->
    `{"data": [{"embedding": [...]}]}` contract as OpenAI's."""

    endpoint: str

    def __init__(self, provider_name: str, model_name: str, api_key: str | None) -> None:
        if not api_key:
            raise ProviderNotConfiguredError(
                f"{provider_name.upper()}_API_KEY is not configured."
            )
        self.provider_name = provider_name
        self.model_name = model_name
        self._api_key = api_key

    def _pricing(self) -> dict[str, float]:
        raise NotImplementedError

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        start = time.perf_counter()
        response = httpx.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"input": texts, "model": self.model_name},
            timeout=30.0,
        )
        response.raise_for_status()
        elapsed_ms = (time.perf_counter() - start) * 1000
        per_text_latency_ms = max(1, int(elapsed_ms / max(len(texts), 1)))
        price_per_1k = self._pricing().get(self.model_name, 0.0)

        payload = response.json()
        results = []
        for i, item in enumerate(payload["data"]):
            vector = item["embedding"]
            tokens = count_tokens(texts[i])
            results.append(
                EmbeddingResult(
                    vector=list(vector),
                    dimensions=len(vector),
                    token_count=tokens,
                    latency_ms=per_text_latency_ms,
                    cost_usd=round(tokens / 1000 * price_per_1k, 8),
                )
            )
        return results


class VoyageEmbeddingProvider(_RestEmbeddingProvider):
    endpoint = "https://api.voyageai.com/v1/embeddings"

    def __init__(self, model_name: str, api_key: str | None) -> None:
        super().__init__("voyage", model_name, api_key)

    def _pricing(self) -> dict[str, float]:
        return VOYAGE_PRICING_PER_1K


class JinaEmbeddingProvider(_RestEmbeddingProvider):
    endpoint = "https://api.jina.ai/v1/embeddings"

    def __init__(self, model_name: str, api_key: str | None) -> None:
        super().__init__("jina", model_name, api_key)

    def _pricing(self) -> dict[str, float]:
        return JINA_PRICING_PER_1K
