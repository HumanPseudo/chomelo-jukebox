from datetime import UTC, datetime

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)

SAMPLE_INFO = {
    "id": "abc123",
    "title": "Never Gonna Give You Up",
    "artist": "Rick Astley",
    "duration": 213,
    "thumbnail": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_track_info_mapping():
    info = dict(SAMPLE_INFO, url="https://example.com/stream")
    assert main._track_info(info) == {
        "provider": "youtube",
        "track_id": "abc123",
        "title": "Never Gonna Give You Up",
        "artist": "Rick Astley",
        "duration_seconds": 213,
        "thumbnail_url": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
    }


def test_track_info_artist_fallback():
    info = {"id": "x", "title": "T", "uploader": "Channel U", "thumbnails": [{"url": "th.jpg"}]}
    out = main._track_info(info)
    assert out["artist"] == "Channel U"
    assert out["thumbnail_url"] == "th.jpg"


def test_search_endpoint(monkeypatch):
    monkeypatch.setattr(
        main,
        "_search_tracks",
        lambda q, limit: [main._track_info(SAMPLE_INFO)],
    )
    r = client.get("/search", params={"q": "never gonna", "limit": 2})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["track_id"] == "abc123"
    assert items[0]["artist"] == "Rick Astley"


def test_search_requires_q():
    r = client.get("/search")
    assert r.status_code == 422


def test_track_info_endpoint(monkeypatch):
    monkeypatch.setattr(main, "_track_meta", lambda tid: main._track_info(SAMPLE_INFO))
    r = client.get("/tracks/abc123")
    assert r.status_code == 200
    assert r.json()["track_id"] == "abc123"


def test_track_info_error(monkeypatch):
    monkeypatch.setattr(
        main,
        "_track_meta",
        lambda tid: (_ for _ in ()).throw(
            main.WorkerError("boom", code="worker_fetch_error", status_code=502)
        ),
    )
    r = client.get("/tracks/abc123")
    assert r.status_code == 502
    assert r.json()["code"] == "worker_fetch_error"


def test_stream_endpoint(monkeypatch):
    def _fake_resolved(tid):
        out = main._track_info(SAMPLE_INFO)
        out["stream_url"] = "https://example.com/audio.m4a"
        out["expires_at"] = "2026-09-16T00:00:00+00:00"
        return out

    monkeypatch.setattr(main, "_resolved", _fake_resolved)
    r = client.get("/tracks/abc123/stream")
    assert r.status_code == 200
    body = r.json()
    assert body["stream_url"].startswith("https://")
    assert body["expires_at"]


def test_expires_at_is_iso_utc():
    out = main._expires_at()
    parsed = datetime.fromisoformat(out)
    assert parsed.tzinfo is not None
    assert parsed.tzinfo == UTC
