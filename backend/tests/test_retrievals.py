import uuid

import pytest

from app.db.session import AsyncSessionLocal
from app.models.chunk import Chunk, ChunkSetStatus, ChunkStatus, DocumentChunkSet
from app.models.embedding import EmbeddingVersion, EmbeddingVersionStatus
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


async def _seed_chunk(document_id: str) -> str:
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
            text="a",
            char_start=0,
            char_end=1,
            token_count=1,
            page=None,
            heading=None,
            status=ChunkStatus.READY,
        )
        session.add(chunk)
        await session.commit()
        return str(chunk_set.id)


async def _seed_embedding_version(chunk_set_id: str, document_id: str) -> str:
    async with AsyncSessionLocal() as session:
        version = EmbeddingVersion(
            chunk_set_id=uuid.UUID(chunk_set_id),
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
        await session.commit()
        return str(version.id)


async def _seed_vector_index(embedding_version_id: str, document_id: str) -> str:
    async with AsyncSessionLocal() as session:
        index = VectorIndex(
            embedding_version_id=uuid.UUID(embedding_version_id),
            document_id=uuid.UUID(document_id),
            provider="pgvector",
            index_type="hnsw",
            namespace=embedding_version_id,
            dimensions=384,
            version=1,
            status=VectorIndexStatus.READY,
            vector_count=1,
        )
        session.add(index)
        await session.commit()
        return str(index.id)


async def _seed_index_chain(client, token: str) -> tuple[str, str]:
    document_id, vector_index_id, _ = await _seed_index_chain_with_repository(client, token)
    return document_id, vector_index_id


async def _seed_index_chain_with_repository(client, token: str) -> tuple[str, str, str]:
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_id = await _seed_chunk(document_id)
    embedding_version_id = await _seed_embedding_version(chunk_set_id, document_id)
    vector_index_id = await _seed_vector_index(embedding_version_id, document_id)
    return document_id, vector_index_id, repository_id


@pytest.mark.asyncio
async def test_create_retrieval_creates_pending_row_and_enqueues(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id = await _seed_index_chain(client, token)

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        json={"query_text": "what is RAG?", "top_k": 5},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["status"] == "pending"
    assert body["query_text"] == "what is RAG?"
    assert body["top_k"] == 5
    assert body["similarity_metric"] == "cosine"


@pytest.mark.asyncio
async def test_create_retrieval_validates_top_k_bounds(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id = await _seed_index_chain(client, token)

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        json={"query_text": "test", "top_k": 0},
        headers=_auth(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_and_get_retrieval(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id = await _seed_index_chain(client, token)

    created = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        json={"query_text": "test query"},
        headers=_auth(token),
    )
    retrieval_id = created.json()["data"]["id"]

    listing = await client.get(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        headers=_auth(token),
    )
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    detail = await client.get(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}",
        headers=_auth(token),
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == retrieval_id


@pytest.mark.asyncio
async def test_get_retrieval_results_empty_before_worker_runs(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id = await _seed_index_chain(client, token)

    created = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        json={"query_text": "test query"},
        headers=_auth(token),
    )
    retrieval_id = created.json()["data"]["id"]

    results = await client.get(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}"
        f"/retrievals/{retrieval_id}/results",
        headers=_auth(token),
    )
    assert results.status_code == 200
    assert results.json()["data"] == []


@pytest.mark.asyncio
async def test_retrieval_requires_at_least_viewer_role(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    document_id, vector_index_id = await _seed_index_chain(client, owner_token)

    response = await client.post(
        f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals",
        json={"query_text": "test"},
        headers=_auth(stranger_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_retrieval_from_another_document_is_not_accessible(client):
    token = await _register_and_login(client, "owner@example.com")
    document_id, vector_index_id, repository_id = await _seed_index_chain_with_repository(
        client, token
    )

    other_document_id = await _upload_document(
        client, token, repository_id, filename="other.txt", content=b"a different file"
    )

    response = await client.get(
        f"/api/v1/documents/{other_document_id}/vector-indexes/{vector_index_id}/retrievals",
        headers=_auth(token),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VECTOR_INDEX_NOT_FOUND"
