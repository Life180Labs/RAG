import uuid

import pytest

from app.core.citations import build_citations
from app.core.context_window import ContextEntry, build_context_window
from app.core.token_budget import available_context_tokens, count_tokens
from app.db.session import AsyncSessionLocal
from app.models.chunk import Chunk, ChunkSetStatus, ChunkStatus, DocumentChunkSet
from app.models.embedding import EmbeddingVersion, EmbeddingVersionStatus
from app.models.retrieval import Retrieval, RetrievalResult, RetrievalStatus
from app.models.vector_index import VectorIndex, VectorIndexStatus

VALID_PASSWORD = "Str0ng!Passw0rd"


# --- Core module unit tests (no DB) ---------------------------------------


def test_count_tokens_empty_string_is_zero():
    assert count_tokens("") == 0


def test_count_tokens_counts_real_tokens():
    assert count_tokens("hello world") > 0


def test_available_context_tokens_never_negative():
    assert (
        available_context_tokens(
            model_context_window=100,
            system_prompt_tokens=50,
            conversation_tokens=0,
            query_tokens=40,
            response_reserve_tokens=20,
        )
        == 0
    )


def test_available_context_tokens_subtracts_all_budgets():
    assert (
        available_context_tokens(
            model_context_window=1000,
            system_prompt_tokens=100,
            conversation_tokens=50,
            query_tokens=20,
            response_reserve_tokens=200,
        )
        == 630
    )


def _make_result(rank: int, chunk_id: uuid.UUID, score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(
        id=uuid.uuid4(),
        retrieval_id=uuid.uuid4(),
        chunk_id=chunk_id,
        rank=rank,
        score=score,
    )


def _make_chunk(chunk_id: uuid.UUID, text: str, page: int | None = None) -> Chunk:
    return Chunk(
        id=chunk_id,
        chunk_set_id=uuid.uuid4(),
        chunk_index=0,
        text=text,
        char_start=0,
        char_end=len(text),
        token_count=len(text.split()),
        page=page,
        heading=None,
        status=ChunkStatus.READY,
    )


def test_build_context_window_respects_token_budget():
    chunk_a = _make_chunk(uuid.uuid4(), "short text")
    chunk_b = _make_chunk(uuid.uuid4(), " ".join(["word"] * 5000))
    rows = [
        (_make_result(1, chunk_a.id), chunk_a),
        (_make_result(2, chunk_b.id), chunk_b),
    ]
    context_text, entries = build_context_window(
        rows, document_id="doc-1", token_budget=count_tokens("short text") + 5
    )
    assert len(entries) == 1
    assert entries[0].chunk_id == str(chunk_a.id)
    assert "short text" in context_text


def test_build_context_window_deduplicates_by_chunk_id():
    chunk = _make_chunk(uuid.uuid4(), "same chunk twice")
    rows = [
        (_make_result(1, chunk.id), chunk),
        (_make_result(2, chunk.id), chunk),
    ]
    _, entries = build_context_window(rows, document_id="doc-1", token_budget=10_000)
    assert len(entries) == 1


def test_build_context_window_order_by_page_reorders_display():
    chunk_a = _make_chunk(uuid.uuid4(), "chunk from page 3", page=3)
    chunk_b = _make_chunk(uuid.uuid4(), "chunk from page 1", page=1)
    rows = [
        (_make_result(1, chunk_a.id), chunk_a),
        (_make_result(2, chunk_b.id), chunk_b),
    ]
    _, entries = build_context_window(
        rows, document_id="doc-1", token_budget=10_000, order_by_page=True
    )
    assert [e.page for e in entries] == [1, 3]


def test_build_citations_labels_sources_in_order():
    entries = [
        ContextEntry(
            chunk_id="c1",
            document_id="d1",
            text="text",
            tokens=1,
            page=3,
            heading="Intro",
            rank=1,
            confidence=0.8,
        )
    ]
    citations = build_citations(entries, document_filename="handbook.pdf")
    assert citations == [
        {
            "source_label": "Source 1",
            "document_id": "d1",
            "document_filename": "handbook.pdf",
            "page": 3,
            "section": "Intro",
            "chunk_id": "c1",
            "confidence": 0.8,
        }
    ]


# --- API integration tests (real Postgres, rag_test) ----------------------


async def _register_and_login(client, email: str, full_name: str = "Test User") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": full_name},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return login.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_repository_chain(client, token: str, suffix: str = "") -> str:
    org_response = await client.post(
        "/api/v1/organizations",
        json={"name": f"Acme{suffix}", "slug": f"acme{suffix}"},
        headers=_auth(token),
    )
    org_id = org_response.json()["data"]["id"]
    ws_response = await client.post(
        f"/api/v1/organizations/{org_id}/workspaces",
        json={"name": "Eng", "slug": "eng"},
        headers=_auth(token),
    )
    workspace_id = ws_response.json()["data"]["id"]
    proj_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        json={"name": "RAG Studio", "slug": "rag-studio"},
        headers=_auth(token),
    )
    project_id = proj_response.json()["data"]["id"]
    repo_response = await client.post(
        f"/api/v1/projects/{project_id}/repositories",
        json={"name": "Docs", "slug": "docs"},
        headers=_auth(token),
    )
    return repo_response.json()["data"]["id"]


