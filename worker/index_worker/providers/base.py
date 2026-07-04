"""Vector index provider interface (docs/05-task.md Phase 8 build side,
Phase 9 search side; docs/02-architecture.md sections 43 and 56).

Every provider — PgVector (data already lives in Postgres, no copy
needed) or an external store (Qdrant, Chroma, Pinecone) — implements the
same `create_or_rebuild`/`delete`/`stats`/`health_check`/`search`
contract so `index_worker.tasks`/`retrieval_worker.tasks` never branch
on provider identity.

`search()`'s `metric` support is honestly asymmetric across providers,
same as `index_type` in Phase 8: PgVector can select cosine/dot/euclidean
per query because the raw vectors always live in Postgres (any of
pgvector's three distance operators is a valid query regardless of which
operator class the ANN index itself was built with), but Qdrant/Chroma/
Pinecone all fix their distance metric to cosine at collection/index
creation time (Phase 8's `create_or_rebuild` never exposed a metric
choice), so requesting `dot`/`euclidean` against those three raises
`UnsupportedMetricError` — a real per-provider limitation, not a
deferral choice.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VectorRecord:
    chunk_id: str
    vector: list[float]
    metadata: dict


@dataclass
class IndexStats:
    vector_count: int
    dimensions: int
    extra: dict


@dataclass
class SearchHit:
    chunk_id: str
    score: float
    metadata: dict


class VectorIndexProvider(ABC):
    provider_name: str

    @abstractmethod
    def create_or_rebuild(
        self, namespace: str, index_type: str, dimensions: int, records: list[VectorRecord]
    ) -> IndexStats:
        """Creates the index/collection if absent, or rebuilds it in place
        if it already exists, then (re)loads every record."""

    @abstractmethod
    def delete(self, namespace: str) -> None:
        """Removes the index/collection. No-op if it doesn't exist."""

    @abstractmethod
    def stats(self, namespace: str) -> IndexStats:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """True if the provider's backing store is reachable."""

    @abstractmethod
    def search(
        self,
        namespace: str,
        query_vector: list[float],
        top_k: int,
        metric: str,
        score_threshold: float | None,
        metadata_filter: dict | None,
    ) -> list[SearchHit]:
        """Ranked nearest-neighbor search, best match first. `score` is
        always normalized so *higher is better* regardless of metric
        (cosine/dot similarity as-is; euclidean distance negated), so
        `score_threshold` ("keep hits with score >= threshold") means the
        same thing for every metric. `metadata_filter` is an exact-match
        equality filter over the same keys Phase 8 attaches at build time
        (`heading`, `page`, `language`)."""


class VectorIndexProviderError(RuntimeError):
    pass


class ProviderNotConfiguredError(VectorIndexProviderError):
    """Raised when a cloud provider is selected but its API key is not set."""


class UnsupportedIndexTypeError(VectorIndexProviderError):
    """Raised when a provider doesn't support the requested index_type
    (e.g. pgvector has no native PQ support)."""


class UnsupportedMetricError(VectorIndexProviderError):
    """Raised when a provider's index has a similarity metric fixed at
    build time (Qdrant/Chroma/Pinecone are all cosine-only) that differs
    from the metric requested at search time."""
