import uuid

import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.chunk import Chunk, ChunkSetStatus, ChunkStatus, DocumentChunkSet
from app.models.embedding import (
    Embedding,
    EmbeddingStatus,
    EmbeddingVersion,
    EmbeddingVersionStatus,
)

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


async def _seed_chunk_set(document_id: str, strategy: str, texts: list[str]) -> str:
    async with AsyncSessionLocal() as session:
        chunk_set = DocumentChunkSet(
            document_id=uuid.UUID(document_id),
            version=1,
            strategy=strategy,
            config={"max_tokens": 400},
            status=ChunkSetStatus.READY,
            chunk_count=len(texts),
        )
        session.add(chunk_set)
        await session.flush()

        for index, text in enumerate(texts):
            session.add(
                Chunk(
                    chunk_set_id=chunk_set.id,
                    chunk_index=index,
                    text=text,
                    char_start=0,
                    char_end=len(text),
                    token_count=len(text.split()),
                    page=None,
                    heading=None,
                    status=ChunkStatus.READY,
                )
            )
        await session.commit()
        return str(chunk_set.id)


async def _seed_embedding_version(
    chunk_set_id: str, document_id: str, provider: str, model: str, chunk_count: int
) -> str:
    """Inserts an embedding_version + embeddings directly via the ORM,
    bypassing the real Celery worker — these tests exercise the
    read/compare/delete API surface, not the embed_chunk_set task itself
    (covered by worker/tests/test_embed_chunk_set.py)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chunk)
            .where(Chunk.chunk_set_id == uuid.UUID(chunk_set_id))
            .order_by(Chunk.chunk_index)
        )
        chunks = list(result.scalars().all())

        version = EmbeddingVersion(
            chunk_set_id=uuid.UUID(chunk_set_id),
            document_id=uuid.UUID(document_id),
            provider=provider,
            model=model,
            dimensions=384,
            version=1,
            status=EmbeddingVersionStatus.READY,
            embedding_count=chunk_count,
            total_tokens=chunk_count * 5,
            total_cost_usd=None,
            avg_latency_ms=10,
        )
        session.add(version)
        await session.flush()

        for chunk in chunks[:chunk_count]:
            session.add(
                Embedding(
                    embedding_version_id=version.id,
                    chunk_id=chunk.id,
                    embedding=[0.0] * 1536,
                    token_count=5,
                    cost_usd=None,
                    latency_ms=10,
                    status=EmbeddingStatus.READY,
                )
            )
        await session.commit()
        return str(version.id)


@pytest.mark.asyncio
async def test_generate_embeddings_enqueues_and_requires_admin(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    repository_id = await _create_repository_chain(client, owner_token)
    document_id = await _upload_document(client, owner_token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id, "recursive", ["a", "b"])

    forbidden = await client.post(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings",
        json={"provider": "bge"},
        headers=_auth(stranger_token),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "NOT_A_MEMBER"

    response = await client.post(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings",
        json={"provider": "bge"},
        headers=_auth(owner_token),
    )
    body = response.json()
    assert response.status_code == 200, response.text
    assert body["data"] == {"enqueued": True, "provider": "bge", "model": None}


@pytest.mark.asyncio
async def test_list_embedding_versions_returns_seeded_versions(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id, "recursive", ["a", "b"])
    await _seed_embedding_version(chunk_set_id, document_id, "bge", "BAAI/bge-small-en-v1.5", 2)

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings",
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert len(body["data"]) == 1
    assert body["data"][0]["provider"] == "bge"
    assert body["data"][0]["embedding_count"] == 2


@pytest.mark.asyncio
async def test_list_embeddings_returns_vector_rows(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id, "recursive", ["a", "b", "c"])
    version_id = await _seed_embedding_version(
        chunk_set_id, document_id, "bge", "BAAI/bge-small-en-v1.5", 3
    )

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}"
        f"/embeddings/{version_id}/vectors",
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert len(body["data"]) == 3
    assert all(e["status"] == "ready" for e in body["data"])
    assert all("embedding" not in e for e in body["data"])


@pytest.mark.asyncio
async def test_compare_embedding_versions_returns_both_sides(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id, "recursive", ["a", "b"])
    await _seed_embedding_version(chunk_set_id, document_id, "bge", "BAAI/bge-small-en-v1.5", 2)
    await _seed_embedding_version(chunk_set_id, document_id, "nomic", "nomic-ai/nomic", 2)

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/compare",
        params={"provider_a": "bge", "provider_b": "nomic"},
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["version_a"]["provider"] == "bge"
    assert len(body["data"]["embeddings_a"]) == 2
    assert body["data"]["version_b"]["provider"] == "nomic"
    assert len(body["data"]["embeddings_b"]) == 2


@pytest.mark.asyncio
async def test_compare_missing_provider_returns_404(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id, "recursive", ["a"])
    await _seed_embedding_version(chunk_set_id, document_id, "bge", "BAAI/bge-small-en-v1.5", 1)

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/compare",
        params={"provider_a": "bge", "provider_b": "openai"},
        headers=_auth(token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EMBEDDING_VERSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_embedding_version_requires_admin_and_removes_it(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    repository_id = await _create_repository_chain(client, owner_token)
    document_id = await _upload_document(client, owner_token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id, "recursive", ["a", "b"])
    version_id = await _seed_embedding_version(
        chunk_set_id, document_id, "bge", "BAAI/bge-small-en-v1.5", 2
    )

    forbidden = await client.delete(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{version_id}",
        headers=_auth(stranger_token),
    )
    assert forbidden.status_code == 403

    response = await client.delete(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings/{version_id}",
        headers=_auth(owner_token),
    )
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True

    listing = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/embeddings",
        headers=_auth(owner_token),
    )
    assert listing.json()["data"] == []


@pytest.mark.asyncio
async def test_embedding_version_from_another_chunk_set_is_not_accessible(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_a = await _seed_chunk_set(document_id, "recursive", ["a"])
    chunk_set_b = await _seed_chunk_set(document_id, "sentence", ["b"])
    version_id = await _seed_embedding_version(
        chunk_set_a, document_id, "bge", "BAAI/bge-small-en-v1.5", 1
    )

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_b}"
        f"/embeddings/{version_id}/vectors",
        headers=_auth(token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EMBEDDING_VERSION_NOT_FOUND"
