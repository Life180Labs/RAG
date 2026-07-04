"""Vector index provider interface (docs/05-task.md Phase 8;
docs/02-architecture.md section 43).

Every provider — PgVector (data already lives in Postgres, no copy
needed) or an external store (Qdrant, Chroma, Pinecone) — implements the
same `create_or_rebuild`/`delete`/`stats`/`health_check` contract so
`index_worker.tasks` never branches on provider identity.
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


class VectorIndexProviderError(RuntimeError):
    pass


class ProviderNotConfiguredError(VectorIndexProviderError):
    """Raised when a cloud provider is selected but its API key is not set."""


class UnsupportedIndexTypeError(VectorIndexProviderError):
    """Raised when a provider doesn't support the requested index_type
    (e.g. pgvector has no native PQ support)."""
