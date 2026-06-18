import redis.asyncio as aioredis

from app.core.audit import AuditedRedis
from app.core.config import settings

_pool: aioredis.ConnectionPool | None = None


def init_redis() -> None:
    global _pool
    _pool = aioredis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    global _pool
    if _pool:
        await _pool.disconnect()
        _pool = None


def get_redis() -> aioredis.Redis:
    if _pool is None:
        raise RuntimeError("Redis pool not initialized")
    return AuditedRedis(aioredis.Redis(connection_pool=_pool))
