import pytest


async def test_register_success(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "new@wallet.app", "password": "NewUser12"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_register_weak_password(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "weak@wallet.app", "password": "short"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "auth/weak_password"


async def test_register_duplicate_email(client, test_user):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "test@wallet.app", "password": "Test1234"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "auth/email_taken"


async def test_login_success(client, test_user):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "test@wallet.app", "password": "Test1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client, test_user):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "test@wallet.app", "password": "Wrong999"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "auth/invalid_credentials"


async def test_login_nonexistent_email(client):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@wallet.app", "password": "Test1234"},
    )
    assert resp.status_code == 401


async def test_refresh_success(client, test_user):
    # Login first to get a refresh token
    login = await client.post(
        "/api/auth/login",
        json={"email": "test@wallet.app", "password": "Test1234"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # New refresh token should differ (rotation)
    assert data["refresh_token"] != refresh_token


async def test_refresh_revoked_token(client, test_user):
    login = await client.post(
        "/api/auth/login",
        json={"email": "test@wallet.app", "password": "Test1234"},
    )
    refresh_token = login.json()["refresh_token"]

    # Use the refresh token once (revokes it)
    await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    # Try again — should fail
    resp = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "auth/invalid_refresh_token"


async def test_refresh_invalid_token(client):
    resp = await client.post(
        "/api/auth/refresh", json={"refresh_token": "bogus-token"}
    )
    assert resp.status_code == 401


async def test_logout(client, test_user):
    login = await client.post(
        "/api/auth/login",
        json={"email": "test@wallet.app", "password": "Test1234"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post(
        "/api/auth/logout", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 204

    # Refresh should now fail
    resp = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 401


async def test_me_authenticated(auth_client, test_user):
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@wallet.app"
    assert data["id"] == test_user.id


async def test_me_unauthenticated(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
