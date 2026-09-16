from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel

from app.core.exceptions import AppError


class TrackInfo(BaseModel):
    provider: str
    track_id: str
    title: str
    artist: str = ""
    duration_seconds: int | None = None
    thumbnail_url: str | None = None


class ResolvedTrack(TrackInfo):
    stream_url: str
    expires_at: datetime


class MusicProviderError(AppError):
    """El worker de música no responde o devolvió un error."""

    def __init__(
        self,
        message: str = "el proveedor de música no está disponible",
    ) -> None:
        super().__init__(message, code="music_provider_error", status_code=502)


class MusicProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[TrackInfo]: ...

    @abstractmethod
    async def get_track(self, track_id: str) -> TrackInfo: ...

    @abstractmethod
    async def resolve(self, track_id: str) -> ResolvedTrack: ...
