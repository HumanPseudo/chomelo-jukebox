from app.infra.music_cache import cache_get_track, cache_set_track
from app.providers.music import MusicProvider, ResolvedTrack, TrackInfo


async def search_tracks(provider: MusicProvider, query: str, limit: int) -> list[TrackInfo]:
    return await provider.search(query, limit=limit)


async def get_track(provider: MusicProvider, track_id: str) -> TrackInfo:
    cached = await cache_get_track(track_id)
    if cached is not None:
        return cached
    track = await provider.get_track(track_id)
    await cache_set_track(track_id, track)
    return track


async def resolve_track(provider: MusicProvider, track_id: str) -> ResolvedTrack:
    return await provider.resolve(track_id)
