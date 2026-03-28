from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def test_github_login_redirects(client: AsyncClient):
    resp = await client.get("/api/auth/github", follow_redirects=False)

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "github.com/login/oauth" in location


async def test_github_callback_creates_new_user_and_returns_tokens(
    client: AsyncClient, db_session: AsyncSession
):
    github_profile = {"id": 12345, "email": "gh@example.com", "login": "ghuser"}

    client.cookies.set("oauth_state", "xyz")
    with patch(
        "app.api.oauth.exchange_github_code",
        new=AsyncMock(return_value=github_profile),
    ):
        resp = await client.get(
            "/api/auth/github/callback",
            params={"code": "valid-code", "state": "xyz"},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "/oauth/callback" in location
    qs = parse_qs(urlparse(location).query)
    assert "access_token" in qs
    assert "refresh_token" in qs

    result = await db_session.execute(
        select(User).where(User.email == "gh@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.github_id == 12345


async def test_github_callback_returns_tokens_for_existing_github_user(
    client: AsyncClient, db_session: AsyncSession
):
    existing = User(
        email="gh-existing@example.com",
        password_hash="",
        github_id=12345,
    )
    db_session.add(existing)
    await db_session.flush()

    github_profile = {
        "id": 12345,
        "email": "gh-existing@example.com",
        "login": "ghuser",
    }

    client.cookies.set("oauth_state", "xyz")
    with patch(
        "app.api.oauth.exchange_github_code",
        new=AsyncMock(return_value=github_profile),
    ):
        resp = await client.get(
            "/api/auth/github/callback",
            params={"code": "valid-code", "state": "xyz"},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "/oauth/callback" in location
    qs = parse_qs(urlparse(location).query)
    assert "access_token" in qs
    assert "refresh_token" in qs

    result = await db_session.execute(select(User).where(User.github_id == 12345))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].id == existing.id


async def test_github_callback_returns_error_when_code_exchange_fails(
    client: AsyncClient,
):
    client.cookies.set("oauth_state", "xyz")
    with patch(
        "app.api.oauth.exchange_github_code",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.get(
            "/api/auth/github/callback",
            params={"code": "bad-code", "state": "xyz"},
        )

    assert resp.status_code in (400, 401)
    assert resp.json().get("code") == "auth/oauth_failed"


async def test_google_login_redirects(client: AsyncClient):
    resp = await client.get("/api/auth/google", follow_redirects=False)

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "accounts.google.com" in location


async def test_google_callback_creates_new_user_and_returns_tokens(
    client: AsyncClient, db_session: AsyncSession
):
    google_profile = {"sub": "g-sub-123", "email": "goo@example.com"}

    client.cookies.set("oauth_state", "xyz")
    with patch(
        "app.api.oauth.exchange_google_code",
        new=AsyncMock(return_value=google_profile),
    ):
        resp = await client.get(
            "/api/auth/google/callback",
            params={"code": "valid-code", "state": "xyz"},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "/oauth/callback" in location
    qs = parse_qs(urlparse(location).query)
    assert "access_token" in qs
    assert "refresh_token" in qs

    result = await db_session.execute(
        select(User).where(User.email == "goo@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.google_sub == "g-sub-123"


async def test_google_callback_returns_tokens_for_existing_google_user(
    client: AsyncClient, db_session: AsyncSession
):
    existing = User(
        email="goo-existing@example.com",
        password_hash="",
        google_sub="g-sub-123",
    )
    db_session.add(existing)
    await db_session.flush()

    google_profile = {"sub": "g-sub-123", "email": "goo-existing@example.com"}

    client.cookies.set("oauth_state", "xyz")
    with patch(
        "app.api.oauth.exchange_google_code",
        new=AsyncMock(return_value=google_profile),
    ):
        resp = await client.get(
            "/api/auth/google/callback",
            params={"code": "valid-code", "state": "xyz"},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "/oauth/callback" in location
    qs = parse_qs(urlparse(location).query)
    assert "access_token" in qs
    assert "refresh_token" in qs

    result = await db_session.execute(
        select(User).where(User.google_sub == "g-sub-123")
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].id == existing.id


async def test_google_callback_returns_error_when_code_exchange_fails(
    client: AsyncClient,
):
    client.cookies.set("oauth_state", "xyz")
    with patch(
        "app.api.oauth.exchange_google_code",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.get(
            "/api/auth/google/callback",
            params={"code": "bad-code", "state": "xyz"},
        )

    assert resp.status_code in (400, 401)
    assert resp.json().get("code") == "auth/oauth_failed"
