from httpx import AsyncClient

from tests.helpers import (
    BASE,
    add_item,
    auth,
    make_jukebox_x2,
    register_user,
    transport,
)


async def _queue(client: AsyncClient, token: str, jukebox_id: int) -> dict:
    return (await client.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=auth(token))).json()


async def _demote_to_guest(
    client: AsyncClient, owner_token: str, jukebox_id: int, user_id: int
) -> None:
    r = await client.patch(
        f"/api/v1/jukeboxes/{jukebox_id}/members/{user_id}",
        headers=auth(owner_token),
        json={"role": "GUEST"},
    )
    assert r.status_code == 200


async def _member_user_id(
    client: AsyncClient, owner_token: str, jukebox_id: int, member_token: str
) -> int:
    me = await client.get("/api/v1/users/me", headers=auth(member_token))
    return me.json()["id"]


# ---------- permisos ----------


async def test_vote_requires_auth():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.post("/api/v1/jukeboxes/1/queue/1/vote")
    assert r.status_code == 401


async def test_guest_cannot_vote():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await add_item(c, owner_token, jukebox_id, "aaa")
        uid = await _member_user_id(c, owner_token, jukebox_id, member_token)
        await _demote_to_guest(c, owner_token, jukebox_id, uid)
        r = await c.post(f"/api/v1/jukeboxes/{jukebox_id}/queue/1/vote", headers=auth(member_token))
    assert r.status_code == 403
    assert r.json()["code"] == "insufficient_role"


async def test_vote_non_member_404():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await add_item(c, owner_token, jukebox_id, "aaa")
        stranger_token = await register_user(c, "vstranger@test.com")
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/1/vote", headers=auth(stranger_token)
        )
    assert r.status_code == 404
    assert r.json()["code"] == "not_member"


async def test_vote_invalid_item_404():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/999999/vote", headers=auth(owner_token)
        )
    assert r.status_code == 404
    assert r.json()["code"] == "queue_item_not_found"


# ---------- votar ----------


async def test_cast_vote_updates_queue():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await add_item(c, owner_token, jukebox_id, "aaa")
        item = (await add_item(c, owner_token, jukebox_id, "bbb")).json()
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
        q = await _queue(c, member_token, jukebox_id)
    assert r.status_code == 204
    voted = next(i for i in q["items"] if i["id"] == item["id"])
    assert voted["score"] == 1
    assert voted["voted_by_me"] is True
    other = next(i for i in q["items"] if i["id"] != item["id"])
    assert other["score"] == 0
    assert other["voted_by_me"] is False
    assert [i["track_id"] for i in q["items"]] == ["bbb", "aaa"]


async def test_one_vote_moves_between_items():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item_a = (await add_item(c, owner_token, jukebox_id, "aaa")).json()
        item_b = (await add_item(c, owner_token, jukebox_id, "bbb")).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item_a['id']}/vote",
            headers=auth(member_token),
        )
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item_b['id']}/vote",
            headers=auth(member_token),
        )
        q = await _queue(c, member_token, jukebox_id)
    assert r.status_code == 204
    by_id = {i["id"]: i for i in q["items"]}
    assert by_id[item_a["id"]]["score"] == 0
    assert by_id[item_a["id"]]["voted_by_me"] is False
    assert by_id[item_b["id"]]["score"] == 1
    assert by_id[item_b["id"]]["voted_by_me"] is True


async def test_vote_same_item_idempotent():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id, "aaa")).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
        q = await _queue(c, member_token, jukebox_id)
    by_id = {i["id"]: i for i in q["items"]}
    assert by_id[item["id"]]["score"] == 1


async def test_queue_reordered_by_score():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item_c = (await add_item(c, owner_token, jukebox_id, "ccc")).json()
        await add_item(c, owner_token, jukebox_id, "aaa")
        await add_item(c, owner_token, jukebox_id, "bbb")
        # el miembro vota al último; debe pasar al frente
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item_c['id']}/vote",
            headers=auth(member_token),
        )
        q = await _queue(c, owner_token, jukebox_id)
    assert [i["track_id"] for i in q["items"]] == ["ccc", "aaa", "bbb"]
    assert [i["position"] for i in q["items"]] == [0, 1, 2]


async def test_two_votes_tie_keeps_add_order():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item_a = (await add_item(c, owner_token, jukebox_id, "aaa")).json()
        await add_item(c, owner_token, jukebox_id, "bbb")
        await add_item(c, owner_token, jukebox_id, "ccc")
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item_a['id']}/vote",
            headers=auth(member_token),
        )
        q = await _queue(c, owner_token, jukebox_id)
    assert [i["track_id"] for i in q["items"]] == ["aaa", "bbb", "ccc"]


async def test_remove_vote():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await add_item(c, owner_token, jukebox_id, "aaa")
        item = (await add_item(c, owner_token, jukebox_id, "bbb")).json()
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
        r = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
        q = await _queue(c, member_token, jukebox_id)
    assert r.status_code == 204
    by_id = {i["id"]: i for i in q["items"]}
    assert by_id[item["id"]]["score"] == 0
    assert by_id[item["id"]]["voted_by_me"] is False
    assert [i["track_id"] for i in q["items"]] == ["bbb", "aaa"]


async def test_remove_vote_idempotent():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id, "aaa")).json()
        first = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
        second = await c.delete(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
    assert first.status_code == 204
    assert second.status_code == 204


# ---------- ítems no votables ----------


async def test_cannot_vote_playing_item():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id, "aaa")).json()
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(owner_token),
        )
    assert r.status_code == 409
    assert r.json()["code"] == "item_not_votable"


async def test_cannot_vote_played_item():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id, "aaa")).json()
        await add_item(c, owner_token, jukebox_id, "bbb")
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/next", headers=auth(owner_token))
        r = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(member_token),
        )
    assert r.status_code == 409
    assert r.json()["code"] == "item_not_votable"
