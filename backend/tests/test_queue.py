from httpx import ASGITransport, AsyncClient

from app.api.deps import get_music_provider
from app.main import app
from app.providers.music import MusicProvider, MusicProviderError, TrackInfo

_transport = ASGITransport(app=app)
_BASE = "http://test"
_PASSWORD = "secure123"


class FakeMusicProvider(MusicProvider):
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def search(self, query: str, limit: int = 5) -> list[TrackInfo]:
        raise MusicProviderError()

    async def get_track(self, track_id: str) -> TrackInfo:
        if self.fail:
            raise MusicProviderError()
        return TrackInfo(
            provider="youtube",
            track_id=track_id,
            title=f"Titulo {track_id}",
            artist="Artista",
            duration_seconds=180,
            thumbnail_url="https://i.ytimg.com/vi/x/default.jpg",
        )

    async def resolve(self, track_id: str):
        raise MusicProviderError()


def _use_fake_music(fail: bool = False) -> None:
    app.dependency_overrides[get_music_provider] = lambda: FakeMusicProvider(fail=fail)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


async def _make_jukebox_x2() -> tuple[str, str, int, str]:
    """Crea jukebox con owner y un member; devuelve tokens owner/member + id + codigo."""
    _use_fake_music()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        owner_token = await _register(c, "qowner@test.com")
        member_token = await _register(c, "qmember@test.com")
        jb = (
            await c.post(
                "/api/v1/jukeboxes",
                headers=_auth(owner_token),
                json={"name": "Cola"},
            )
        ).json()
        await c.post(
            "/api/v1/jukeboxes/join",
            headers=_auth(member_token),
            json={"invite_code": jb["invite_code"]},
        )
    return owner_token, member_token, int(jb["id"]), jb["invite_code"]


async def _add(client: AsyncClient, token: str, jukebox_id: int, track_id: str = "abc"):
    return await client.post(
        f"/api/v1/jukeboxes/{jukebox_id}/queue",
        headers=_auth(token),
        json={"track_id": track_id},
    )


# ---------- acceso ----------


async def test_queue_requires_auth():
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.get("/api/v1/jukeboxes/1/queue")
    assert r.status_code == 401


async def test_queue_non_member_404():
    _owner, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        stranger_token = await _register(c, "strangerq@test.com")
        r = await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(stranger_token))
    assert r.status_code == 404


# ---------- agregar / listar ----------


async def test_add_and_list_queue():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await _add(c, owner_token, jukebox_id, "abc")
        r2 = await _add(c, owner_token, jukebox_id, "def")
        queue = await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
    assert r.status_code == 201
    assert r.json()["title"] == "Titulo abc"
    assert r2.json()["status"] == "QUEUED"
    body = queue.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["track_id"] == "abc"
    assert body["items"][1]["track_id"] == "def"
    assert body["items"][0]["position"] == 0
    assert body["items"][1]["position"] == 1
    assert body["player"]["is_playing"] is False


async def test_add_invalid_track_502():
    _use_fake_music()
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    _use_fake_music(fail=True)
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await _add(c, owner_token, jukebox_id, "bad")
    assert r.status_code == 502
    assert r.json()["code"] == "music_provider_error"


# ---------- player ----------


async def test_play_empty_queue_409():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=_auth(owner_token))
    assert r.status_code == 409
    assert r.json()["code"] == "queue_empty"


async def test_play_pause_resume_skip_flow():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        first = (await _add(c, owner_token, jukebox_id, "aaa")).json()
        second = (await _add(c, owner_token, jukebox_id, "bbb")).json()
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=_auth(owner_token))
        q1 = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
        ).json()
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/pause", headers=_auth(owner_token))
        q2 = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
        ).json()
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/resume", headers=_auth(owner_token))
        q3 = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
        ).json()
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/next", headers=_auth(owner_token))
        q4 = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
        ).json()
    assert q1["player"]["is_playing"] is True
    assert q1["player"]["current_item_id"] == first["id"]
    assert [i["status"] for i in q1["items"]] == ["PLAYING", "QUEUED"]
    assert q2["player"]["is_playing"] is False
    assert q3["player"]["is_playing"] is True
    assert q4["player"]["current_item_id"] == second["id"]
    assert [i["status"] for i in q4["items"]] == ["PLAYING"]  # PLAYED sale de la cola


