import redis.asyncio as aioredis
from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthInvalidToken, AuthUserNotFound
from app.core.redis import get_redis as _get_redis_pool
from app.core.security import decode_access_token
from app.models.user import User


def get_redis() -> aioredis.Redis:
    return _get_redis_pool()


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if access_token is None:
        raise AuthInvalidToken()
    user_id = decode_access_token(access_token)
    if user_id is None:
        raise AuthInvalidToken()
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthUserNotFound()
    return user
