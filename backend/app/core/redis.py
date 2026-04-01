import redis.asyncio as aioredis

from app.core.config import settings

redis_pool: aioredis.Redis | None = None


async def init_redis() -> None:
    global redis_pool
    redis_pool = aioredis.from_url(settings.REDIS_URL, decode_responses=False)


async def close_redis() -> None:
    if redis_pool is not None:
        await redis_pool.aclose()


def get_redis() -> aioredis.Redis:
    assert redis_pool is not None, "Redis pool is not initialized"
    return redis_pool