async def test_history_after_skip():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        first = (await _add(c, owner_token, jukebox_id, "aaa")).json()
        await _add(c, owner_token, jukebox_id, "bbb")
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=_auth(owner_token))
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/next", headers=_auth(owner_token))
        history = await c.get(f"/api/v1/jukeboxes/{jukebox_id}/history", headers=_auth(owner_token))
    body = history.json()
    assert len(body) == 1
    assert body[0]["id"] == first["id"]
    assert body[0]["status"] == "PLAYED"


async def test_player_previous_replays_last_track():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        first = (await _add(c, owner_token, jukebox_id, "aaa")).json()
        second = (await _add(c, owner_token, jukebox_id, "bbb")).json()
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=_auth(owner_token))
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/next", headers=_auth(owner_token))
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/player/previous", headers=_auth(owner_token)
        )
        q = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
        ).json()
        history = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/history", headers=_auth(owner_token))
        ).json()
    assert r.status_code == 204
    assert q["player"]["is_playing"] is True
    assert q["player"]["current_item_id"] == first["id"]
    # "second" (lo que sonaba) no se pierde: vuelve al frente de la cola.
    ids_by_status = {i["id"]: i["status"] for i in q["items"]}
    assert ids_by_status[first["id"]] == "PLAYING"
    assert ids_by_status[second["id"]] == "QUEUED"
    assert history == []


async def test_player_previous_without_history_409():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        await _add(c, owner_token, jukebox_id, "aaa")
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=_auth(owner_token))
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/player/previous", headers=_auth(owner_token)
        )
    assert r.status_code == 409
    assert r.json()["code"] == "no_previous_track"


async def test_seek_clamps_to_duration():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        await _add(c, owner_token, jukebox_id, "aaa")
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=_auth(owner_token))
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/player/seek",
            headers=_auth(owner_token),
            json={"position_ms": 999_999_999},  # duracion 180s = 180000 ms
        )
        q = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
        ).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/player/seek",
            headers=_auth(owner_token),
            json={"position_ms": 60_000},
        )
        q2 = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
        ).json()
    assert q["player"]["position_ms"] == 180_000
    assert q2["player"]["position_ms"] == 60_000


async def test_member_cannot_control_player():
    _owner, member_token, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        r = await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=_auth(member_token))
    assert r.status_code == 403


# ---------- quitar / mover ----------


async def test_member_removes_own_item():
    _owner, member_token, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        item = (await _add(c, member_token, jukebox_id, "own")).json()
        r = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}", headers=_auth(member_token)
        )
    assert r.status_code == 204


async def test_member_cannot_remove_other_item():
    owner_token, member_token, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        item = (await _add(c, owner_token, jukebox_id, "other")).json()
        r = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}", headers=_auth(member_token)
        )
    assert r.status_code == 403


async def test_owner_removes_any_item():
    owner_token, member_token, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        item = (await _add(c, member_token, jukebox_id, "other")).json()
        r = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}", headers=_auth(owner_token)
        )
    assert r.status_code == 204


async def test_remove_playing_item_409():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        item = (await _add(c, owner_token, jukebox_id, "play")).json()
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=_auth(owner_token))
        r = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}", headers=_auth(owner_token)
        )
    assert r.status_code == 409
    assert r.json()["code"] == "item_not_removable"


async def test_move_item():
    owner_token, _member, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        a = (await _add(c, owner_token, jukebox_id, "aaa")).json()
        _b = (await _add(c, owner_token, jukebox_id, "bbb")).json()
        await _add(c, owner_token, jukebox_id, "ccc")
        r = await c.patch(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{a['id']}/move",
            headers=_auth(owner_token),
            json={"position": 2},
        )
        queue = (
            await c.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=_auth(owner_token))
        ).json()
    assert r.status_code == 200
    order = [i["track_id"] for i in queue["items"]]
    assert order == ["bbb", "ccc", "aaa"]


async def test_member_cannot_move():
    _owner, member_token, jukebox_id, _code = await _make_jukebox_x2()
    async with AsyncClient(transport=_transport, base_url=_BASE) as c:
        item = (await _add(c, member_token, jukebox_id, "aaa")).json()
        r = await c.patch(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/move",
            headers=_auth(member_token),
            json={"position": 0},
        )
    assert r.status_code == 403
