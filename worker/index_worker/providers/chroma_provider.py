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
    SearchHit,
    UnsupportedIndexTypeError,
    UnsupportedMetricError,
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

    def search(
        self,
        namespace: str,
        query_vector: list[float],
        top_k: int,
        metric: str,
        score_threshold: float | None,
        metadata_filter: dict | None,
    ) -> list[SearchHit]:
        if metric != "cosine":
            raise UnsupportedMetricError(
                "chroma collections are always built with a fixed cosine metric "
                f"(requested '{metric}')."
            )
        try:
            collection = self._client.get_collection(namespace)
        except Exception:  # noqa: BLE001 - collection doesn't exist
            return []

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=metadata_filter or None,
            include=["metadatas", "distances"],
        )
        hits = []
        for chunk_id, distance, metadata in zip(
            results["ids"][0], results["distances"][0], results["metadatas"][0], strict=True
        ):
            # Chroma's "hnsw:space": "cosine" collections report distance
            # as 1 - cosine_similarity, so invert it back to a similarity
            # score for a "higher is better" contract consistent with
            # every other provider.
            score = 1 - distance
            if score_threshold is not None and score < score_threshold:
                continue
            hits.append(SearchHit(chunk_id=chunk_id, score=score, metadata=metadata or {}))
        return hits
