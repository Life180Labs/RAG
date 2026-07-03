import pytest

VALID_PASSWORD = "Str0ng!Passw0rd"


async def _register(
    client, email="user@example.com", password=VALID_PASSWORD, full_name="Ada Lovelace"
):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


async def _login(client, email="user@example.com", password=VALID_PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


@pytest.mark.asyncio
async def test_register_creates_user_with_default_viewer_role(client):
    response = await _register(client)
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["email"] == "user@example.com"
    assert body["data"]["role"] == "viewer"
    assert "hashed_password" not in body["data"]


@pytest.mark.asyncio
async def test_register_rejects_weak_password(client):
    response = await _register(client, password="short1!")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(client):
    await _register(client)
    response = await _register(client)

    body = response.json()
    assert response.status_code == 409
    assert body["success"] is False
    assert body["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_login_returns_token_pair(client):
    await _register(client)
    response = await _login(client)
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client):
    await _register(client)
    response = await _login(client, password="WrongPassw0rd!")
    body = response.json()

    assert response.status_code == 401
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_account_locks_after_max_failed_attempts(client):
    await _register(client)

    for _ in range(5):
        await _login(client, password="WrongPassw0rd!")

    response = await _login(client, password=VALID_PASSWORD)
    body = response.json()

    assert response.status_code == 403
    assert body["error"]["code"] == "ACCOUNT_LOCKED"


@pytest.mark.asyncio
async def test_me_requires_bearer_token(client):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user_with_valid_token(client):
    await _register(client)
    login_response = await _login(client)
    access_token = login_response.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_refresh_rotates_tokens_and_invalidates_old_refresh_token(client):
    await _register(client)
    login_response = await _login(client)
    old_refresh_token = login_response.json()["data"]["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()["data"]
    assert new_tokens["refresh_token"] != old_refresh_token

    replay_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert replay_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session(client):
    await _register(client)
    login_response = await _login(client)
    refresh_token = login_response.json()["data"]["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 200

    refresh_after_logout = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_after_logout.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password_never_reveals_account_existence(client):
    await _register(client)

    known = await client.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})
    unknown = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json()["data"]["message"] == unknown.json()["data"]["message"]


@pytest.mark.asyncio
async def test_reset_password_with_valid_token_allows_new_login(client):
    await _register(client)
    forgot_response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "user@example.com"}
    )
    reset_token = forgot_response.json()["data"]["reset_token"]

    new_password = "N3wStr0ng!Passw0rd"
    reset_response = await client.post(
        "/api/v1/auth/reset-password",
        json={"reset_token": reset_token, "new_password": new_password},
    )
    assert reset_response.status_code == 200

    old_login = await _login(client, password=VALID_PASSWORD)
    assert old_login.status_code == 401

    new_login = await _login(client, password=new_password)
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_token_is_single_use(client):
    await _register(client)
    forgot_response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "user@example.com"}
    )
    reset_token = forgot_response.json()["data"]["reset_token"]

    payload = {"reset_token": reset_token, "new_password": "N3wStr0ng!Passw0rd"}
    first = await client.post("/api/v1/auth/reset-password", json=payload)
    second = await client.post("/api/v1/auth/reset-password", json=payload)

    assert first.status_code == 200
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_viewer_cannot_access_admin_only_route(client):
    # No admin-only route exists yet in Phase 1; this exercises the
    # require_role() dependency directly against a throwaway route to
    # prove RBAC route guards work end to end.
    from fastapi import Depends

    from app.api.deps import require_role
    from app.main import app as fastapi_app
    from app.models.user import User, UserRole

    @fastapi_app.get("/api/v1/_test/admin-only")
    async def _admin_only(user: User = Depends(require_role(UserRole.ADMIN))):
        return {"ok": True}

    await _register(client)
    login_response = await _login(client)
    access_token = login_response.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/_test/admin-only", headers={"Authorization": f"Bearer {access_token}"}
    )
    body = response.json()

    assert response.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"
