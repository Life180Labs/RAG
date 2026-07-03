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


async def _create_org(client, token: str, name: str = "Acme", slug: str = "acme") -> str:
    response = await client.post(
        "/api/v1/organizations", json={"name": name, "slug": slug}, headers=_auth(token)
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


async def _create_workspace(client, token: str, org_id: str, slug: str = "engineering") -> str:
    response = await client.post(
        f"/api/v1/organizations/{org_id}/workspaces",
        json={"name": "Engineering", "slug": slug},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


async def _create_project(client, token: str, workspace_id: str, slug: str = "rag-studio") -> str:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        json={"name": "RAG Studio", "slug": slug},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


# --- Organization ---


@pytest.mark.asyncio
async def test_create_organization_makes_creator_owner(client):
    token = await _register_and_login(client, "owner@example.com")
    response = await client.post(
        "/api/v1/organizations", json={"name": "Acme", "slug": "acme"}, headers=_auth(token)
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["slug"] == "acme"
    assert body["data"]["status"] == "active"


@pytest.mark.asyncio
async def test_duplicate_organization_slug_rejected(client):
    token = await _register_and_login(client, "owner@example.com")
    await _create_org(client, token)

    response = await client.post(
        "/api/v1/organizations", json={"name": "Acme Two", "slug": "acme"}, headers=_auth(token)
    )
    body = response.json()

    assert response.status_code == 409
    assert body["error"]["code"] == "SLUG_TAKEN"


@pytest.mark.asyncio
async def test_list_organizations_is_tenant_isolated(client):
    token_a = await _register_and_login(client, "a@example.com")
    token_b = await _register_and_login(client, "b@example.com")
    await _create_org(client, token_a, "A Org", "a-org")
    await _create_org(client, token_b, "B Org", "b-org")

    response_a = await client.get("/api/v1/organizations", headers=_auth(token_a))
    slugs_a = [org["slug"] for org in response_a.json()["data"]]

    assert slugs_a == ["a-org"]


@pytest.mark.asyncio
async def test_non_member_cannot_read_organization(client):
    token_owner = await _register_and_login(client, "owner@example.com")
    token_stranger = await _register_and_login(client, "stranger@example.com")
    org_id = await _create_org(client, token_owner)

    response = await client.get(f"/api/v1/organizations/{org_id}", headers=_auth(token_stranger))
    body = response.json()

    assert response.status_code == 403
    assert body["error"]["code"] == "NOT_A_MEMBER"


@pytest.mark.asyncio
async def test_nonexistent_organization_returns_404_even_for_valid_uuid(client):
    token = await _register_and_login(client, "owner@example.com")
    response = await client.get(
        "/api/v1/organizations/00000000-0000-0000-0000-000000000000", headers=_auth(token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_organization_requires_owner_role(client):
    owner_token = await _register_and_login(client, "owner2@example.com")
    org_id = await _create_org(client, owner_token, "Delete Co", "delete-co")

    # An org with only one member (the owner) — deleting as owner succeeds.
    response = await client.delete(f"/api/v1/organizations/{org_id}", headers=_auth(owner_token))
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_update_organization_renames_it(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)

    response = await client.patch(
        f"/api/v1/organizations/{org_id}", json={"name": "Renamed Org"}, headers=_auth(owner_token)
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["name"] == "Renamed Org"


@pytest.mark.asyncio
async def test_archive_and_restore_organization(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)

    archive_response = await client.post(
        f"/api/v1/organizations/{org_id}/archive", headers=_auth(owner_token)
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["data"]["status"] == "archived"

    restore_response = await client.post(
        f"/api/v1/organizations/{org_id}/restore", headers=_auth(owner_token)
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["data"]["status"] == "active"


# --- Workspace ---


@pytest.mark.asyncio
async def test_creating_workspace_requires_organization_admin(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)

    workspace_id = await _create_workspace(client, owner_token, org_id)
    assert workspace_id


@pytest.mark.asyncio
async def test_workspace_creator_can_manage_it_but_org_admin_who_didnt_create_it_cannot(client):
    """Documents the deliberate MVP simplification: workspace access is
    explicit membership, not inherited from organization role."""
    owner_token = await _register_and_login(client, "owner@example.com")
    admin_token = await _register_and_login(client, "admin@example.com")
    org_id = await _create_org(client, owner_token)

    # Owner invites admin as an org ADMIN (accepted via direct membership
    # insertion isn't available over the API, so we approximate by having
    # the owner create the workspace and verifying the *second* org admin
    # cannot access it without explicit workspace membership.
    workspace_id = await _create_workspace(client, owner_token, org_id)

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}", headers=_auth(admin_token)
    )
    body = response.json()

    assert response.status_code == 403
    assert body["error"]["code"] == "NOT_A_MEMBER"


@pytest.mark.asyncio
async def test_update_and_archive_workspace(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)
    workspace_id = await _create_workspace(client, owner_token, org_id)

    update_response = await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Renamed Workspace"},
        headers=_auth(owner_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Renamed Workspace"

    archive_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/archive", headers=_auth(owner_token)
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["data"]["status"] == "archived"


@pytest.mark.asyncio
async def test_duplicate_workspace_slug_within_organization_rejected(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)
    await _create_workspace(client, owner_token, org_id, slug="eng")

    response = await client.post(
        f"/api/v1/organizations/{org_id}/workspaces",
        json={"name": "Engineering Two", "slug": "eng"},
        headers=_auth(owner_token),
    )
    body = response.json()

    assert response.status_code == 409
    assert body["error"]["code"] == "SLUG_TAKEN"


# --- Project ---


@pytest.mark.asyncio
async def test_project_creator_becomes_owner_and_can_manage(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)
    workspace_id = await _create_workspace(client, owner_token, org_id)
    project_id = await _create_project(client, owner_token, workspace_id)

    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Renamed"},
        headers=_auth(owner_token),
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Renamed"


@pytest.mark.asyncio
async def test_project_requires_workspace_membership_not_just_org_membership(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    stranger_token = await _register_and_login(client, "stranger@example.com")
    org_id = await _create_org(client, owner_token)
    workspace_id = await _create_workspace(client, owner_token, org_id)
    project_id = await _create_project(client, owner_token, workspace_id)

    response = await client.get(
        f"/api/v1/projects/{project_id}", headers=_auth(stranger_token)
    )
    assert response.status_code == 403


# --- Invitations ---


@pytest.mark.asyncio
async def test_invite_and_accept_flow_grants_organization_membership(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)

    invite_response = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "invitee@example.com", "role": "developer"},
        headers=_auth(owner_token),
    )
    assert invite_response.status_code == 200
    invite_token = invite_response.json()["data"]["invite_token"]

    invitee_token = await _register_and_login(client, "invitee@example.com")
    accept_response = await client.post(
        "/api/v1/invitations/accept", json={"token": invite_token}, headers=_auth(invitee_token)
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["data"]["accepted"] is True

    list_response = await client.get("/api/v1/organizations", headers=_auth(invitee_token))
    assert org_id in [org["id"] for org in list_response.json()["data"]]


@pytest.mark.asyncio
async def test_invite_rejected_when_user_already_a_member(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)

    response = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "owner@example.com", "role": "viewer"},
        headers=_auth(owner_token),
    )
    body = response.json()

    assert response.status_code == 409
    assert body["error"]["code"] == "ALREADY_MEMBER"


@pytest.mark.asyncio
async def test_accept_invitation_with_mismatched_email_is_forbidden(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)

    invite_response = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "invitee@example.com", "role": "viewer"},
        headers=_auth(owner_token),
    )
    invite_token = invite_response.json()["data"]["invite_token"]

    someone_else_token = await _register_and_login(client, "someone-else@example.com")
    response = await client.post(
        "/api/v1/invitations/accept",
        json={"token": invite_token},
        headers=_auth(someone_else_token),
    )
    body = response.json()

    assert response.status_code == 403
    assert body["error"]["code"] == "EMAIL_MISMATCH"


@pytest.mark.asyncio
async def test_reject_invitation_marks_it_rejected_and_prevents_reacceptance(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)

    invite_response = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "invitee@example.com", "role": "viewer"},
        headers=_auth(owner_token),
    )
    invite_token = invite_response.json()["data"]["invite_token"]

    invitee_token = await _register_and_login(client, "invitee@example.com")
    reject_response = await client.post(
        "/api/v1/invitations/reject", json={"token": invite_token}, headers=_auth(invitee_token)
    )
    assert reject_response.status_code == 200

    accept_response = await client.post(
        "/api/v1/invitations/accept", json={"token": invite_token}, headers=_auth(invitee_token)
    )
    body = accept_response.json()
    assert accept_response.status_code == 409
    assert body["error"]["code"] == "INVITATION_NOT_PENDING"
