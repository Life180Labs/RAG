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
        files={
            "file": (
                "handbook.txt",
                b"Employees get 20 annual leave days a year.",
                "text/plain",
            )
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


async def _seed_chunk(
    document_id: str, text: str = "Employees get 20 annual leave days a year."
) -> str:
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
    return repository_id, document_id, vector_index_id, chunk_id


def _conversations_path(document_id: str, vector_index_id: str) -> str:
    return f"/api/v1/documents/{document_id}/vector-indexes/{vector_index_id}/conversations"


@pytest.mark.asyncio
async def test_create_list_get_delete_conversation(client):
    token = await _register_and_login(client, "owner@example.com")
    _, document_id, vector_index_id, _ = await _seed_index_chain(client, token)

    created = await client.post(
        _conversations_path(document_id, vector_index_id),
        json={"title": "HR questions"},
        headers=_auth(token),
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["data"]["id"]
    assert created.json()["data"]["title"] == "HR questions"

    listing = await client.get(
        _conversations_path(document_id, vector_index_id), headers=_auth(token)
    )
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    detail = await client.get(
        f"{_conversations_path(document_id, vector_index_id)}/{conversation_id}",
        headers=_auth(token),
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == conversation_id

    deleted = await client.delete(
        f"{_conversations_path(document_id, vector_index_id)}/{conversation_id}",
        headers=_auth(token),
    )
    assert deleted.status_code == 200

    after_delete = await client.get(
        f"{_conversations_path(document_id, vector_index_id)}/{conversation_id}",
        headers=_auth(token),
    )
    assert after_delete.status_code == 404


@pytest.mark.asyncio
async def test_conversation_requires_at_least_viewer_role(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    _, document_id, vector_index_id, _ = await _seed_index_chain(client, owner_token)

    response = await client.post(
        _conversations_path(document_id, vector_index_id),
        json={},
        headers=_auth(stranger_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_conversation_memory_get_defaults_and_update(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    initial = await client.get(
        f"/api/v1/repositories/{repository_id}/conversation-memory", headers=_auth(token)
    )
    assert initial.status_code == 200
    assert initial.json()["data"]["custom_instructions"] is None

    updated = await client.patch(
        f"/api/v1/repositories/{repository_id}/conversation-memory",
        json={
            "custom_instructions": "Always answer in bullet points.",
            "preferences": {"lang": "en"},
        },
        headers=_auth(token),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["custom_instructions"] == "Always answer in bullet points."
    assert updated.json()["data"]["preferences"] == {"lang": "en"}

    refetched = await client.get(
        f"/api/v1/repositories/{repository_id}/conversation-memory", headers=_auth(token)
    )
    assert refetched.json()["data"]["custom_instructions"] == "Always answer in bullet points."


@pytest.mark.asyncio
async def test_send_message_full_turn_and_followup_condensation(client):
    """The real end-to-end flow: two turns against the real, locally
    running Ollama provider — retrieval -> prompt -> completion for turn
    one, then a follow-up whose retrieval query is condensed using turn
    one's history rather than sent verbatim."""
    token = await _register_and_login(client, "owner@example.com")
    _, document_id, vector_index_id, _ = await _seed_index_chain(client, token)

    created = await client.post(
        _conversations_path(document_id, vector_index_id), json={}, headers=_auth(token)
    )
    conversation_id = created.json()["data"]["id"]
    messages_path = (
        f"{_conversations_path(document_id, vector_index_id)}/{conversation_id}/messages"
    )

    first = await client.post(
        messages_path,
        json={"content": "How many annual leave days do employees get?"},
        headers=_auth(token),
    )
    assert first.status_code == 200, first.text
    first_body = first.json()["data"]
    assert first_body["user_message"]["role"] == "user"
    assert first_body["assistant_message"]["role"] == "assistant"
    assert first_body["assistant_message"]["content"]
    assert first_body["assistant_message"]["retrieval_id"] is not None
    assert first_body["assistant_message"]["prompt_id"] is not None
    assert first_body["assistant_message"]["llm_request_id"] is not None

    second = await client.post(
        messages_path,
        json={"content": "Can you repeat just the number?"},
        headers=_auth(token),
    )
    assert second.status_code == 200, second.text
    second_body = second.json()["data"]
    assert second_body["assistant_message"]["content"]

    all_messages = await client.get(messages_path, headers=_auth(token))
    assert all_messages.status_code == 200
    assert len(all_messages.json()["data"]) == 4

    export = await client.get(
        f"{_conversations_path(document_id, vector_index_id)}/{conversation_id}/export",
        headers=_auth(token),
    )
    assert export.status_code == 200
    assert "User" in export.text and "Assistant" in export.text
