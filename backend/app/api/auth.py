from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    AuthEmailTaken,
    AuthInvalidCredentials,
    AuthInvalidRefreshToken,
    AuthWeakPassword,
)
from app.core.password_policy import validate_password
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UpdatePreferencesRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _cleanup_tokens(user_id: int, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            (RefreshToken.revoked == True) | (RefreshToken.expires_at < now),  # noqa: E712
        )
    )


async def _issue_tokens(user_id: int, db: AsyncSession) -> tuple[str, str]:
    """Returns (access_token, raw_refresh_token). Stores only hash of refresh token in DB."""
    await _cleanup_tokens(user_id, db)
    access_token = create_access_token(user_id)
    raw_refresh, hashed_refresh = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(
        RefreshToken(user_id=user_id, token_hash=hashed_refresh, expires_at=expires_at)
    )
    return access_token, raw_refresh


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    secure = not settings.DEV_MODE
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    violations = validate_password(body.password)
    if violations:
        raise AuthWeakPassword(violations)

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise AuthEmailTaken()

    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()
    access_token, refresh_token = await _issue_tokens(user.id, db)
    _set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise AuthInvalidCredentials()
    access_token, refresh_token = await _issue_tokens(user.id, db)
    _set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise AuthInvalidRefreshToken()
    token_hash = hash_refresh_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()

    if not token or token.revoked or token.expires_at < datetime.now(timezone.utc):
        raise AuthInvalidRefreshToken()

    token.revoked = True
    access_token, new_refresh = await _issue_tokens(token.user_id, db)
    _set_auth_cookies(response, access_token, new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()
        if token and not token.revoked:
            token.revoked = True
    _clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/me/complete-onboarding", response_model=UserResponse)
async def complete_onboarding(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(timezone.utc)
        await db.flush()
    return user


@router.patch("/me/email", response_model=UserResponse)
async def change_email(
    body: ChangeEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise AuthInvalidCredentials()
    existing = await db.execute(select(User).where(User.email == body.new_email))
    if existing.scalar_one_or_none():
        raise AuthEmailTaken()
    user.email = body.new_email
    await db.flush()
    return user


@router.patch("/me/preferences", response_model=UserResponse)
async def update_preferences(
    body: UpdatePreferencesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.base_currency_code = body.base_currency_code
    await db.flush()
    return user


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, user.password_hash):
        raise AuthInvalidCredentials()
    violations = validate_password(body.new_password)
    if violations:
        raise AuthWeakPassword(violations)
    user.password_hash = hash_password(body.new_password)
