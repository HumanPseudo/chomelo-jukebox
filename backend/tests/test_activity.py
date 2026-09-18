from httpx import AsyncClient

from tests.helpers import BASE, add_item, auth, make_jukebox_x2, transport


async def test_activity_requires_auth():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.get("/api/v1/jukeboxes/1/activity")
    assert r.status_code == 401


async def test_activity_member_forbidden():
    _owner, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.get(
            f"/api/v1/jukeboxes/{jukebox_id}/activity",
            headers=auth(member_token),
        )
    assert r.status_code == 403
    assert r.json()["code"] == "insufficient_role"


async def test_activity_limit_validation():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        assert (
            await c.get(
                f"/api/v1/jukeboxes/{jukebox_id}/activity?limit=0", headers=auth(owner_token)
            )
        ).status_code == 422
        assert (
            await c.get(
                f"/api/v1/jukeboxes/{jukebox_id}/activity?limit=101", headers=auth(owner_token)
            )
        ).status_code == 422


async def test_activity_aggregates_existing_events():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id)).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        poll = (
            await c.post(
                f"/api/v1/jukeboxes/{jukebox_id}/polls",
                headers=auth(owner_token),
                json={"question": "¿Sí o no?", "options": ["Sí", "No"]},
            )
        ).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(member_token),
            json={"option_id": poll["options"][0]["id"]},
        )
        r = await c.get(
            f"/api/v1/jukeboxes/{jukebox_id}/activity",
            headers=auth(owner_token),
        )
    assert r.status_code == 200, r.text
    kinds = {e["kind"] for e in r.json()}
    assert {
        "queue.add",
        "track.played",
        "vote",
        "poll.created",
        "poll.vote",
        "member.joined",
    } <= kinds
    # viene ordenada de más reciente a más antigua
    times = [e["created_at"] for e in r.json()]
    assert times == sorted(times, reverse=True)


async def test_activity_includes_display_names():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await c.patch(
            "/api/v1/users/me/profile",
            headers=auth(owner_token),
            json={"display_name": "Radio Pirata"},
        )
        await add_item(c, owner_token, jukebox_id)
        r = await c.get(
            f"/api/v1/jukeboxes/{jukebox_id}/activity",
            headers=auth(owner_token),
        )
    add = next(e for e in r.json() if e["kind"] == "queue.add")
    assert add["display_name"] == "Radio Pirata"
    assert add["title"] == "Titulo abc"


async def test_activity_does_not_leak_open_round_secret():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        for i in range(4):
            await add_item(c, owner_token, jukebox_id, f"s{i:03d}")
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        for _ in range(4):
            await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/next", headers=auth(owner_token))
        round_ = (
            await c.post(
                f"/api/v1/jukeboxes/{jukebox_id}/games/guess_the_song/rounds",
                headers=auth(owner_token),
                json={},
            )
        ).json()
        r = await c.get(
            f"/api/v1/jukeboxes/{jukebox_id}/activity",
            headers=auth(owner_token),
        )
    assert r.status_code == 200, r.text
    secret = f"Titulo {round_['track_id']}"
    round_events = [e for e in r.json() if e["kind"] == "game.round"]
    assert round_events, "la ronda iniciada debe aparecer en la actividad"
    for entry in round_events:
        assert secret not in (entry["title"] or ""), (
            "la actividad de la ronda no debe revelar la respuesta"
        )
