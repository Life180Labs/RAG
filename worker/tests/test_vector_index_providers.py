"""Unit tests for vector index providers (docs/05-task.md Phase 8). The
local providers (PgVector, real HTTP against self-hosted Qdrant/Chroma)
run for real — no mocks — as long as those services are reachable
(docker-compose provisions all three; CI provisions them as service
containers too). Pinecone is a real HTTP integration too, but this
environment has no paid API key configured, so it's skipped via
`pytest.mark.skipif`, the same convention Phase 7's cloud providers use.
"""

import os
import socket
import uuid
from urllib.parse import urlparse

import pytest

from common.config import get_worker_settings
from common.db import SessionLocal
from index_worker.providers.base import (
    ProviderNotConfiguredError,
    UnsupportedIndexTypeError,
    VectorRecord,
)
from index_worker.providers.chroma_provider import ChromaProvider
from index_worker.providers.factory import get_provider
from index_worker.providers.pgvector_provider import PgVectorProvider
from index_worker.providers.pinecone_provider import PineconeProvider
from index_worker.providers.qdrant_provider import QdrantProvider


def _reachable(url: str) -> bool:
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=2):
            return True
    except OSError:
        return False


_settings = get_worker_settings()
_qdrant_up = _reachable(_settings.qdrant_url)
_chroma_up = _reachable(_settings.chroma_url)


def test_pgvector_create_stats_delete_round_trip():
    with SessionLocal() as session:
        provider = PgVectorProvider(session)
        namespace = str(uuid.uuid4())

        created = provider.create_or_rebuild(namespace, "hnsw", 8, [])
        assert created.extra["index_type"] == "hnsw"

        stats = provider.stats(namespace)
        assert stats.extra["index_exists"] is True

        provider.delete(namespace)
        after = provider.stats(namespace)
        assert after.extra["index_exists"] is False


def test_pgvector_rejects_pq():
    with SessionLocal() as session:
        provider = PgVectorProvider(session)
        with pytest.raises(UnsupportedIndexTypeError):
            provider.create_or_rebuild(str(uuid.uuid4()), "pq", 8, [])


def test_pgvector_health_check():
    with SessionLocal() as session:
        assert PgVectorProvider(session).health_check() is True


@pytest.mark.skipif(not _qdrant_up, reason="qdrant is not reachable in this environment")
def test_qdrant_create_stats_delete_round_trip():
    provider = QdrantProvider(_settings.qdrant_url)
    namespace = f"test-{uuid.uuid4()}"
    records = [VectorRecord(chunk_id=str(uuid.uuid4()), vector=[0.1] * 8, metadata={"a": "b"})]

    created = provider.create_or_rebuild(namespace, "hnsw", 8, records)
    assert created.vector_count == 1

    stats = provider.stats(namespace)
    assert stats.vector_count == 1

    provider.delete(namespace)
    after = provider.stats(namespace)
    assert after.extra["exists"] is False


@pytest.mark.skipif(not _qdrant_up, reason="qdrant is not reachable in this environment")
def test_qdrant_rejects_ivf_flat():
    provider = QdrantProvider(_settings.qdrant_url)
    with pytest.raises(UnsupportedIndexTypeError):
        provider.create_or_rebuild(f"test-{uuid.uuid4()}", "ivf_flat", 8, [])


@pytest.mark.skipif(not _chroma_up, reason="chroma is not reachable in this environment")
def test_chroma_create_stats_delete_round_trip():
    provider = ChromaProvider(_settings.chroma_url)
    namespace = f"test-{uuid.uuid4()}"
    records = [VectorRecord(chunk_id=str(uuid.uuid4()), vector=[0.1] * 8, metadata={"a": "b"})]

    created = provider.create_or_rebuild(namespace, "hnsw", 8, records)
    assert created.vector_count == 1

    stats = provider.stats(namespace)
    assert stats.vector_count == 1

    provider.delete(namespace)
    after = provider.stats(namespace)
    assert after.extra["exists"] is False


@pytest.mark.skipif(not _chroma_up, reason="chroma is not reachable in this environment")
def test_chroma_rejects_flat():
    provider = ChromaProvider(_settings.chroma_url)
    with pytest.raises(UnsupportedIndexTypeError):
        provider.create_or_rebuild(f"test-{uuid.uuid4()}", "flat", 8, [])


def test_pinecone_provider_raises_when_not_configured():
    with pytest.raises(ProviderNotConfiguredError):
        PineconeProvider(api_key=None)


@pytest.mark.skipif(
    not os.environ.get("PINECONE_API_KEY"),
    reason="PINECONE_API_KEY not configured in this environment",
)
def test_pinecone_create_stats_delete_round_trip_live():
    provider = PineconeProvider(api_key=os.environ["PINECONE_API_KEY"])
    namespace = f"test-{uuid.uuid4()}"
    records = [VectorRecord(chunk_id=str(uuid.uuid4()), vector=[0.1] * 8, metadata={"a": "b"})]

    created = provider.create_or_rebuild(namespace, "hnsw", 8, records)
    assert created.vector_count == 1
    provider.delete(namespace)


def test_factory_returns_pgvector_by_default():
    with SessionLocal() as session:
        provider = get_provider("pgvector", session)
        assert provider.provider_name == "pgvector"


def test_factory_raises_for_unknown_provider():
    with SessionLocal() as session:
        with pytest.raises(ValueError):
            get_provider("not-a-real-provider", session)
