"""Unit tests for embedding providers (docs/05-task.md Phase 7). The
local (fastembed/ONNX) providers run for real — no mocks. Cloud
providers (OpenAI/Voyage/Jina) are real HTTP integrations too, but this
environment has no paid API keys configured for them, so those tests
skip via `pytest.mark.skipif` rather than mocking the HTTP layer — the
same convention `test_ocr.py` uses for missing local binaries.
"""

import os

import pytest

from embedding_worker.providers.base import ProviderNotConfiguredError
from embedding_worker.providers.cloud import JinaEmbeddingProvider, OpenAIEmbeddingProvider
from embedding_worker.providers.factory import default_model, get_provider
from embedding_worker.providers.local import LocalEmbeddingProvider


def test_local_provider_embeds_real_texts():
    provider = LocalEmbeddingProvider("bge")
    results = provider.embed(["hello world", "a second, longer sentence about testing"])

    assert len(results) == 2
    for result in results:
        assert result.dimensions == 384
        assert len(result.vector) == 384
        assert result.token_count > 0
        assert result.latency_ms >= 1
        assert result.cost_usd is None


def test_local_provider_rejects_unknown_provider_name():
    with pytest.raises(ValueError):
        LocalEmbeddingProvider("not-a-real-provider")


def test_factory_default_model_known_for_every_registered_provider():
    for provider in ("bge", "e5", "nomic", "openai", "voyage", "jina"):
        assert default_model(provider)


def test_factory_get_provider_returns_local_provider_without_api_key():
    provider = get_provider("bge")
    assert isinstance(provider, LocalEmbeddingProvider)


def test_factory_raises_for_unknown_provider():
    with pytest.raises(ValueError):
        get_provider("not-a-real-provider")


def test_openai_provider_raises_when_not_configured():
    with pytest.raises(ProviderNotConfiguredError):
        OpenAIEmbeddingProvider("text-embedding-3-small", api_key=None)


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not configured in this environment",
)
def test_openai_provider_embeds_real_texts_live():
    provider = OpenAIEmbeddingProvider(
        "text-embedding-3-small", api_key=os.environ["OPENAI_API_KEY"]
    )
    results = provider.embed(["hello world"])
    assert len(results) == 1
    assert results[0].dimensions > 0
    assert results[0].cost_usd is not None


@pytest.mark.skipif(
    not os.environ.get("VOYAGE_API_KEY"),
    reason="VOYAGE_API_KEY not configured in this environment",
)
def test_voyage_provider_embeds_real_texts_live():
    from embedding_worker.providers.cloud import VoyageEmbeddingProvider

    provider = VoyageEmbeddingProvider("voyage-2", api_key=os.environ["VOYAGE_API_KEY"])
    results = provider.embed(["hello world"])
    assert len(results) == 1
    assert results[0].dimensions > 0


@pytest.mark.skipif(
    not os.environ.get("JINA_API_KEY"),
    reason="JINA_API_KEY not configured in this environment",
)
def test_jina_provider_embeds_real_texts_live():
    provider = JinaEmbeddingProvider(
        "jina-embeddings-v2-base-en", api_key=os.environ["JINA_API_KEY"]
    )
    results = provider.embed(["hello world"])
    assert len(results) == 1
    assert results[0].dimensions > 0
