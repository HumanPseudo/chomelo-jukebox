from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_music_provider
from app.core.exceptions import AppError
from app.main import app
from app.providers.music import MusicProvider, MusicProviderError, ResolvedTrack, TrackInfo
from app.providers.ytdlp import YtDlpProvider

_transport = ASGITransport(app=app)
_BASE = "http://test"
_PASSWORD = "secure123"


class FakeMusicProvider(MusicProvider):
    fail_worker: bool

    def __init__(self, fail_worker: bool = False) -> None:
        self.fail_worker = fail_worker

    async def search(self, query: str, limit: int = 5) -> list[TrackInfo]:
        if self.fail_worker:
            raise MusicProviderError()
        return [
            TrackInfo(
                provider="youtube",
                track_id="abc123",
                title=query,
                artist="Rick Astley",
                duration_seconds=213,
                thumbnail_url="https://i.ytimg.com/vi/abc123/hqdefault.jpg",
            )
        ]

    async def get_track(self, track_id: str) -> TrackInfo:
        if self.fail_worker:
            raise MusicProviderError()
        if track_id == "missing":
            raise AppError("track no encontrado", code="track_not_found", status_code=404)
        return TrackInfo(
            provider="youtube",
            track_id=track_id,
            title="Never Gonna Give You Up",
            artist="Rick Astley",
            duration_seconds=213,
        )

    async def resolve(self, track_id: str) -> ResolvedTrack:
        if self.fail_worker:
            raise MusicProviderError()
        if track_id == "missing":
            raise AppError("track no encontrado", code="track_not_found", status_code=404)
        return ResolvedTrack(
            provider="youtube",
            track_id=track_id,
            title="Never Gonna Give You Up",
            artist="Rick Astley",
            stream_url="https://example.com/audio.m4a",
            expires_at=datetime.now(UTC) + timedelta(hours=6),
        )


async def _token(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "music@test.com", "password": _PASSWORD},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


def _override(provider: FakeMusicProvider) -> None:
    app.dependency_overrides[get_music_provider] = lambda: provider


async def test_search_requires_auth():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.get("/api/v1/music/search", params={"q": "never gonna"})
    assert r.status_code == 401


async def test_search_ok():
    _override(FakeMusicProvider())
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _token(c)
        r = await c.get(
            "/api/v1/music/search",
            params={"q": "never gonna", "limit": 3},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body[0]["track_id"] == "abc123"
    assert body[0]["artist"] == "Rick Astley"


async def test_search_validation():
    _override(FakeMusicProvider())
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _token(c)
        r = await c.get(
            "/api/v1/music/search",
            params={"q": "  "},
            headers={"Authorization": f"Bearer {token}"},
        )
        r2 = await c.get(
            "/api/v1/music/search",
            params={"limit": 99},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200  # query vacío -> lista vacía
    assert r.json() == []
    assert r2.status_code == 422


async def test_track_info_ok():
    _override(FakeMusicProvider())
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _token(c)
        r = await c.get(
            "/api/v1/music/tracks/abc123",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert r.json()["title"] == "Never Gonna Give You Up"


async def test_track_not_found():
    _override(FakeMusicProvider())
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _token(c)
        r = await c.get(
            "/api/v1/music/tracks/missing",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 404
    assert r.json()["code"] == "track_not_found"


async def test_stream_ok():
    _override(FakeMusicProvider())
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _token(c)
        r = await c.get(
            "/api/v1/music/tracks/abc123/stream",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["stream_url"].startswith("https://")
    assert body["expires_at"]


async def test_worker_down_returns_502():
    _override(FakeMusicProvider(fail_worker=True))
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        token = await _token(c)
        r = await c.get(
            "/api/v1/music/tracks/abc123",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 502
    body = r.json()
    assert body["code"] == "music_provider_error"


# ---------- YtDlpProvider (unit) ----------


def _json_response(payload: dict):
    return httpx.MockTransport(lambda request: httpx.Response(200, json=payload))


async def test_ytdlp_provider_search_parsing():
    transport = _json_response(
        {
            "items": [
                {
                    "provider": "youtube",
                    "track_id": "abc",
                    "title": "Never Gonna",
                    "artist": "Rick",
                    "duration_seconds": 213,
                    "thumbnail_url": None,
                }
            ]
        }
    )
    provider = YtDlpProvider(transport=transport, timeout=2.0)
    items = await provider.search("never", limit=1)
    assert len(items) == 1
    assert items[0].track_id == "abc"
    assert items[0].artist == "Rick"


async def test_ytdlp_provider_stream_parsing():
    transport = _json_response(
        {
            "provider": "youtube",
            "track_id": "abc",
            "title": "T",
            "artist": "",
            "stream_url": "https://example.com/a.m4a",
            "expires_at": "2026-09-16T00:00:00+00:00",
        }
    )
    provider = YtDlpProvider(transport=transport, timeout=2.0)
    track = await provider.resolve("abc")
    assert track.stream_url == "https://example.com/a.m4a"
    assert track.expires_at is not None


async def test_ytdlp_provider_worker_down():
    def _boom(request: httpx.Request):
        raise httpx.ConnectError("connection refused")

    provider = YtDlpProvider(transport=httpx.MockTransport(_boom), timeout=1.0)
    with pytest.raises(MusicProviderError):
        await provider.search("x")


async def test_ytdlp_provider_non_200():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(502, json={"detail": "x", "code": "worker_search_error"})
    )
    provider = YtDlpProvider(transport=transport, timeout=1.0)
    with pytest.raises(MusicProviderError):
        await provider.get_track("abc")
