from httpx import AsyncClient

from tests.helpers import BASE, add_item, auth, make_jukebox_x2, transport


async def _queue(client: AsyncClient, token: str, jukebox_id: int) -> dict:
    return (await client.get(f"/api/v1/jukeboxes/{jukebox_id}/queue", headers=auth(token))).json()


async def _boost(client: AsyncClient, token: str, jukebox_id: int, item_id: int, credits: int):
    return await client.post(
        f"/api/v1/jukeboxes/{jukebox_id}/queue/{item_id}/boost",
        headers=auth(token),
        json={"credits": credits},
    )


async def test_boost_requires_auth():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.post("/api/v1/jukeboxes/1/queue/1/boost", json={"credits": 1})
    assert r.status_code == 401


async def test_boost_moves_item_ahead_in_queue():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        first = (await add_item(c, owner_token, jukebox_id, "first")).json()
        second = (await add_item(c, owner_token, jukebox_id, "second")).json()
        # owner ganó 1 crédito por cada canción añadida (add_track).
        r = await _boost(c, owner_token, jukebox_id, second["id"], 1)
        queue = await _queue(c, owner_token, jukebox_id)
    assert r.status_code == 200
    assert r.json()["boost"] == 1
    ordered_ids = [i["id"] for i in queue["items"]]
    assert ordered_ids == [second["id"], first["id"]]
    assert queue["items"][0]["boost"] == 1


async def test_boost_insufficient_balance_409():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id, "only")).json()
        r = await _boost(c, owner_token, jukebox_id, item["id"], 999)
    assert r.status_code == 409
    assert r.json()["code"] == "insufficient_balance"


async def test_boost_only_queued_items_409():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id, "playing")).json()
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        r = await _boost(c, owner_token, jukebox_id, item["id"], 1)
    assert r.status_code == 409
    assert r.json()["code"] == "item_not_boostable"


async def test_boost_item_not_found_404():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await _boost(c, owner_token, jukebox_id, 999999, 1)
    assert r.status_code == 404
    assert r.json()["code"] == "queue_item_not_found"


async def test_guest_cannot_boost():
    owner_token, member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id, "abc")).json()
        me = (await c.get("/api/v1/users/me", headers=auth(member_token))).json()
        await c.patch(
            f"/api/v1/jukeboxes/{jukebox_id}/members/{me['id']}",
            headers=auth(owner_token),
            json={"role": "GUEST"},
        )
        r = await _boost(c, member_token, jukebox_id, item["id"], 1)
    assert r.status_code == 403
    assert r.json()["code"] == "insufficient_role"


async def test_boost_recorded_in_wallet_ledger():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id, "abc")).json()
        before = (await c.get("/api/v1/users/me/wallet", headers=auth(owner_token))).json()
        await _boost(c, owner_token, jukebox_id, item["id"], 1)
        after = (await c.get("/api/v1/users/me/wallet", headers=auth(owner_token))).json()
    assert after["credits"] == before["credits"] - 1
    assert after["transactions"][0]["kind"] == "boost"
    assert after["transactions"][0]["amount"] == -1
