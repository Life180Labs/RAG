import pytest

from app.core.security import decrypt_credential, encrypt_credential
from tests.test_tenancy import _auth, _create_org, _register_and_login

VALID_PASSWORD = "Str0ng!Passw0rd"


def test_encrypt_decrypt_credential_round_trip():
    ciphertext = encrypt_credential("sk-super-secret-key")
    assert ciphertext != "sk-super-secret-key"
    assert decrypt_credential(ciphertext) == "sk-super-secret-key"


@pytest.mark.asyncio
async def test_upsert_and_list_provider_credential_masks_key(client):
    token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, token)

    create_response = await client.post(
        f"/api/v1/organizations/{org_id}/provider-credentials",
        json={"provider": "openai", "api_key": "sk-abc123def456"},
        headers=_auth(token),
    )
    body = create_response.json()

    assert create_response.status_code == 200, create_response.text
    assert body["data"]["provider"] == "openai"
    assert body["data"]["last_four"] == "f456"
    assert "api_key" not in body["data"]
    assert "encrypted_key" not in body["data"]

    list_response = await client.get(
        f"/api/v1/organizations/{org_id}/provider-credentials", headers=_auth(token)
    )
    list_body = list_response.json()

    assert list_response.status_code == 200
    assert len(list_body["data"]) == 1
    assert list_body["data"][0]["provider"] == "openai"
    assert list_body["data"][0]["last_four"] == "f456"


@pytest.mark.asyncio
async def test_upsert_same_provider_replaces_existing_credential(client):
    token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, token)

    await client.post(
        f"/api/v1/organizations/{org_id}/provider-credentials",
        json={"provider": "openai", "api_key": "sk-first-key-0001"},
        headers=_auth(token),
    )
    second_response = await client.post(
        f"/api/v1/organizations/{org_id}/provider-credentials",
        json={"provider": "openai", "api_key": "sk-second-key-9999"},
        headers=_auth(token),
    )
    assert second_response.status_code == 200

    list_response = await client.get(
        f"/api/v1/organizations/{org_id}/provider-credentials", headers=_auth(token)
    )
    list_body = list_response.json()

    assert len(list_body["data"]) == 1
    assert list_body["data"][0]["last_four"] == "9999"


@pytest.mark.asyncio
async def test_unknown_provider_rejected(client):
    token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, token)

    response = await client.post(
        f"/api/v1/organizations/{org_id}/provider-credentials",
        json={"provider": "not-a-real-provider", "api_key": "sk-abc123def456"},
        headers=_auth(token),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_admin_cannot_create_provider_credential(client):
    owner_token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, owner_token)

    invite_response = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=_auth(owner_token),
    )
    invite_token = invite_response.json()["data"]["invite_token"]
    viewer_token = await _register_and_login(client, "viewer@example.com")
    await client.post(
        "/api/v1/invitations/accept", json={"token": invite_token}, headers=_auth(viewer_token)
    )

    response = await client.post(
        f"/api/v1/organizations/{org_id}/provider-credentials",
        json={"provider": "openai", "api_key": "sk-abc123def456"},
        headers=_auth(viewer_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_provider_credential(client):
    token = await _register_and_login(client, "owner@example.com")
    org_id = await _create_org(client, token)

    create_response = await client.post(
        f"/api/v1/organizations/{org_id}/provider-credentials",
        json={"provider": "pinecone", "api_key": "pc-abc123def456"},
        headers=_auth(token),
    )
    credential_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/organizations/{org_id}/provider-credentials/{credential_id}",
        headers=_auth(token),
    )
    assert delete_response.status_code == 200

    list_response = await client.get(
        f"/api/v1/organizations/{org_id}/provider-credentials", headers=_auth(token)
    )
    assert list_response.json()["data"] == []
