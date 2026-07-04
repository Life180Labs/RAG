"""Qdrant index provider (docs/05-task.md Phase 8). Real HTTP client
against a self-hosted Qdrant instance (`qdrant/qdrant` in
docker-compose.yml) — no API key needed for local/self-hosted use.

Qdrant's native ANN index is always HNSW; there's no separate "ivf_flat"
or "pq" index type to select the way pgvector has distinct access
methods. `flat` is supported by disabling the HNSW graph
(`hnsw_config.m = 0`, forcing exact brute-force search) — a real Qdrant
configuration, not a placeholder. `ivf_flat` and `pq` aren't concepts
Qdrant exposes this way, so requesting them raises
`UnsupportedIndexTypeError`.
"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, HnswConfigDiff, PointStruct, VectorParams

from index_worker.providers.base import (
    IndexStats,
    UnsupportedIndexTypeError,
    VectorIndexProvider,
    VectorRecord,
)

_SUPPORTED_INDEX_TYPES = {"hnsw", "flat"}


class QdrantProvider(VectorIndexProvider):
    provider_name = "qdrant"

    def __init__(self, url: str) -> None:
        self._client = QdrantClient(url=url)

    def create_or_rebuild(
        self, namespace: str, index_type: str, dimensions: int, records: list[VectorRecord]
    ) -> IndexStats:
        if index_type not in _SUPPORTED_INDEX_TYPES:
            raise UnsupportedIndexTypeError(f"qdrant does not support index_type '{index_type}'.")

        if self._client.collection_exists(namespace):
            self._client.delete_collection(namespace)

        hnsw_config = HnswConfigDiff(m=0) if index_type == "flat" else None
        self._client.create_collection(
            collection_name=namespace,
            vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
            hnsw_config=hnsw_config,
        )

        if records:
            self._client.upsert(
                collection_name=namespace,
                points=[
                    PointStruct(id=record.chunk_id, vector=record.vector, payload=record.metadata)
                    for record in records
                ],
            )

        return IndexStats(
            vector_count=len(records), dimensions=dimensions, extra={"index_type": index_type}
        )

    def delete(self, namespace: str) -> None:
        if self._client.collection_exists(namespace):
            self._client.delete_collection(namespace)

    def stats(self, namespace: str) -> IndexStats:
        if not self._client.collection_exists(namespace):
            return IndexStats(vector_count=0, dimensions=0, extra={"exists": False})
        info = self._client.get_collection(namespace)
        return IndexStats(
            vector_count=info.points_count or 0,
            dimensions=info.config.params.vectors.size,
            extra={"exists": True},
        )

    def health_check(self) -> bool:
        self._client.get_collections()
        return True
