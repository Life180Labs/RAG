"""Chroma index provider (docs/05-task.md Phase 8). Real HTTP client
against a self-hosted Chroma instance (`chromadb/chroma` in
docker-compose.yml) — no API key needed for local/self-hosted use.

Chroma's client API doesn't expose a choice of ANN index type at all —
it always uses HNSW (via hnswlib) internally, with no separate
"ivf_flat"/"flat"/"pq" mode. Requesting anything but `hnsw` raises
`UnsupportedIndexTypeError`, a real client limitation rather than a
deferral choice.
"""

import chromadb

from index_worker.providers.base import (
    IndexStats,
    UnsupportedIndexTypeError,
    VectorIndexProvider,
    VectorRecord,
)

_SUPPORTED_INDEX_TYPES = {"hnsw"}


class ChromaProvider(VectorIndexProvider):
    provider_name = "chroma"

    def __init__(self, url: str) -> None:
        parsed_host, _, parsed_port = url.partition("://")[2].partition(":")
        self._client = chromadb.HttpClient(host=parsed_host, port=int(parsed_port or 8000))

    def create_or_rebuild(
        self, namespace: str, index_type: str, dimensions: int, records: list[VectorRecord]
    ) -> IndexStats:
        if index_type not in _SUPPORTED_INDEX_TYPES:
            raise UnsupportedIndexTypeError(f"chroma does not support index_type '{index_type}'.")

        try:
            self._client.delete_collection(namespace)
        except Exception:  # noqa: BLE001 - delete-if-exists; Chroma raises if absent
            pass

        collection = self._client.create_collection(
            name=namespace, metadata={"hnsw:space": "cosine"}
        )

        if records:
            collection.upsert(
                ids=[record.chunk_id for record in records],
                embeddings=[record.vector for record in records],
                metadatas=[record.metadata or {"_empty": True} for record in records],
            )

        return IndexStats(
            vector_count=len(records), dimensions=dimensions, extra={"index_type": index_type}
        )

    def delete(self, namespace: str) -> None:
        try:
            self._client.delete_collection(namespace)
        except Exception:  # noqa: BLE001 - no-op if the collection doesn't exist
            pass

    def stats(self, namespace: str) -> IndexStats:
        try:
            collection = self._client.get_collection(namespace)
        except Exception:  # noqa: BLE001 - collection doesn't exist
            return IndexStats(vector_count=0, dimensions=0, extra={"exists": False})
        return IndexStats(
            vector_count=collection.count(), dimensions=0, extra={"exists": True}
        )

    def health_check(self) -> bool:
        self._client.heartbeat()
        return True
