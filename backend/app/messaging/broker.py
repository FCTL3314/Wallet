from faststream.redis import RedisBroker

from app.core.config import settings

broker = RedisBroker(settings.REDIS_URL)
