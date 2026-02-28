from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import AuthEmailTaken, AuthInvalidCredentials, AuthInvalidRefreshToken, AuthWeakPassword
from app.core.password_policy import validate_password
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse, ChangeEmailRequest, ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["auth"])


async def _cleanup_tokens(user_id: int, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            (RefreshToken.revoked == True) | (RefreshToken.expires_at < now),  # noqa: E712
        )
    )


async def _issue_tokens(user_id: int, db: AsyncSession) -> TokenResponse:
    await _cleanup_tokens(user_id, db)
    access_token = create_access_token(user_id)
    raw_refresh, hashed_refresh = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user_id, token_hash=hashed_refresh, expires_at=expires_at))
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    violations = validate_password(body.password)
    if violations:
        raise AuthWeakPassword(violations)

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise AuthEmailTaken()

    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()
    return await _issue_tokens(user.id, db)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise AuthInvalidCredentials()
    return await _issue_tokens(user.id, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    expires_at = token.expires_at if token else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if not token or token.revoked or expires_at < now:
        raise AuthInvalidRefreshToken()

    token.revoked = True
    return await _issue_tokens(token.user_id, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one_or_none()
    if token and not token.revoked:
        token.revoked = True


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
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
    return user


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise AuthInvalidCredentials()
    violations = validate_password(body.new_password)
    if violations:
        raise AuthWeakPassword(violations)
    user.password_hash = hash_password(body.new_password)
