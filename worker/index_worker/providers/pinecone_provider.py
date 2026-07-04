"""Pinecone index provider (docs/05-task.md Phase 8). Real HTTP
integration against Pinecone's documented serverless API — not a stub —
but this dev environment has no paid Pinecone API key configured, so
it's exercised live only when `PINECONE_API_KEY` is set (see
index_worker/tests, which skip via `pytest.mark.skipif` rather than
mocking the HTTP layer, the same convention Phase 7's OpenAI/Voyage/Jina
tests use).

Pinecone only supports its own managed ANN index (no user-selectable
index_type); `hnsw` is accepted as the conventional label since that's
what Pinecone's serverless index uses internally, everything else raises
`UnsupportedIndexTypeError`.
"""

import httpx

from index_worker.providers.base import (
    IndexStats,
    ProviderNotConfiguredError,
    UnsupportedIndexTypeError,
    VectorIndexProvider,
    VectorRecord,
)

_CONTROL_PLANE = "https://api.pinecone.io"
_API_VERSION = "2024-10"
_SUPPORTED_INDEX_TYPES = {"hnsw"}


class PineconeProvider(VectorIndexProvider):
    provider_name = "pinecone"

    def __init__(self, api_key: str | None, cloud: str = "aws", region: str = "us-east-1") -> None:
        if not api_key:
            raise ProviderNotConfiguredError("PINECONE_API_KEY is not configured.")
        self._headers = {
            "Api-Key": api_key,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": _API_VERSION,
        }
        self._cloud = cloud
        self._region = region

    def _index_host(self, namespace: str) -> str | None:
        response = httpx.get(
            f"{_CONTROL_PLANE}/indexes/{namespace}", headers=self._headers, timeout=30.0
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()["host"]

    def create_or_rebuild(
        self, namespace: str, index_type: str, dimensions: int, records: list[VectorRecord]
    ) -> IndexStats:
        if index_type not in _SUPPORTED_INDEX_TYPES:
            raise UnsupportedIndexTypeError(
                f"pinecone does not support index_type '{index_type}'."
            )

        if self._index_host(namespace) is not None:
            httpx.delete(
                f"{_CONTROL_PLANE}/indexes/{namespace}", headers=self._headers, timeout=30.0
            ).raise_for_status()

        httpx.post(
            f"{_CONTROL_PLANE}/indexes",
            headers=self._headers,
            json={
                "name": namespace,
                "dimension": dimensions,
                "metric": "cosine",
                "spec": {"serverless": {"cloud": self._cloud, "region": self._region}},
            },
            timeout=30.0,
        ).raise_for_status()

        host = self._index_host(namespace)
        if records:
            httpx.post(
                f"https://{host}/vectors/upsert",
                headers=self._headers,
                json={
                    "vectors": [
                        {"id": r.chunk_id, "values": r.vector, "metadata": r.metadata}
                        for r in records
                    ]
                },
                timeout=60.0,
            ).raise_for_status()

        return IndexStats(
            vector_count=len(records), dimensions=dimensions, extra={"index_type": index_type}
        )

    def delete(self, namespace: str) -> None:
        if self._index_host(namespace) is not None:
            httpx.delete(
                f"{_CONTROL_PLANE}/indexes/{namespace}", headers=self._headers, timeout=30.0
            ).raise_for_status()

    def stats(self, namespace: str) -> IndexStats:
        host = self._index_host(namespace)
        if host is None:
            return IndexStats(vector_count=0, dimensions=0, extra={"exists": False})
        response = httpx.post(
            f"https://{host}/describe_index_stats", headers=self._headers, json={}, timeout=30.0
        )
        response.raise_for_status()
        payload = response.json()
        return IndexStats(
            vector_count=payload.get("totalVectorCount", 0),
            dimensions=payload.get("dimension", 0),
            extra={"exists": True},
        )

    def health_check(self) -> bool:
        response = httpx.get(f"{_CONTROL_PLANE}/indexes", headers=self._headers, timeout=10.0)
        response.raise_for_status()
        return True
