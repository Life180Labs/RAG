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


async def _create_project_chain(client, token: str) -> str:
    """Registers the org/workspace/project scaffolding a repository needs
    and returns the project_id."""
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
    return proj_response.json()["data"]["id"]


async def _create_repository(
    client, token: str, project_id: str, slug: str = "docs", name: str = "Docs"
) -> str:
    response = await client.post(
        f"/api/v1/projects/{project_id}/repositories",
        json={"name": name, "slug": slug},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_repository_makes_creator_owner_with_zeroed_statistics(client):
    token = await _register_and_login(client, "owner@example.com")
    project_id = await _create_project_chain(client, token)

    response = await client.post(
        f"/api/v1/projects/{project_id}/repositories",
        json={"name": "Docs", "slug": "docs", "description": "Handbook"},
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["slug"] == "docs"
    assert body["data"]["status"] == "active"
    assert body["data"]["document_count"] == 0
    assert body["data"]["chunk_count"] == 0
    assert body["data"]["default_embedding_model"] is None


@pytest.mark.asyncio
async def test_duplicate_repository_slug_within_project_rejected(client):
    token = await _register_and_login(client, "owner@example.com")
    project_id = await _create_project_chain(client, token)
    await _create_repository(client, token, project_id, slug="docs")

    response = await client.post(
        f"/api/v1/projects/{project_id}/repositories",
        json={"name": "Docs Two", "slug": "docs"},
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 409
    assert body["error"]["code"] == "SLUG_TAKEN"


@pytest.mark.asyncio
async def test_non_member_cannot_read_repository(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    project_id = await _create_project_chain(client, owner_token)
    repository_id = await _create_repository(client, owner_token, project_id)

    response = await client.get(
        f"/api/v1/repositories/{repository_id}", headers=_auth(stranger_token)
    )
    body = response.json()

    assert response.status_code == 403
    assert body["error"]["code"] == "NOT_A_MEMBER"


@pytest.mark.asyncio
async def test_update_repository_name_and_description(client):
    token = await _register_and_login(client, "owner@example.com")
    project_id = await _create_project_chain(client, token)
    repository_id = await _create_repository(client, token, project_id)

    response = await client.patch(
        f"/api/v1/repositories/{repository_id}",
        json={"name": "Renamed Docs", "description": "Updated description"},
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["name"] == "Renamed Docs"
    assert body["data"]["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_repository_settings(client):
    token = await _register_and_login(client, "owner@example.com")
    project_id = await _create_project_chain(client, token)
    repository_id = await _create_repository(client, token, project_id)

    response = await client.patch(
        f"/api/v1/repositories/{repository_id}/settings",
        json={
            "default_chunk_strategy": "recursive",
            "default_embedding_model": "text-embedding-3-small",
            "default_retriever": "hybrid",
            "default_reranker": "cross-encoder",
            "default_prompt_version": "v1",
        },
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["default_chunk_strategy"] == "recursive"
    assert body["data"]["default_embedding_model"] == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_archive_and_restore_repository(client):
    token = await _register_and_login(client, "owner@example.com")
    project_id = await _create_project_chain(client, token)
    repository_id = await _create_repository(client, token, project_id)

    archive_response = await client.post(
        f"/api/v1/repositories/{repository_id}/archive", headers=_auth(token)
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["data"]["status"] == "archived"

    restore_response = await client.post(
        f"/api/v1/repositories/{repository_id}/restore", headers=_auth(token)
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["data"]["status"] == "active"


@pytest.mark.asyncio
async def test_delete_repository_requires_owner_role(client):
    token = await _register_and_login(client, "owner@example.com")
    project_id = await _create_project_chain(client, token)
    repository_id = await _create_repository(client, token, project_id)

    response = await client.delete(f"/api/v1/repositories/{repository_id}", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_search_repositories_by_name(client):
    token = await _register_and_login(client, "owner@example.com")
    project_id = await _create_project_chain(client, token)
    await _create_repository(client, token, project_id, slug="handbook", name="Employee Handbook")
    await _create_repository(
        client, token, project_id, slug="engineering-wiki", name="Engineering Wiki"
    )

    response = await client.get(
        f"/api/v1/projects/{project_id}/repositories/search",
        params={"q": "Handbook"},
        headers=_auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert len(body["data"]) == 1
    assert body["data"][0]["slug"] == "handbook"


@pytest.mark.asyncio
async def test_repository_activity_records_create_and_update(client):
    token = await _register_and_login(client, "owner@example.com")
    project_id = await _create_project_chain(client, token)
    repository_id = await _create_repository(client, token, project_id)

    await client.patch(
        f"/api/v1/repositories/{repository_id}",
        json={"name": "Renamed"},
        headers=_auth(token),
    )

    response = await client.get(
        f"/api/v1/repositories/{repository_id}/activity", headers=_auth(token)
    )
    body = response.json()
    actions = [entry["action"] for entry in body["data"]]

    assert response.status_code == 200
    assert "repository.create" in actions
    assert "repository.update" in actions


@pytest.mark.asyncio
async def test_creating_repository_requires_project_admin(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    project_id = await _create_project_chain(client, owner_token)

    response = await client.post(
        f"/api/v1/projects/{project_id}/repositories",
        json={"name": "Docs", "slug": "docs"},
        headers=_auth(stranger_token),
    )
    body = response.json()

    assert response.status_code == 403
    assert body["error"]["code"] == "NOT_A_MEMBER"
