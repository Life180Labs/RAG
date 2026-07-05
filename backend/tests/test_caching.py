"""Phase 17 (Intelligent Caching) backend tests: Prompt Cache, Semantic
Cache, and the Metadata/API Cache example (`prompt-templates`). The
Retrieval Cache lives entirely in the worker and is tested there
(`worker/tests/test_retrieval_cache.py`).
"""

import uuid

import pytest

from app.core.cache import metrics, semantic
from app.core.cache.keys import hash_text, prompt_cache_key
from app.core.cache.store import CacheStore
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.models.prompt import Prompt, PromptTemplate
from tests.test_llm_requests import (
    _auth,
    _build_prompt,
    _completions_path,
    _create_and_complete_retrieval,
    _create_repository_chain,
    _register_and_login,
    _seed_index_chain,
)


@pytest.mark.asyncio
async def test_second_identical_completion_is_a_prompt_cache_hit(client):
    token = await _register_and_login(client, "prompt-cache-owner@example.com")
    document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )
    prompt_id = await _build_prompt(client, token, document_id, vector_index_id, retrieval_id)

    # This test's seeded chunk/system-prompt text is fixed, so a prior
    # run within the same `prompt_cache_ttl_seconds` window would leave a
    # real cache entry behind and turn this test's "first" call into a
    # false hit. Clear it explicitly (using the real key-building/delete
    # path, not a Redis FLUSHALL) so this test's own miss->hit transition
    # is what's actually being observed.
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        prompt = await session.get(Prompt, uuid.UUID(prompt_id))
        stale_key = prompt_cache_key(
            prompt.rendered_prompt,
            "ollama",
            "deepseek-r1:1.5b",
            hash_text(prompt.rendered_context or ""),
        )
    await CacheStore("prompt", settings.prompt_cache_ttl_seconds).delete(stale_key)

    stats_before = await metrics.get_stats()

    first = await client.post(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        json={"provider": "ollama", "model": "deepseek-r1:1.5b"},
        headers=_auth(token),
    )
    assert first.status_code == 200, first.text
    first_body = first.json()["data"]
    assert first_body["status"] == "completed"
    assert first_body["latency_ms"] > 0

    stats_after_first = await metrics.get_stats()
    assert stats_after_first["prompt"]["misses"] == stats_before["prompt"]["misses"] + 1

    second = await client.post(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        json={"provider": "ollama", "model": "deepseek-r1:1.5b"},
        headers=_auth(token),
    )
    assert second.status_code == 200, second.text
    second_body = second.json()["data"]
    assert second_body["status"] == "completed"
    assert second_body["output_text"] == first_body["output_text"]
    # Served straight from cache — no real gateway round trip this time.
    assert second_body["latency_ms"] == 0

    stats_after_second = await metrics.get_stats()
    assert stats_after_second["prompt"]["hits"] == stats_after_first["prompt"]["hits"] + 1


@pytest.mark.asyncio
async def test_semantic_cache_find_similar_scoped_to_vector_index(client):
    token = await _register_and_login(client, "semantic-cache-owner@example.com")
    document_id, vector_index_id, _chunk_id = await _seed_index_chain(client, token)

    async with AsyncSessionLocal() as session:
        document = await session.get(Document, uuid.UUID(document_id))
        repository_id = document.repository_id

        vector = [0.1] * 384
        await semantic.upsert_entry(
            session,
            repository_id=repository_id,
            vector_index_id=uuid.UUID(vector_index_id),
            query_text="how many leave days?",
            query_vector=vector,
            answer_text="20 days.",
        )
        await session.commit()

        hit = await semantic.find_similar(session, uuid.UUID(vector_index_id), vector)
        assert hit is not None
        assert hit.answer_text == "20 days."

        far_vector = [-0.1] * 384
        miss = await semantic.find_similar(session, uuid.UUID(vector_index_id), far_vector)
        assert miss is None

        # A different vector index must never see another index's cached
        # answer, even with an identical query embedding.
        other_index_miss = await semantic.find_similar(session, uuid.uuid4(), vector)
        assert other_index_miss is None


@pytest.mark.asyncio
async def test_prompt_templates_list_is_cached_and_invalidated_on_write(client):
    token = await _register_and_login(client, "metadata-cache-owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    settings = get_settings()
    assert settings.cache_enabled

    create_1 = await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates",
        json={"name": "greeting", "system_prompt": "Be nice."},
        headers=_auth(token),
    )
    assert create_1.status_code == 200
    template_1_id = create_1.json()["data"]["id"]

    first_list = await client.get(
        f"/api/v1/repositories/{repository_id}/prompt-templates", headers=_auth(token)
    )
    assert len(first_list.json()["data"]) == 1

    # Insert a second template directly via the ORM, bypassing the create
    # endpoint (and therefore its cache invalidation) entirely — proves
    # the *next* GET is actually served from cache, not just correct by
    # coincidence.
    async with AsyncSessionLocal() as session:
        session.add(
            PromptTemplate(
                repository_id=uuid.UUID(repository_id),
                name="farewell",
                version=1,
                system_prompt="Say goodbye.",
                is_active=True,
            )
        )
        await session.commit()

    stale_list = await client.get(
        f"/api/v1/repositories/{repository_id}/prompt-templates", headers=_auth(token)
    )
    assert len(stale_list.json()["data"]) == 1

    # Archiving goes through the real invalidation path, so the next
    # read must reflect both templates.
    await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates/{template_1_id}/archive",
        headers=_auth(token),
    )

    fresh_list = await client.get(
        f"/api/v1/repositories/{repository_id}/prompt-templates", headers=_auth(token)
    )
    assert len(fresh_list.json()["data"]) == 2


@pytest.mark.asyncio
async def test_cache_stats_endpoint_returns_every_cache_type(client):
    token = await _register_and_login(client, "cache-stats-owner@example.com")
    response = await client.get("/api/v1/cache/stats", headers=_auth(token))
    assert response.status_code == 200
    data = response.json()["data"]
    assert set(data.keys()) == {"retrieval", "prompt", "semantic", "metadata"}
    for stats in data.values():
        assert set(stats.keys()) == {"hits", "misses", "hit_ratio"}
