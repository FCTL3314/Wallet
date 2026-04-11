async def test_register_success(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "new@wallet.app", "password": "NewUser12"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@wallet.app"
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies


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
    assert data["email"] == "test@wallet.app"
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies


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
    # Login first — httpx stores cookies automatically
    await client.post(
        "/api/auth/login",
        json={"email": "test@wallet.app", "password": "Test1234"},
    )

    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 204
    # New cookies issued
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies


async def test_refresh_revoked_token(client, test_user):
    await client.post(
        "/api/auth/login",
        json={"email": "test@wallet.app", "password": "Test1234"},
    )
    old_refresh = client.cookies.get("refresh_token")

    # First refresh — rotates the token, httpx gets new cookies
    await client.post("/api/auth/refresh")

    # Restore the now-revoked refresh token
    client.cookies.set("refresh_token", old_refresh)

    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["code"] == "auth/invalid_refresh_token"


async def test_refresh_no_cookie(client):
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


async def test_logout(client, test_user):
    await client.post(
        "/api/auth/login",
        json={"email": "test@wallet.app", "password": "Test1234"},
    )

    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 204

    # Cookies cleared — refresh should fail
    resp = await client.post("/api/auth/refresh")
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
