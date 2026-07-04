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


async def _upload_document(client, token: str, repository_id: str) -> str:
    response = await client.post(
        f"/api/v1/repositories/{repository_id}/documents",
        headers=_auth(token),
        files={"file": ("report.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


async def _seed_chunk_set(document_id: str, strategy: str = "recursive") -> str:
    async with AsyncSessionLocal() as session:
        chunk_set = DocumentChunkSet(
            document_id=uuid.UUID(document_id),
            version=1,
            strategy=strategy,
            config={"max_tokens": 400},
            status=ChunkSetStatus.READY,
            chunk_count=1,
        )
        session.add(chunk_set)
        await session.flush()
        session.add(
            Chunk(
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
        )
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


async def _seed_vector_index(embedding_version_id: str, document_id: str, provider: str) -> str:
    async with AsyncSessionLocal() as session:
        index = VectorIndex(
            embedding_version_id=uuid.UUID(embedding_version_id),
            document_id=uuid.UUID(document_id),
            provider=provider,
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


@pytest.mark.asyncio
async def test_create_vector_index_enqueues_and_requires_admin(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    repository_id = await _create_repository_chain(client, owner_token)
    document_id = await _upload_document(client, owner_token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id)
    embedding_version_id = await _seed_embedding_version(chunk_set_id, document_id)

    forbidden = await client.post(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}"
        f"/embeddings/{embedding_version_id}/index",
        json={"provider": "pgvector"},
        headers=_auth(stranger_token),
    )
    assert forbidden.status_code == 403

    response = await client.post(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}"
        f"/embeddings/{embedding_version_id}/index",
        json={"provider": "pgvector"},
        headers=_auth(owner_token),
    )
    body = response.json()
    assert response.status_code == 200, response.text
    assert body["data"] == {"enqueued": True, "provider": "pgvector", "index_type": "hnsw"}


@pytest.mark.asyncio
async def test_list_and_get_vector_indexes(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id)
    embedding_version_id = await _seed_embedding_version(chunk_set_id, document_id)
    vector_index_id = await _seed_vector_index(embedding_version_id, document_id, "pgvector")

    listing = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}"
        f"/embeddings/{embedding_version_id}/index",
        headers=_auth(token),
    )
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1
    assert listing.json()["data"][0]["provider"] == "pgvector"

    detail = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}"
        f"/embeddings/{embedding_version_id}/index/{vector_index_id}",
        headers=_auth(token),
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == vector_index_id
    assert detail.json()["data"]["vector_count"] == 1


@pytest.mark.asyncio
async def test_delete_vector_index_requires_admin_and_enqueues(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    repository_id = await _create_repository_chain(client, owner_token)
    document_id = await _upload_document(client, owner_token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id)
    embedding_version_id = await _seed_embedding_version(chunk_set_id, document_id)
    vector_index_id = await _seed_vector_index(embedding_version_id, document_id, "pgvector")

    forbidden = await client.delete(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}"
        f"/embeddings/{embedding_version_id}/index/{vector_index_id}",
        headers=_auth(stranger_token),
    )
    assert forbidden.status_code == 403

    response = await client.delete(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}"
        f"/embeddings/{embedding_version_id}/index/{vector_index_id}",
        headers=_auth(owner_token),
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"enqueued": True}


@pytest.mark.asyncio
async def test_vector_index_from_another_embedding_version_is_not_accessible(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id)
    embedding_version_a = await _seed_embedding_version(chunk_set_id, document_id)
    vector_index_id = await _seed_vector_index(embedding_version_a, document_id, "pgvector")

    chunk_set_b = await _seed_chunk_set(document_id, strategy="sentence")
    embedding_version_b = await _seed_embedding_version(chunk_set_b, document_id)

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_b}"
        f"/embeddings/{embedding_version_b}/index/{vector_index_id}",
        headers=_auth(token),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VECTOR_INDEX_NOT_FOUND"
