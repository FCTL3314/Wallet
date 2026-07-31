from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def test_github_login_redirects(client: AsyncClient):
    resp = await client.get("/api/auth/github", follow_redirects=False)

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "github.com/login/oauth" in location


async def test_github_callback_creates_new_user_and_sets_cookies(
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
    # Tokens are now in httpOnly cookies, not URL params
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies

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
    assert "/oauth/callback" in resp.headers.get("location", "")
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies

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
            follow_redirects=False,
        )

    # The callback is reached by top-level browser navigation, so failures go
    # back to the frontend with an error to render, not a raw JSON body.
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "/oauth/callback" in location
    assert "error=profile" in location


async def test_github_callback_refuses_to_link_existing_email(
    client: AsyncClient, db_session: AsyncSession
):
    """A GitHub identity must not attach itself to an account it does not own."""
    existing = User(email="victim@example.com", password_hash="hashed")
    db_session.add(existing)
    await db_session.flush()

    github_profile = {"id": 99999, "email": "victim@example.com", "login": "attacker"}

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
    assert "error=email_taken" in resp.headers.get("location", "")
    assert "access_token" not in resp.cookies

    await db_session.refresh(existing)
    assert existing.github_id is None


async def test_google_login_redirects(client: AsyncClient):
    resp = await client.get("/api/auth/google", follow_redirects=False)

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "accounts.google.com" in location


async def test_google_callback_creates_new_user_and_sets_cookies(
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
    assert "/oauth/callback" in resp.headers.get("location", "")
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies

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
    assert "/oauth/callback" in resp.headers.get("location", "")
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies

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
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "/oauth/callback" in location
    assert "error=profile" in location


async def test_google_callback_refuses_to_link_existing_email(
    client: AsyncClient, db_session: AsyncSession
):
    """A Google identity must not attach itself to an account it does not own."""
    existing = User(email="victim-goo@example.com", password_hash="hashed")
    db_session.add(existing)
    await db_session.flush()

    google_profile = {"sub": "g-sub-attacker", "email": "victim-goo@example.com"}

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
    assert "error=email_taken" in resp.headers.get("location", "")
    assert "access_token" not in resp.cookies

    await db_session.refresh(existing)
    assert existing.google_sub is None
