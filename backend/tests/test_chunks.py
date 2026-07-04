import uuid

import pytest

from app.db.session import AsyncSessionLocal
from app.models.chunk import Chunk, ChunkSetStatus, ChunkStatus, DocumentChunkSet

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
    """Inserts a chunk_set + chunks directly via the ORM, bypassing the
    real Celery worker — these tests exercise the read/compare/delete API
    surface, not the chunk_document task itself (covered by
    worker/tests/test_chunk_document.py)."""
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


@pytest.mark.asyncio
async def test_generate_chunks_enqueues_and_requires_admin(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    repository_id = await _create_repository_chain(client, owner_token)
    document_id = await _upload_document(client, owner_token, repository_id)

    forbidden = await client.post(
        f"/api/v1/documents/{document_id}/chunk-sets",
        json={"strategy": "recursive"},
        headers=_auth(stranger_token),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "NOT_A_MEMBER"

    response = await client.post(
        f"/api/v1/documents/{document_id}/chunk-sets",
        json={"strategy": "recursive"},
        headers=_auth(owner_token),
    )
    body = response.json()
    assert response.status_code == 200, response.text
    assert body["data"] == {"enqueued": True, "strategy": "recursive"}


@pytest.mark.asyncio
async def test_list_chunk_sets_returns_seeded_sets(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    await _seed_chunk_set(document_id, "recursive", ["chunk one", "chunk two"])

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets", headers=_auth(token)
    )
    body = response.json()

    assert response.status_code == 200
    assert len(body["data"]) == 1
    assert body["data"][0]["strategy"] == "recursive"
    assert body["data"][0]["chunk_count"] == 2


@pytest.mark.asyncio
async def test_list_chunks_returns_ordered_chunk_rows(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id, "sentence", ["first", "second", "third"])

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}/chunks",
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert [c["text"] for c in body["data"]] == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_compare_chunk_sets_returns_both_sides(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    await _seed_chunk_set(document_id, "recursive", ["a", "b"])
    await _seed_chunk_set(document_id, "sentence", ["x", "y", "z"])

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/compare",
        params={"strategy_a": "recursive", "strategy_b": "sentence"},
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["strategy_a"]["strategy"] == "recursive"
    assert len(body["data"]["chunks_a"]) == 2
    assert body["data"]["strategy_b"]["strategy"] == "sentence"
    assert len(body["data"]["chunks_b"]) == 3


@pytest.mark.asyncio
async def test_compare_missing_strategy_returns_404(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_id = await _upload_document(client, token, repository_id)
    await _seed_chunk_set(document_id, "recursive", ["a"])

    response = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets/compare",
        params={"strategy_a": "recursive", "strategy_b": "semantic"},
        headers=_auth(token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CHUNK_SET_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_chunk_set_requires_admin_and_removes_it(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    repository_id = await _create_repository_chain(client, owner_token)
    document_id = await _upload_document(client, owner_token, repository_id)
    chunk_set_id = await _seed_chunk_set(document_id, "recursive", ["a", "b"])

    forbidden = await client.delete(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}",
        headers=_auth(stranger_token),
    )
    assert forbidden.status_code == 403

    response = await client.delete(
        f"/api/v1/documents/{document_id}/chunk-sets/{chunk_set_id}", headers=_auth(owner_token)
    )
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True

    listing = await client.get(
        f"/api/v1/documents/{document_id}/chunk-sets", headers=_auth(owner_token)
    )
    assert listing.json()["data"] == []


@pytest.mark.asyncio
async def test_chunk_set_from_another_document_is_not_accessible(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    document_a = await _upload_document(client, token, repository_id)

    response_b = await client.post(
        f"/api/v1/repositories/{repository_id}/documents",
        headers=_auth(token),
        files={"file": ("other.txt", b"different content", "text/plain")},
    )
    document_b = response_b.json()["data"]["id"]

    chunk_set_id = await _seed_chunk_set(document_a, "recursive", ["a"])

    response = await client.get(
        f"/api/v1/documents/{document_b}/chunk-sets/{chunk_set_id}/chunks", headers=_auth(token)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CHUNK_SET_NOT_FOUND"
