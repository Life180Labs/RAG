"""Rerank provider factory (docs/05-task.md Phase 13).

Mirrors `common.embedding_providers.factory`'s shape: local providers
(`cross_encoder`, `bge`, `flashrank`) never fail to construct — they
have no external dependency beyond cached/downloadable ONNX weights;
cloud providers (`cohere`, `jina`) raise `ProviderNotConfiguredError`
when their API key isn't set, which `execute_retrieval` surfaces as a
failed retrieval rather than crashing.
"""

from retrieval_worker.reranking.base import RerankProvider
from retrieval_worker.reranking.cloud import CohereRerankProvider, JinaRerankProvider
from retrieval_worker.reranking.flashrank_provider import FlashRankProvider
from retrieval_worker.reranking.local import LOCAL_MODEL_NAMES, LocalRerankProvider

DEFAULT_PROVIDER = "cross_encoder"

_LOCAL_PROVIDERS = set(LOCAL_MODEL_NAMES)


def get_provider(provider: str) -> RerankProvider:
    if provider in _LOCAL_PROVIDERS:
        return LocalRerankProvider(provider)
    if provider == "flashrank":
        return FlashRankProvider()
    if provider == "cohere":
        return CohereRerankProvider()
    if provider == "jina":
        return JinaRerankProvider()
    raise ValueError(f"Unknown rerank provider '{provider}'.")
