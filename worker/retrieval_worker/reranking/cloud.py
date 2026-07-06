"""Cloud reranking providers (docs/05-task.md Phase 13).

Real HTTP integrations against each provider's documented rerank API —
not stubs — but this dev environment has no paid API keys configured
for either, so they're exercised live only when the corresponding
`{PROVIDER}_API_KEY` env var is set (the same convention Phase 7's
cloud embedding providers established; worker tests skip via
`pytest.mark.skipif` rather than mocking the HTTP layer). Jina reuses
the same `JINA_API_KEY` Phase 7's `JinaEmbeddingProvider` already
gates on, since it's the same provider account; Cohere is a new key.
"""

import httpx

from common.config import get_worker_settings
from retrieval_worker.reranking.base import ProviderNotConfiguredError, RerankHit, RerankProvider


class CohereRerankProvider(RerankProvider):
    provider_name = "cohere"
    endpoint = "https://api.cohere.com/v1/rerank"

    def __init__(
        self, model_name: str = "rerank-english-v3.0", api_key_override: str | None = None
    ) -> None:
        api_key = api_key_override or get_worker_settings().cohere_api_key
        if not api_key:
            raise ProviderNotConfiguredError("COHERE_API_KEY is not configured.")
        self.model_name = model_name
        self._api_key = api_key

    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[RerankHit]:
        if not candidates:
            return []
        documents = [text for _, text in candidates]
        response = httpx.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self.model_name, "query": query, "documents": documents},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        hits = [
            RerankHit(chunk_id=candidates[item["index"]][0], score=float(item["relevance_score"]))
            for item in payload["results"]
        ]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)


class JinaRerankProvider(RerankProvider):
    provider_name = "jina"
    endpoint = "https://api.jina.ai/v1/rerank"

    def __init__(
        self,
        model_name: str = "jina-reranker-v2-base-multilingual",
        api_key_override: str | None = None,
    ) -> None:
        api_key = api_key_override or get_worker_settings().jina_api_key
        if not api_key:
            raise ProviderNotConfiguredError("JINA_API_KEY is not configured.")
        self.model_name = model_name
        self._api_key = api_key

    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[RerankHit]:
        if not candidates:
            return []
        documents = [text for _, text in candidates]
        response = httpx.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self.model_name, "query": query, "documents": documents},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        hits = [
            RerankHit(chunk_id=candidates[item["index"]][0], score=float(item["relevance_score"]))
            for item in payload["results"]
        ]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)
