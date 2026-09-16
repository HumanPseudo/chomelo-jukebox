import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: aioredis.Redis | None = None


def get_client() -> aioredis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = aioredis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=1
            )
        except Exception:
            return None
    return _client


async def is_rate_limited(key: str, *, limit: int, window: int) -> bool:
    """Chequea/baja un contador en Redis. Si Redis no está disponible, permite pasar."""
    client = get_client()
    if client is None:
        return False
    try:
        redis_key = f"rate:{key}"
        count = await client.incr(redis_key)
        if count == 1:
            await client.expire(redis_key, window)
        return count > limit
    except Exception:
        logger.warning("rate limit check failed; allowing request", exc_info=True)
        return False