async def _upload_document(
    client,
    token: str,
    repository_id: str,
    filename: str = "report.txt",
    content: bytes = b"hello world",
) -> str:
    response = await client.post(
        f"/api/v1/repositories/{repository_id}/documents",
        headers=_auth(token),
        files={"file": (filename, content, "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


async def _seed_chunk(document_id: str, text: str = "The office is open Monday to Friday.") -> str:
    async with AsyncSessionLocal() as session:
        chunk_set = DocumentChunkSet(
            document_id=uuid.UUID(document_id),
            version=1,
            strategy="recursive",
            config={"max_tokens": 400},
            status=ChunkSetStatus.READY,
            chunk_count=1,
        )
        session.add(chunk_set)
        await session.flush()
        chunk = Chunk(
            chunk_set_id=chunk_set.id,
            chunk_index=0,
            text=text,
            char_start=0,
            char_end=len(text),
            token_count=len(text.split()),
            page=1,
            heading="Policy",
            status=ChunkStatus.READY,
        )
        session.add(chunk)
        await session.commit()
        return str(chunk.id)


async def _seed_index_chain(client, token: str) -> tuple[str, str, str, str]:
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_id = await _seed_chunk(document_id)
    async with AsyncSessionLocal() as session:
        chunk = await session.get(Chunk, uuid.UUID(chunk_id))
        chunk_set_id = chunk.chunk_set_id
        version = EmbeddingVersion(
            chunk_set_id=chunk_set_id,
            document_id=uuid.UUID(document_id),
            provider="bge",
            model="BAAI/bge-small-en-v1.5",
            dimensions=384,
            version=1,
            status=EmbeddingVersionStatus.READY,
            embedding_count=1,
            total_tokens=5,
        )
        session.add(version)
        await session.flush()
        index = VectorIndex(
            embedding_version_id=version.id,
            document_id=uuid.UUID(document_id),
            provider="pgvector",
            index_type="hnsw",
            namespace=str(version.id),
            dimensions=384,
            version=1,
            status=VectorIndexStatus.READY,
            vector_count=1,
        )
        session.add(index)
        await session.commit()
        vector_index_id = str(index.id)
    return repository_id, document_id, vector_index_id, chunk_id


async def _create_and_complete_retrieval(
    client, token: str, document_id: str, vector_index_id: str, chunk_id: str
) -> str:
    created = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        json={"query_text": "when is the office open?"},
        headers=_auth(token),
    )
    retrieval_id = created.json()["data"]["id"]
    async with AsyncSessionLocal() as session:
        retrieval = await session.get(Retrieval, uuid.UUID(retrieval_id))
        retrieval.status = RetrievalStatus.COMPLETED
        retrieval.result_count = 1
        retrieval.avg_similarity = 0.9
        session.add(
            RetrievalResult(
                retrieval_id=uuid.UUID(retrieval_id),
                chunk_id=uuid.UUID(chunk_id),
                rank=1,
                score=0.9,
            )
        )
        await session.commit()
    return retrieval_id


@pytest.mark.asyncio
async def test_create_prompt_template_starts_at_version_one(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    response = await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates",
        json={"name": "support-answer", "system_prompt": "You are a helpful assistant."},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["version"] == 1
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_recreating_same_name_creates_new_version_not_overwrite(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    first = await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates",
        json={"name": "support-answer", "system_prompt": "v1 prompt"},
        headers=_auth(token),
    )
    second = await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates",
        json={"name": "support-answer", "system_prompt": "v2 prompt"},
        headers=_auth(token),
    )
    assert second.json()["data"]["version"] == 2

    versions = await client.get(
        f"/api/v1/repositories/{repository_id}/prompt-templates/support-answer/versions",
        headers=_auth(token),
    )
    bodies = versions.json()["data"]
    assert len(bodies) == 2
    assert {b["version"] for b in bodies} == {1, 2}
    # The first version's exact text is still intact — not overwritten.
    assert {b["system_prompt"] for b in bodies} == {"v1 prompt", "v2 prompt"}
    assert first.json()["data"]["id"] != second.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_prompt_template_requires_admin(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    viewer_token = await _register_and_login(client, "viewer@example.com")
    repository_id = await _create_repository_chain(client, owner_token)

    response = await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates",
        json={"name": "x", "system_prompt": "y"},
        headers=_auth(viewer_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_archive_prompt_template_sets_inactive(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    created = await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates",
        json={"name": "support-answer", "system_prompt": "v1"},
        headers=_auth(token),
    )
    template_id = created.json()["data"]["id"]

    archived = await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates/{template_id}/archive",
        headers=_auth(token),
    )
    assert archived.status_code == 200
    assert archived.json()["data"]["is_active"] is False


@pytest.mark.asyncio
async def test_build_prompt_requires_completed_retrieval(client):
    token = await _register_and_login(client, "owner@example.com")
    _, document_id, vector_index_id, _ = await _seed_index_chain(client, token)

    created = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        json={"query_text": "test"},
        headers=_auth(token),
    )
    retrieval_id = created.json()["data"]["id"]

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={"system_prompt": "You are a helpful assistant."},
        headers=_auth(token),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RETRIEVAL_NOT_COMPLETED"


@pytest.mark.asyncio
async def test_build_prompt_requires_system_prompt_or_template(client):
    token = await _register_and_login(client, "owner@example.com")
    _, document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={},
        headers=_auth(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_build_prompt_with_inline_system_prompt_renders_context_and_citations(client):
    token = await _register_and_login(client, "owner@example.com")
    _, document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={"system_prompt": "You are a helpful assistant."},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["status"] == "completed"
    assert "office is open" in body["rendered_context"]
    assert "You are a helpful assistant." in body["rendered_prompt"]
    assert "when is the office open?" in body["rendered_prompt"]
    assert body["citations"][0]["chunk_id"] == chunk_id
    assert body["citations"][0]["source_label"] == "Source 1"
    assert body["total_tokens"] > 0
    assert body["context_tokens"] > 0


@pytest.mark.asyncio
async def test_build_prompt_from_template_snapshots_text(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id, document_id, vector_index_id, chunk_id = await _seed_index_chain(
        client, token
    )
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )

    template = await client.post(
        f"/api/v1/repositories/{repository_id}/prompt-templates",
        json={
            "name": "support-answer",
            "system_prompt": "You are an enterprise assistant.",
            "formatting_instructions": "Be concise.",
        },
        headers=_auth(token),
    )
    template_id = template.json()["data"]["id"]

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={"prompt_template_id": template_id},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["prompt_template_id"] == template_id
    assert "You are an enterprise assistant." in body["rendered_prompt"]
    assert "Be concise." in body["rendered_prompt"]


@pytest.mark.asyncio
async def test_build_prompt_fails_when_budget_leaves_no_room_for_context(client):
    token = await _register_and_login(client, "owner@example.com")
    _, document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={
            "system_prompt": "You are a helpful assistant.",
            "model_context_window": 256,
            "response_reserve_tokens": 256,
        },
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["status"] == "failed"
    assert body["status_message"] is not None
    assert body["rendered_prompt"] is None


@pytest.mark.asyncio
async def test_prompt_template_from_another_repository_is_rejected(client):
    token = await _register_and_login(client, "owner@example.com")
    _, document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )

    other_repository_id = await _create_repository_chain(client, token, suffix="2")
    other_template = await client.post(
        f"/api/v1/repositories/{other_repository_id}/prompt-templates",
        json={"name": "unrelated", "system_prompt": "unrelated prompt"},
        headers=_auth(token),
    )
    other_template_id = other_template.json()["data"]["id"]

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={"prompt_template_id": other_template_id},
        headers=_auth(token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_and_get_prompt(client):
    token = await _register_and_login(client, "owner@example.com")
    _, document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )

    created = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={"system_prompt": "You are a helpful assistant."},
        headers=_auth(token),
    )
    prompt_id = created.json()["data"]["id"]

    listing = await client.get(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        headers=_auth(token),
    )
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    detail = await client.get(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts/{prompt_id}",
        headers=_auth(token),
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == prompt_id
