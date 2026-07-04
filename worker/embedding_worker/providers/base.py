"""Embedding provider interface (docs/05-task.md Phase 7;
docs/02-architecture.md section 41).

Every provider — local ONNX model or cloud API — implements `.embed()`
with the same signature so `embedding_worker.tasks` never branches on
provider identity. `EmbeddingResult` carries per-text vector, true
dimensionality, token count, latency, and cost so the caller can persist
and aggregate them without knowing provider-specific response shapes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    vector: list[float]
    dimensions: int
    token_count: int
    latency_ms: int
    cost_usd: float | None


class EmbeddingProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed a batch of texts, returning one EmbeddingResult per input
        in the same order."""


class EmbeddingProviderError(RuntimeError):
    pass


class ProviderNotConfiguredError(EmbeddingProviderError):
    """Raised when a cloud provider is selected but its API key is not set."""
