import httpx

from app.core.config import settings
from app.providers.music import (
    MusicProvider,
    MusicProviderError,
    ResolvedTrack,
    TrackInfo,
)


class YtDlpProvider(MusicProvider):
    """MusicProvider que delega en el worker (yt-dlp) por HTTP."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or settings.worker_url).rstrip("/")
        self._timeout = timeout
        self._transport = transport
        self._http: httpx.AsyncClient | None = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            )
        return self._http

    async def _get(self, path: str, **params) -> dict:
        client = await self._client()
        try:
            response = await client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise MusicProviderError(
                f"el worker de música no responde: {type(exc).__name__}"
            ) from exc
        if response.status_code != 200:
            raise MusicProviderError("el worker de música devolvió un error")
        return response.json()

    async def search(self, query: str, limit: int = 5) -> list[TrackInfo]:
        data = await self._get("/search", q=query, limit=limit)
        return [TrackInfo.model_validate(item) for item in data.get("items", [])]

    async def get_track(self, track_id: str) -> TrackInfo:
        data = await self._get(f"/tracks/{track_id}")
        return TrackInfo.model_validate(data)

    async def resolve(self, track_id: str) -> ResolvedTrack:
        data = await self._get(f"/tracks/{track_id}/stream")
        return ResolvedTrack.model_validate(data)
