import uuid

import pytest

from app.db.session import AsyncSessionLocal
from app.models.chunk import Chunk, ChunkSetStatus, ChunkStatus, DocumentChunkSet
from app.models.embedding import EmbeddingVersion, EmbeddingVersionStatus
from app.models.retrieval import Retrieval, RetrievalResult, RetrievalStatus
from app.models.vector_index import VectorIndex, VectorIndexStatus

VALID_PASSWORD = "Str0ng!Passw0rd"


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


async def _create_repository_chain(client, token: str) -> str:
    org_response = await client.post(
        "/api/v1/organizations", json={"name": "Acme", "slug": "acme"}, headers=_auth(token)
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


async def _upload_document(client, token: str, repository_id: str) -> str:
    response = await client.post(
        f"/api/v1/repositories/{repository_id}/documents",
        headers=_auth(token),
        files={"file": ("report.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


async def _seed_chunk(document_id: str, text: str = "Employees get 20 leave days a year.") -> str:
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


async def _seed_index_chain(client, token: str) -> tuple[str, str, str]:
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_id = await _seed_chunk(document_id)
    async with AsyncSessionLocal() as session:
        chunk = await session.get(Chunk, uuid.UUID(chunk_id))
        version = EmbeddingVersion(
            chunk_set_id=chunk.chunk_set_id,
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
    return document_id, vector_index_id, chunk_id


async def _create_and_complete_retrieval(
    client, token: str, document_id: str, vector_index_id: str, chunk_id: str
) -> str:
    created = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        json={"query_text": "how many leave days?"},
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


async def _build_prompt(
    client, token: str, document_id: str, vector_index_id: str, retrieval_id: str
) -> str:
    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={"system_prompt": "You are a helpful HR assistant."},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


def _completions_path(
    document_id: str, vector_index_id: str, retrieval_id: str, prompt_id: str
) -> str:
    return (
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts/{prompt_id}/completions"
    )


@pytest.mark.asyncio
async def test_list_models_returns_all_providers(client):
    token = await _register_and_login(client, "owner@example.com")
    response = await client.get("/api/v1/llm/models", headers=_auth(token))
    assert response.status_code == 200
    providers = {m["provider"] for m in response.json()["data"]}
    assert providers == {"openai", "anthropic", "gemini", "groq", "openrouter", "ollama"}


@pytest.mark.asyncio
async def test_provider_health_reports_configured_and_healthy(client):
    token = await _register_and_login(client, "owner@example.com")

    ollama = await client.get("/api/v1/llm/models/ollama/health", headers=_auth(token))
    assert ollama.status_code == 200
    assert ollama.json()["data"]["configured"] is True

    openai = await client.get("/api/v1/llm/models/openai/health", headers=_auth(token))
    assert openai.status_code == 200
    assert openai.json()["data"] == {"provider": "openai", "configured": False, "healthy": False}


@pytest.mark.asyncio
async def test_create_completion_requires_completed_prompt_is_completed(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )
    prompt_id = await _build_prompt(client, token, document_id, vector_index_id, retrieval_id)

    response = await client.post(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        json={"provider": "ollama", "model": "deepseek-r1:1.5b"},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["status"] == "completed"
    assert body["provider"] == "ollama"
    assert body["output_text"]
    assert body["input_tokens"] > 0
    assert body["output_tokens"] > 0
    assert body["cost_usd"] == pytest.approx(0.0)
    assert body["latency_ms"] is not None
    assert body["attempted_providers"] == [
        {"provider": "ollama", "model": "deepseek-r1:1.5b", "error": None}
    ]


@pytest.mark.asyncio
async def test_create_completion_falls_back_to_ollama_when_default_providers_unconfigured(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )
    prompt_id = await _build_prompt(client, token, document_id, vector_index_id, retrieval_id)

    response = await client.post(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        json={},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["status"] == "completed"
    assert body["provider"] == "ollama"
    providers_tried = [a["provider"] for a in body["attempted_providers"]]
    assert providers_tried == ["openai", "anthropic", "groq", "openrouter", "gemini", "ollama"]
    assert all(a["error"] is not None for a in body["attempted_providers"][:-1])
    assert body["attempted_providers"][-1]["error"] is None


@pytest.mark.asyncio
async def test_create_completion_before_prompt_built_is_conflict(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )
    created = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/prompts",
        json={
            "system_prompt": "x",
            "model_context_window": 256,
            "response_reserve_tokens": 256,
        },
        headers=_auth(token),
    )
    prompt_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "failed"

    response = await client.post(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        json={"provider": "ollama", "model": "deepseek-r1:1.5b"},
        headers=_auth(token),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROMPT_NOT_COMPLETED"


@pytest.mark.asyncio
async def test_list_and_get_completion(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )
    prompt_id = await _build_prompt(client, token, document_id, vector_index_id, retrieval_id)
    created = await client.post(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        json={"provider": "ollama", "model": "deepseek-r1:1.5b"},
        headers=_auth(token),
    )
    request_id = created.json()["data"]["id"]

    listing = await client.get(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        headers=_auth(token),
    )
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    detail = await client.get(
        f"{_completions_path(document_id, vector_index_id, retrieval_id, prompt_id)}/{request_id}",
        headers=_auth(token),
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == request_id


@pytest.mark.asyncio
async def test_create_completion_requires_at_least_viewer_role(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    document_id, vector_index_id, chunk_id = await _seed_index_chain(client, owner_token)
    retrieval_id = await _create_and_complete_retrieval(
        client, owner_token, document_id, vector_index_id, chunk_id
    )
    prompt_id = await _build_prompt(client, owner_token, document_id, vector_index_id, retrieval_id)

    response = await client.post(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        json={"provider": "ollama", "model": "deepseek-r1:1.5b"},
        headers=_auth(stranger_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_completion_requires_provider_and_model_together(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id, chunk_id = await _seed_index_chain(client, token)
    retrieval_id = await _create_and_complete_retrieval(
        client, token, document_id, vector_index_id, chunk_id
    )
    prompt_id = await _build_prompt(client, token, document_id, vector_index_id, retrieval_id)

    response = await client.post(
        _completions_path(document_id, vector_index_id, retrieval_id, prompt_id),
        json={"provider": "ollama"},
        headers=_auth(token),
    )
    assert response.status_code == 422
