from httpx import AsyncClient

from app.domain.user import level_for_xp
from tests.helpers import (
    BASE,
    add_item,
    auth,
    make_jukebox_x2,
    transport,
)


async def _profile(client: AsyncClient, token: str) -> dict:
    return (await client.get("/api/v1/users/me/profile", headers=auth(token))).json()


async def _setup_votes(
    client: AsyncClient, owner: str, member: str, jukebox_id: int
) -> tuple[int, int]:
    item_id = (await add_item(client, owner, jukebox_id, "aaa")).json()["id"]
    other = (await add_item(client, owner, jukebox_id, "bbb")).json()
    return item_id, other["id"]


async def test_profile_requires_auth():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.get("/api/v1/users/me/profile")
    assert r.status_code == 401


async def test_new_user_profile_defaults():
    owner_token, _member, _jb_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        body = await _profile(c, owner_token)
    assert body["xp"] == 0
    assert body["level"] == 1
    assert body["tracks_added"] == 0
    assert body["tracks_played"] == 0
    assert body["votes_cast"] == 0
    assert body["polls_created"] == 0
    assert body["poll_votes_cast"] == 0
    assert body["bio"] == ""


async def test_add_track_grants_xp_and_stats():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await add_item(c, owner_token, jukebox_id, "aaa")
        body = await _profile(c, owner_token)
    assert body["xp"] == 10
    assert body["tracks_added"] == 1


async def test_track_played_grants_xp_to_adder():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await add_item(c, member_token, jukebox_id, "aaa")
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        member_body = await _profile(c, member_token)
    # +10 por agregar + +20 porque su track empezó a sonar
    assert member_body["xp"] == 30
    assert member_body["tracks_played"] == 1


async def test_vote_and_poll_grants_xp():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item_id, other_id = await _setup_votes(c, owner_token, member_token, jukebox_id)
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{other_id}/vote",
            headers=auth(member_token),
        )
        member_id = (await c.get("/api/v1/users/me", headers=auth(member_token))).json()["id"]
        await c.patch(
            f"/api/v1/jukeboxes/{jukebox_id}/members/{member_id}",
            headers=auth(owner_token),
            json={"role": "MODERATOR"},
        )  # crear encuestas es cosa de MODERATOR+ (el oyente solo participa)
        poll = (
            await c.post(
                f"/api/v1/jukeboxes/{jukebox_id}/polls",
                headers=auth(member_token),
                json={"question": "q", "options": ["A", "B"]},
            )
        ).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(member_token),
            json={"option_id": poll["options"][0]["id"]},
        )
        body = await _profile(c, member_token)
    assert body["xp"] == 5 + 10 + 5  # vote + poll creada + poll votada
    assert body["votes_cast"] == 1
    assert body["polls_created"] == 1
    assert body["poll_votes_cast"] == 1
    assert item_id >= 1


async def test_xp_never_comes_from_client():
    owner_token, _member, _jb_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.patch(
            "/api/v1/users/me/profile",
            headers=auth(owner_token),
            json={"xp": 9999, "level": 50},
        )
        body = await _profile(c, owner_token)
    assert r.status_code == 200
    assert body["xp"] == 0  # el payload XP se ignora por el servidor
    assert body["level"] == 1


async def test_update_profile():
    owner_token, _member, _jb_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.patch(
            "/api/v1/users/me/profile",
            headers=auth(owner_token),
            json={
                "display_name": "DJ Demo",
                "bio": "amo la música",
                "avatar_url": "https://i.imgur.com/x.png",
            },
        )
        body = await _profile(c, owner_token)
    assert r.status_code == 200
    assert body["display_name"] == "DJ Demo"
    assert body["bio"] == "amo la música"
    assert body["avatar_url"] == "https://i.imgur.com/x.png"


async def test_listen_history():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await add_item(c, member_token, jukebox_id, "aaa")
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/skip", headers=auth(owner_token))
        history = await c.get("/api/v1/users/me/listen-history", headers=auth(member_token))
    body = history.json()
    assert len(body) == 1
    assert body[0]["track_id"] == "aaa"
    assert body[0]["jukebox_name"] == "Votos"
    assert "played_at" in body[0]


async def test_listen_history_empty_for_new_user():
    owner_token, _member, _jb_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        history = await c.get("/api/v1/users/me/listen-history", headers=auth(owner_token))
    assert history.json() == []


async def test_level_boundaries():
    assert level_for_xp(0) == 1
    assert level_for_xp(99) == 1
    assert level_for_xp(100) == 2
    assert level_for_xp(250) == 3
