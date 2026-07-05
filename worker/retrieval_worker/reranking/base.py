"""Shared reranking provider interface (docs/05-task.md Phase 13;
docs/02-architecture.md sections 71-74 Reranking Architecture).

A cross-encoder scores a (query, candidate_text) pair *jointly* — the
whole reason reranking improves precision over the embedding-based
retrieval score, which encodes query and chunk independently and only
ever compares their vectors afterward. Every provider here takes the
same shape in and out regardless of local vs. cloud, ONNX vs. HTTP.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RerankHit:
    chunk_id: str
    score: float


class ProviderNotConfiguredError(Exception):
    pass


class RerankProvider(ABC):
    provider_name: str

    @abstractmethod
    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[RerankHit]:
        """`candidates` is a list of `(chunk_id, text)` pairs. Returns a
        `RerankHit` per candidate, sorted by score descending (higher is
        always better, regardless of provider)."""
        raise NotImplementedError
