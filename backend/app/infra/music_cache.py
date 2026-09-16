import logging

import redis.asyncio as aioredis

from app.core.config import settings
from app.providers.music import TrackInfo

logger = logging.getLogger(__name__)

_client: aioredis.Redis | None = None


def _get_client() -> aioredis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = aioredis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=1
            )
        except Exception:
            return None
    return _client


async def cache_get_track(track_id: str) -> TrackInfo | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = await client.get(f"track:{track_id}")
        if raw is None:
            return None
        return TrackInfo.model_validate_json(raw)
    except Exception:
        logger.warning("track cache read failed", exc_info=True)
        return None


async def cache_set_track(track_id: str, track: TrackInfo) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        await client.set(
            f"track:{track_id}",
            track.model_dump_json(),
            ex=settings.music_cache_ttl_seconds,
        )
    except Exception:
        logger.warning("track cache write failed", exc_info=True)
