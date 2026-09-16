from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.api.deps import get_clock
from app.main import app
from tests.helpers import (
    BASE,
    add_item,
    auth,
    make_jukebox_x2,
    transport,
)


async def _play_songs(client: AsyncClient, token: str, jukebox_id: int, count: int) -> None:
    """Añade `count` canciones y las reproduce todas (queda histórico)."""
    for i in range(count):
        await add_item(client, token, jukebox_id, f"s{i:03d}")
    await client.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(token))
    for _ in range(count):
        s = await client.post(f"/api/v1/jukeboxes/{jukebox_id}/player/next", headers=auth(token))
        assert s.status_code == 204, s.text


def _game_path(jukebox_id: int, game_key: str = "guess_the_song") -> str:
    return f"/api/v1/jukeboxes/{jukebox_id}/games/{game_key}"


async def _start_round(
    client: AsyncClient, token: str, jukebox_id: int, game_key: str = "guess_the_song"
) -> dict:
    r = await client.post(
        f"{_game_path(jukebox_id, game_key)}/rounds", headers=auth(token), json={}
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_games_require_auth():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        for method in ("get", "post"):
            r = await getattr(c, method)(
                "/api/v1/jukeboxes/1/games/guess_the_song/rounds",
            )
            assert r.status_code == 401


async def test_unknown_game_404():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/games/minefield/rounds",
            headers=auth(owner_token),
            json={},
        )
    assert r.status_code == 404
    assert r.json()["code"] == "game_not_found"


async def test_not_enough_songs_409():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 3)
        r = await c.post(f"{_game_path(jukebox_id)}/rounds", headers=auth(owner_token), json={})
    assert r.status_code == 409
    assert r.json()["code"] == "not_enough_songs"


async def test_start_round_and_duplicate_409():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 4)
        round_ = await _start_round(c, owner_token, jukebox_id)
        dup = await c.post(f"{_game_path(jukebox_id)}/rounds", headers=auth(owner_token), json={})
    assert round_["status"] == "OPEN"
    assert round_["game_name"] == "Guess the Song"
    assert len(round_["options"]) == 4
    assert round_["correct_title"] is None  # la respuesta sigue secreta
    assert round_["track_id"] in {f"s{i:03d}" for i in range(4)}
    assert (
        f"Titulo {round_['track_id']}" in round_["options"]
    )  # la respuesta está oculta entre las opciones
    assert dup.status_code == 409
    assert dup.json()["code"] == "round_in_progress"


async def test_plain_member_cannot_start_round():
    """Solo MODERATOR+ lanza rondas; un MEMBER normal solo participa."""
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 4)
        r = await c.post(f"{_game_path(jukebox_id)}/rounds", headers=auth(member_token), json={})
    assert r.status_code == 403
    assert r.json()["code"] == "insufficient_role"


async def test_plain_member_can_answer_round_started_by_admin():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 4)
        round_ = await _start_round(c, owner_token, jukebox_id)
        answer_title = f"Titulo {round_['track_id']}"
        r = await c.post(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
            headers=auth(member_token),
            json={"title": answer_title},
        )
    assert r.status_code == 200
    assert r.json()["correct"] is True


async def test_correct_answer_finishes_round_and_grants_xp():
    owner_token, _member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 4)
        before = (await c.get("/api/v1/users/me/profile", headers=auth(owner_token))).json()["xp"]
        round_ = await _start_round(c, owner_token, jukebox_id)
        answer_title = f"Titulo {round_['track_id']}"  # el test conoce los títulos que añadió
        r = await c.post(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
            headers=auth(owner_token),
            json={"title": answer_title},
        )
        detail = await c.get(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}", headers=auth(owner_token)
        )
        after = (await c.get("/api/v1/users/me/profile", headers=auth(owner_token))).json()["xp"]
    body = r.json()
    assert r.status_code == 200
    assert body["correct"] is True
    assert body["points"] >= 10
    assert body["correct_title"] == answer_title
    assert body["round_status"] == "FINISHED"
    assert detail.json()["status"] == "FINISHED"
    assert detail.json()["correct_title"] == answer_title
    assert detail.json()["my_attempt"]["correct"] is True
    assert after == before + body["points"]


async def test_wrong_answer_gives_zero_points():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 4)
        round_ = await _start_round(c, owner_token, jukebox_id)
        wrong = next(t for t in round_["options"] if t != f"Titulo {round_['track_id']}")
        r = await c.post(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
            headers=auth(member_token),
            json={"title": wrong},
        )
    body = r.json()
    assert r.status_code == 200
    assert body["correct"] is False
    assert body["points"] == 0
    assert body["correct_title"] is None  # no se filtra la respuesta


async def test_second_guess_on_finished_round_409():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 4)
        round_ = await _start_round(c, owner_token, jukebox_id)
        await c.post(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
            headers=auth(owner_token),
            json={"title": f"Titulo {round_['track_id']}"},
        )
        r = await c.post(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
            headers=auth(member_token),
            json={"title": f"Titulo {round_['track_id']}"},
        )
    assert r.status_code == 409
    assert r.json()["code"] == "round_finished"


async def test_same_user_cannot_answer_twice():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 4)
        round_ = await _start_round(c, owner_token, jukebox_id)
        wrong = next(t for t in round_["options"] if t != f"Titulo {round_['track_id']}")
        r2 = await c.post(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
            headers=auth(owner_token),
            json={"title": wrong},
        )
        r3 = await c.post(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
            headers=auth(owner_token),
            json={"title": wrong},
        )
    assert r2.status_code == 200
    assert r2.json()["correct"] is False
    assert r3.status_code == 409
    assert r3.json()["code"] == "already_answered"


async def test_invalid_guess_422():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await _play_songs(c, owner_token, jukebox_id, 4)
        round_ = await _start_round(c, owner_token, jukebox_id)
        r = await c.post(
            f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
            headers=auth(owner_token),
            json={"title": "Canción que no existe"},
        )
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_guess"


async def test_round_expires_automatically():
    fake = {"now": datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)}

    def _fake_clock():
        return fake["now"]

    app.dependency_overrides[get_clock] = lambda: _fake_clock
    try:
        owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
        async with AsyncClient(transport=transport, base_url=BASE) as c:
            await _play_songs(c, owner_token, jukebox_id, 4)
            round_ = await _start_round(c, owner_token, jukebox_id)
            # la ronda vence en 60s según el reloj real de la creación
            fake["now"] += timedelta(seconds=61)
            detail = await c.get(
                f"{_game_path(jukebox_id)}/rounds/{round_['id']}", headers=auth(owner_token)
            )
            answer = await c.post(
                f"{_game_path(jukebox_id)}/rounds/{round_['id']}/answer",
                headers=auth(owner_token),
                json={"title": f"Titulo {round_['track_id']}"},
            )
            finished = await c.get(
                f"{_game_path(jukebox_id)}/rounds?status=FINISHED", headers=auth(owner_token)
            )
    finally:
        app.dependency_overrides.pop(get_clock, None)

    assert detail.json()["status"] == "FINISHED"
    assert detail.json()["finished_at"] == detail.json()["expires_at"]
    assert answer.status_code == 409
    assert answer.json()["code"] == "round_finished"
    assert any(r["id"] == round_["id"] for r in finished.json())
