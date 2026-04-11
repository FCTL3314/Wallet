import secrets

import httpx
from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import _issue_tokens, _set_auth_cookies
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthOAuthFailed
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["oauth"])


async def exchange_github_code(code: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            return None

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return None

        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        user_resp = await client.get(
            "https://api.github.com/user", headers=auth_headers
        )
        if user_resp.status_code != 200:
            return None

        user_data = user_resp.json()
        github_id = user_data.get("id")
        email: str | None = user_data.get("email")

        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails", headers=auth_headers
            )
            if emails_resp.status_code == 200:
                for entry in emails_resp.json():
                    if entry.get("primary") and entry.get("verified"):
                        email = entry.get("email")
                        break

        if not github_id or not email:
            return None

        return {"id": github_id, "email": email, "login": user_data.get("login", "")}


async def exchange_google_code(code: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            return None

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return None

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            return None

        info = userinfo_resp.json()
        sub = info.get("sub")
        email = info.get("email")

        if not sub or not email:
            return None

        return {"sub": sub, "email": email}


@router.get("/github")
async def github_login():
    state = secrets.token_urlsafe(16)
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        "&scope=user:email"
        f"&state={state}"
    )
    response = RedirectResponse(url=url, status_code=302)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=300,
        path="/",
    )
    return response


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str = "",
    state_cookie: str | None = Cookie(default=None, alias="oauth_state"),
    db: AsyncSession = Depends(get_db),
):
    if not state_cookie or state != state_cookie:
        raise AuthOAuthFailed("Invalid OAuth state parameter")

    profile = await exchange_github_code(code)
    if not profile:
        raise AuthOAuthFailed("GitHub did not return a valid profile")

    github_id: int = profile["id"]
    email: str = profile["email"]

    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.github_id = github_id
        else:
            user = User(email=email, password_hash=None, github_id=github_id)
            db.add(user)
            await db.flush()

    access_token, refresh_token = await _issue_tokens(user.id, db)
    redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/oauth/callback", status_code=302
    )
    _set_auth_cookies(redirect, access_token, refresh_token)
    redirect.delete_cookie("oauth_state", path="/")
    return redirect


@router.get("/google")
async def google_login():
    state = secrets.token_urlsafe(16)
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid email"
        f"&state={state}"
    )
    response = RedirectResponse(url=url, status_code=302)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=300,
        path="/",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str = "",
    state_cookie: str | None = Cookie(default=None, alias="oauth_state"),
    db: AsyncSession = Depends(get_db),
):
    if not state_cookie or state != state_cookie:
        raise AuthOAuthFailed("Invalid OAuth state parameter")

    profile = await exchange_google_code(code)
    if not profile:
        raise AuthOAuthFailed("Google did not return a valid profile")

    google_sub: str = profile["sub"]
    email: str = profile["email"]

    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.google_sub = google_sub
        else:
            user = User(email=email, password_hash=None, google_sub=google_sub)
            db.add(user)
            await db.flush()

    access_token, refresh_token = await _issue_tokens(user.id, db)
    redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/oauth/callback", status_code=302
    )
    _set_auth_cookies(redirect, access_token, refresh_token)
    redirect.delete_cookie("oauth_state", path="/")
    return redirect
