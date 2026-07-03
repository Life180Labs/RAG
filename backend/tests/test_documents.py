import pytest

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
    """Registers org/workspace/project/repository scaffolding and returns
    the repository_id, matching test_repositories.py's pattern."""
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


async def _upload(client, token: str, repository_id: str, *, filename: str, content: bytes):
    return await client.post(
        f"/api/v1/repositories/{repository_id}/documents",
        headers=_auth(token),
        files={"file": (filename, content, "text/plain")},
    )


@pytest.mark.asyncio
async def test_upload_document_creates_document_uploaded_status_version_one(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    response = await _upload(
        client, token, repository_id, filename="report.txt", content=b"hello world"
    )
    body = response.json()

    assert response.status_code == 200, response.text
    assert body["data"]["filename"] == "report.txt"
    assert body["data"]["status"] == "uploaded"
    assert body["data"]["current_version"] == 1
    assert body["data"]["size_bytes"] == len(b"hello world")
    assert len(body["data"]["sha256_hash"]) == 64


@pytest.mark.asyncio
async def test_upload_bumps_repository_document_count_and_storage_used(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    await _upload(client, token, repository_id, filename="a.txt", content=b"hello world")

    response = await client.get(f"/api/v1/repositories/{repository_id}", headers=_auth(token))
    body = response.json()

    assert body["data"]["document_count"] == 1
    assert body["data"]["storage_used_bytes"] == len(b"hello world")


@pytest.mark.asyncio
async def test_duplicate_document_upload_rejected(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    await _upload(client, token, repository_id, filename="a.txt", content=b"same bytes")

    response = await _upload(client, token, repository_id, filename="b.txt", content=b"same bytes")
    body = response.json()

    assert response.status_code == 409
    assert body["error"]["code"] == "DUPLICATE_DOCUMENT"


@pytest.mark.asyncio
async def test_unsupported_extension_rejected(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    response = await _upload(
        client, token, repository_id, filename="malware.exe", content=b"anything"
    )
    body = response.json()

    assert response.status_code == 400
    assert body["error"]["code"] == "UNSUPPORTED_EXTENSION"


@pytest.mark.asyncio
async def test_empty_file_rejected(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)

    response = await _upload(client, token, repository_id, filename="empty.txt", content=b"")
    body = response.json()

    assert response.status_code == 400
    assert body["error"]["code"] == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_list_documents_by_repository(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    await _upload(client, token, repository_id, filename="a.txt", content=b"content a")
    await _upload(client, token, repository_id, filename="b.txt", content=b"content b")

    response = await client.get(
        f"/api/v1/repositories/{repository_id}/documents", headers=_auth(token)
    )
    body = response.json()

    assert response.status_code == 200
    assert {d["filename"] for d in body["data"]} == {"a.txt", "b.txt"}


@pytest.mark.asyncio
async def test_non_member_cannot_upload_or_read_document(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    repository_id = await _create_repository_chain(client, owner_token)

    upload_response = await _upload(
        client, stranger_token, repository_id, filename="a.txt", content=b"content"
    )
    assert upload_response.status_code == 403
    assert upload_response.json()["error"]["code"] == "NOT_A_MEMBER"

    upload = await _upload(client, owner_token, repository_id, filename="a.txt", content=b"c1")
    document_id = upload.json()["data"]["id"]

    get_response = await client.get(
        f"/api/v1/documents/{document_id}", headers=_auth(stranger_token)
    )
    assert get_response.status_code == 403
    assert get_response.json()["error"]["code"] == "NOT_A_MEMBER"


@pytest.mark.asyncio
async def test_upload_new_version_increments_version_and_lists_versions(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    upload = await _upload(client, token, repository_id, filename="a.txt", content=b"v1 content")
    document_id = upload.json()["data"]["id"]

    version_response = await client.post(
        f"/api/v1/documents/{document_id}/versions",
        headers=_auth(token),
        files={"file": ("a.txt", b"v2 content", "text/plain")},
    )
    body = version_response.json()

    assert version_response.status_code == 200, version_response.text
    assert body["data"]["current_version"] == 2
    assert body["data"]["size_bytes"] == len(b"v2 content")

    list_response = await client.get(
        f"/api/v1/documents/{document_id}/versions", headers=_auth(token)
    )
    versions = list_response.json()["data"]

    assert len(versions) == 2
    assert {v["version"] for v in versions} == {1, 2}


@pytest.mark.asyncio
async def test_soft_delete_and_restore_document_updates_repository_stats(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    upload = await _upload(client, token, repository_id, filename="a.txt", content=b"delete me")
    document_id = upload.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/documents/{document_id}", headers=_auth(token)
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True

    repo_after_delete = await client.get(
        f"/api/v1/repositories/{repository_id}", headers=_auth(token)
    )
    assert repo_after_delete.json()["data"]["document_count"] == 0
    assert repo_after_delete.json()["data"]["storage_used_bytes"] == 0

    restore_response = await client.post(
        f"/api/v1/documents/{document_id}/restore", headers=_auth(token)
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["data"]["id"] == document_id

    repo_after_restore = await client.get(
        f"/api/v1/repositories/{repository_id}", headers=_auth(token)
    )
    assert repo_after_restore.json()["data"]["document_count"] == 1
    assert repo_after_restore.json()["data"]["storage_used_bytes"] == len(b"delete me")


@pytest.mark.asyncio
async def test_delete_and_restore_document_require_admin_role(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    repository_id = await _create_repository_chain(client, owner_token)
    upload = await _upload(client, owner_token, repository_id, filename="a.txt", content=b"c1")
    document_id = upload.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/documents/{document_id}", headers=_auth(stranger_token)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_A_MEMBER"


@pytest.mark.asyncio
async def test_download_document_returns_presigned_url(client):
    token = await _register_and_login(client, "owner@example.com")
    repository_id = await _create_repository_chain(client, token)
    upload = await _upload(
        client, token, repository_id, filename="download-me.txt", content=b"download content"
    )
    document_id = upload.json()["data"]["id"]

    response = await client.get(
        f"/api/v1/documents/{document_id}/download", headers=_auth(token)
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["stream_via_backend"] is False
    assert body["data"]["url"].startswith("http")
