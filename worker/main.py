from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Chomelo Music Worker", version="0.2.0")

_STREAM_TTL = timedelta(hours=6)


class WorkerError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@app.exception_handler(WorkerError)
async def worker_error_handler(request: Request, exc: WorkerError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


def _ydl_extractor(**extra):
    from yt_dlp import YoutubeDL

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bestaudio/best",
    }
    opts.update(extra)
    return YoutubeDL(opts)


def _thumbnail(info: dict) -> str | None:
    thumbnail = info.get("thumbnail")
    if isinstance(thumbnail, str) and thumbnail:
        return thumbnail
    thumbnails = info.get("thumbnails")
    if isinstance(thumbnails, list):
        for thumb in reversed(thumbnails):
            if isinstance(thumb, dict):
                url = thumb.get("url")
                if url:
                    return url
    return None


def _track_info(info: dict) -> dict:
    return {
        "provider": "youtube",
        "track_id": info.get("id") or "",
        "title": info.get("title") or "",
        "artist": (info.get("artist") or info.get("channel") or info.get("uploader") or ""),
        "duration_seconds": info.get("duration"),
        "thumbnail_url": _thumbnail(info),
    }


def _expires_at() -> str:
    return (datetime.now(UTC) + _STREAM_TTL).isoformat()


def _search_tracks(query: str, limit: int) -> list[dict]:
    with _ydl_extractor(extract_flat="in_playlist") as ydl:
        result = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
    return [_track_info(entry) for entry in result.get("entries", []) if entry]


def _full_extract(track_id: str) -> dict:
    url = f"https://www.youtube.com/watch?v={track_id}"
    with _ydl_extractor() as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries")
    if isinstance(entries, list) and entries:
        info = entries[0]
    return info


def _track_meta(track_id: str) -> dict:
    info = _full_extract(track_id)
    track = _track_info(info)
    if not track["track_id"]:
        raise WorkerError("no se encontró el track", code="track_not_found", status_code=404)
    return track


def _resolved(track_id: str) -> dict:
    info = _full_extract(track_id)
    stream_url = info.get("url")
    if not stream_url:
        raise WorkerError(
            "no hay stream disponible para este track",
            code="worker_stream_error",
            status_code=502,
        )
    track = _track_info(info)
    track["stream_url"] = stream_url
    track["expires_at"] = _expires_at()
    return track


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "chomelo-worker"}


@app.get("/search")
def search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, list[dict]]:
    try:
        return {"items": _search_tracks(q.strip(), limit)}
    except WorkerError:
        raise
    except Exception as exc:
        raise WorkerError(
            f"no se pudo buscar: {exc}", code="worker_search_error", status_code=502
        ) from exc


@app.get("/tracks/{track_id}")
def track_info(track_id: str) -> dict:
    try:
        return _track_meta(track_id)
    except WorkerError:
        raise
    except Exception as exc:
        raise WorkerError(
            f"no se pudo obtener el track: {exc}", code="worker_fetch_error", status_code=502
        ) from exc


@app.get("/tracks/{track_id}/stream")
def track_stream(track_id: str) -> dict:
    try:
        return _resolved(track_id)
    except WorkerError:
        raise
    except Exception as exc:
        raise WorkerError(
            f"no se pudo resolver el stream: {exc}", code="worker_stream_error", status_code=502
        ) from exc
