from fastapi import APIRouter, Depends, Query

from app.api.deps import get_music_provider
from app.core.security import get_current_user
from app.domain.user import User
from app.providers.music import MusicProvider, ResolvedTrack, TrackInfo
from app.services import music_service

router = APIRouter(prefix="/music", tags=["music"])


@router.get("/search", response_model=list[TrackInfo])
async def search_tracks(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=5, ge=1, le=20),
    provider: MusicProvider = Depends(get_music_provider),
    _: User = Depends(get_current_user),
) -> list[TrackInfo]:
    query = q.strip()
    if not query:
        return []
    return await music_service.search_tracks(provider, query, limit)


@router.get("/tracks/{track_id}", response_model=TrackInfo)
async def track_info(
    track_id: str,
    provider: MusicProvider = Depends(get_music_provider),
    _: User = Depends(get_current_user),
) -> TrackInfo:
    return await music_service.get_track(provider, track_id)


@router.get("/tracks/{track_id}/stream", response_model=ResolvedTrack)
async def track_stream(
    track_id: str,
    provider: MusicProvider = Depends(get_music_provider),
    _: User = Depends(get_current_user),
) -> ResolvedTrack:
    return await music_service.resolve_track(provider, track_id)
