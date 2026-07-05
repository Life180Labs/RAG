"""Unit tests for reranking providers (docs/05-task.md Phase 13). The
local (fastembed/ONNX, FlashRank) providers run for real — no mocks.
Cloud providers (Cohere/Jina) are real HTTP integrations too, but this
environment has no paid API keys configured for them, so those tests
skip via `pytest.mark.skipif` rather than mocking the HTTP layer — the
same convention `test_embedding_providers.py` uses.
"""

import os

import pytest

from retrieval_worker.reranking.base import ProviderNotConfiguredError
from retrieval_worker.reranking.cloud import CohereRerankProvider, JinaRerankProvider
from retrieval_worker.reranking.factory import get_provider
from retrieval_worker.reranking.flashrank_provider import FlashRankProvider
from retrieval_worker.reranking.local import LocalRerankProvider

_CANDIDATES = [
    ("a", "Employees are entitled to twenty vacation days per year."),
    ("b", "Remote work requires manager approval through the HR portal."),
]


def test_local_cross_encoder_ranks_relevant_candidate_first():
    provider = LocalRerankProvider("cross_encoder")
    hits = provider.rerank("vacation policy", _CANDIDATES)
    assert [hit.chunk_id for hit in hits] == ["a", "b"]
    assert hits[0].score > hits[1].score


def test_local_provider_rejects_unknown_provider_name():
    with pytest.raises(ValueError):
        LocalRerankProvider("not-a-real-provider")


def test_local_provider_returns_empty_for_empty_candidates():
    provider = LocalRerankProvider("cross_encoder")
    assert provider.rerank("anything", []) == []


def test_flashrank_ranks_relevant_candidate_first():
    provider = FlashRankProvider()
    hits = provider.rerank("vacation policy", _CANDIDATES)
    assert [hit.chunk_id for hit in hits] == ["a", "b"]
    assert hits[0].score > hits[1].score


def test_flashrank_returns_empty_for_empty_candidates():
    provider = FlashRankProvider()
    assert provider.rerank("anything", []) == []


def test_cohere_provider_raises_when_not_configured(monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    from common.config import get_worker_settings

    get_worker_settings.cache_clear()
    with pytest.raises(ProviderNotConfiguredError):
        CohereRerankProvider()
    get_worker_settings.cache_clear()


def test_factory_returns_local_provider_without_api_key():
    provider = get_provider("cross_encoder")
    assert isinstance(provider, LocalRerankProvider)


def test_factory_returns_flashrank_provider():
    provider = get_provider("flashrank")
    assert isinstance(provider, FlashRankProvider)


def test_factory_raises_for_unknown_provider():
    with pytest.raises(ValueError):
        get_provider("not-a-real-provider")


@pytest.mark.skipif(
    not os.environ.get("COHERE_API_KEY"), reason="COHERE_API_KEY not configured in this environment"
)
def test_cohere_provider_reranks_real_candidates_live():
    provider = CohereRerankProvider()
    hits = provider.rerank("vacation policy", _CANDIDATES)
    assert hits[0].chunk_id == "a"


@pytest.mark.skipif(
    not os.environ.get("JINA_API_KEY"), reason="JINA_API_KEY not configured in this environment"
)
def test_jina_provider_reranks_real_candidates_live():
    provider = JinaRerankProvider()
    hits = provider.rerank("vacation policy", _CANDIDATES)
    assert hits[0].chunk_id == "a"
