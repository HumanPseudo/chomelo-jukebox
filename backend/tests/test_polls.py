from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from tests.helpers import (
    BASE,
    auth,
    make_jukebox_x2,
    register_user,
    transport,
)

_POLL = {
    "question": "¿Qué canción sigue?",
    "options": ["Rock", "Pop", "Electrónica"],
}


async def _create_poll(
    client: AsyncClient, token: str, jukebox_id: int, payload: dict | None = None
):
    return await client.post(
        f"/api/v1/jukeboxes/{jukebox_id}/polls",
        headers=auth(token),
        json=payload or _POLL,
    )


async def _get(client: AsyncClient, token: str, jukebox_id: int, poll_id: int) -> dict:
    return (
        await client.get(f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll_id}", headers=auth(token))
    ).json()


async def _member_user_id(client: AsyncClient, owner_token: str, member_token: str) -> int:
    me = await client.get("/api/v1/users/me", headers=auth(member_token))
    return me.json()["id"]


# ---------- creación y permisos ----------


async def test_create_poll_requires_auth():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.post("/api/v1/jukeboxes/1/polls", json=_POLL)
    assert r.status_code == 401


async def test_create_poll_201():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await _create_poll(c, owner_token, jukebox_id)
        body = r.json()
    assert r.status_code == 201
    assert body["question"] == _POLL["question"]
    assert body["status"] == "OPEN"
    assert [o["text"] for o in body["options"]] == _POLL["options"]
    assert [o["votes"] for o in body["options"]] == [0, 0, 0]
    assert body["my_option_id"] is None


async def test_create_poll_one_option_422():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await _create_poll(c, owner_token, jukebox_id, {"question": "q", "options": ["solo"]})
    assert r.status_code == 422


async def test_guest_cannot_create_poll():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        uid = await _member_user_id(c, owner_token, member_token)
        await c.patch(
            f"/api/v1/jukeboxes/{jukebox_id}/members/{uid}",
            headers=auth(owner_token),
            json={"role": "GUEST"},
        )
        r = await _create_poll(c, member_token, jukebox_id)
    assert r.status_code == 403
    assert r.json()["code"] == "insufficient_role"


async def test_create_poll_duplicate_options_deduplicated():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await _create_poll(
            c,
            owner_token,
            jukebox_id,
            {"question": "q", "options": ["Rock", "rock", "  Rock  ", "Pop"]},
        )
    assert r.status_code == 201
    assert [o["text"] for o in r.json()["options"]] == ["Rock", "rock", "Pop"]


# ---------- resultados y voto ----------


async def test_vote_updates_results():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        option_id = poll["options"][1]["id"]
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(member_token),
            json={"option_id": option_id},
        )
        body = await _get(c, member_token, jukebox_id, poll["id"])
    assert r.status_code == 204
    assert body["my_option_id"] == option_id
    assert body["total_votes"] == 1
    by_id = {o["id"]: o["votes"] for o in body["options"]}
    assert by_id[option_id] == 1


async def test_second_vote_rejected_409():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        option_id = poll["options"][0]["id"]
        other_id = poll["options"][1]["id"]
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(member_token),
            json={"option_id": option_id},
        )
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(member_token),
            json={"option_id": other_id},
        )
        body = await _get(c, member_token, jukebox_id, poll["id"])
    assert r.status_code == 409
    assert r.json()["code"] == "poll_already_voted"
    assert body["my_option_id"] == option_id


async def test_vote_invalid_option_404():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(owner_token),
            json={"option_id": 9999},
        )
    assert r.status_code == 404
    assert r.json()["code"] == "poll_option_not_found"


async def test_vote_on_closed_poll_409():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/close",
            headers=auth(owner_token),
        )
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(member_token),
            json={"option_id": poll["options"][0]["id"]},
        )
    assert r.status_code == 409
    assert r.json()["code"] == "poll_closed"


# ---------- cierre automático ----------


async def test_auto_close_by_closes_at():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
        poll = (
            await _create_poll(
                c,
                owner_token,
                jukebox_id,
                {"question": "q", "options": ["A", "B"], "closes_at": past},
            )
        ).json()
        assert poll["status"] == "OPEN"
        body = await _get(c, owner_token, jukebox_id, poll["id"])
    assert body["status"] == "CLOSED"


async def test_future_closes_at_stays_open():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        poll = (
            await _create_poll(
                c,
                owner_token,
                jukebox_id,
                {"question": "q", "options": ["A", "B"], "closes_at": future},
            )
        ).json()
        body = await _get(c, owner_token, jukebox_id, poll["id"])
    assert body["status"] == "OPEN"


# ---------- cerrar / borrar ----------


async def test_member_cannot_close_poll():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/close",
            headers=auth(member_token),
        )
    assert r.status_code == 403
    assert r.json()["code"] == "insufficient_role"


async def test_close_poll_and_results():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        option_id = poll["options"][0]["id"]
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(member_token),
            json={"option_id": option_id},
        )
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/close",
            headers=auth(owner_token),
        )
        body = r.json()
    assert r.status_code == 200
    assert body["status"] == "CLOSED"
    assert body["total_votes"] == 1
    assert body["options"][0]["votes"] == 1


async def test_list_polls_with_status_filter():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/close",
            headers=auth(owner_token),
        )
        all_polls = await c.get(f"/api/v1/jukeboxes/{jukebox_id}/polls", headers=auth(owner_token))
        closed = await c.get(
            f"/api/v1/jukeboxes/{jukebox_id}/polls?status=CLOSED",
            headers=auth(owner_token),
        )
        open_polls = await c.get(
            f"/api/v1/jukeboxes/{jukebox_id}/polls?status=OPEN",
            headers=auth(owner_token),
        )
    assert len(all_polls.json()) == 1
    assert len(closed.json()) == 1
    assert len(open_polls.json()) == 0


async def test_member_cannot_delete_poll():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        r = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}",
            headers=auth(member_token),
        )
    assert r.status_code == 403


async def test_delete_poll_204():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        r = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}",
            headers=auth(owner_token),
        )
        after = await c.get(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}",
            headers=auth(owner_token),
        )
    assert r.status_code == 204
    assert after.status_code == 404


async def test_vote_non_member_404():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        poll = (await _create_poll(c, owner_token, jukebox_id)).json()
        stranger_token = await register_user(c, "pstranger@test.com")
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{poll['id']}/vote",
            headers=auth(stranger_token),
            json={"option_id": poll["options"][0]["id"]},
        )
    assert r.status_code == 404
    assert r.json()["code"] == "not_member"
