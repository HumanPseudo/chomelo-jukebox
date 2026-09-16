from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.domain.wallet import WalletTransaction
from app.services import wallet_service
from tests.helpers import (
    BASE,
    add_item,
    auth,
    make_jukebox_x2,
    register_user,
    transport,
)


async def _wallet(client: AsyncClient, token: str) -> dict:
    r = await client.get("/api/v1/users/me/wallet", headers=auth(token))
    assert r.status_code == 200, r.text
    return r.json()


async def _count_ledger_rows(db_session, user_id: int) -> int:
    wallet = await wallet_service.get_wallet(db_session, user_id)
    if wallet is None:
        return 0
    return int(
        (
            await db_session.execute(
                select(func.count())
                .select_from(WalletTransaction)
                .where(WalletTransaction.wallet_id == wallet.id)
            )
        ).scalar_one()
    )


async def test_wallet_endpoints_require_auth():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        assert (await c.get("/api/v1/users/me/wallet")).status_code == 401
        assert (await c.get("/api/v1/users/me/wallet/transactions")).status_code == 401


async def test_wallet_created_on_demand_empty():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "w0@test.com")
        w = await _wallet(c, token)
    assert w["credits"] == 0
    assert w["transactions"] == []


async def test_credit_is_idempotent(db_session):
    await wallet_service.credit(
        db_session,
        user_id=1,
        amount=5,
        idempotency_key="k1",
        kind="test",
        description="x",
    )
    await db_session.commit()
    await wallet_service.credit(
        db_session,
        user_id=1,
        amount=5,
        idempotency_key="k1",
        kind="test",
        description="x",
    )
    await db_session.commit()
    assert await wallet_service.balance(db_session, 1) == 5
    assert await _count_ledger_rows(db_session, 1) == 1


async def test_credit_rejects_non_positive(db_session):
    for amount in (0, -3):
        try:
            await wallet_service.credit(
                db_session,
                user_id=1,
                amount=amount,
                idempotency_key=f"bad-{amount}",
                kind="test",
            )
            raise AssertionError("debería fallar")
        except AppError as e:
            assert e.code == "invalid_amount"


async def test_debit_success_and_insufficient(db_session):
    await wallet_service.credit(db_session, 1, 10, idempotency_key="c1", kind="test")
    await db_session.commit()
    assert await wallet_service.debit(db_session, 1, 4, idempotency_key="d1", kind="test") == 6
    await db_session.commit()
    row = (
        await db_session.execute(
            select(WalletTransaction).where(WalletTransaction.idempotency_key == "d1")
        )
    ).scalar_one()
    assert row.amount == -4
    assert row.kind == "test"

    try:
        await wallet_service.debit(db_session, 1, 100, idempotency_key="d2", kind="test")
        raise AssertionError("debería fallar por saldo")
    except AppError as e:
        assert e.code == "insufficient_balance"
    await db_session.commit()
    assert await wallet_service.balance(db_session, 1) == 6


async def test_debit_is_idempotent(db_session):
    await wallet_service.credit(db_session, 1, 5, idempotency_key="c1", kind="test")
    await db_session.commit()
    assert await wallet_service.debit(db_session, 1, 5, idempotency_key="d1", kind="test") == 0
    await db_session.commit()
    # reintento con el mismo key: no vuelve a cobrar ni a fallar
    assert await wallet_service.debit(db_session, 1, 5, idempotency_key="d1", kind="test") == 0
    await db_session.commit()
    assert await wallet_service.balance(db_session, 1) == 0
    assert await _count_ledger_rows(db_session, 1) == 2


async def test_add_track_grants_credit():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await add_item(c, owner_token, jukebox_id)
        assert r.status_code == 201, r.text
        w = await _wallet(c, owner_token)
    assert w["credits"] == 1
    assert w["transactions"][0]["kind"] == "add_track"
    assert w["transactions"][0]["amount"] == 1


async def test_played_track_grants_credit_to_adder():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        await add_item(c, owner_token, jukebox_id)
        r = await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        assert r.status_code == 204, r.text
        w = await _wallet(c, owner_token)
    assert w["credits"] == 2
    assert {t["kind"] for t in w["transactions"]} == {"add_track", "track_played"}


async def test_vote_grants_credit():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        item = (await add_item(c, owner_token, jukebox_id)).json()
        v = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/queue/{item['id']}/vote",
            headers=auth(owner_token),
        )
        assert v.status_code == 204, v.text
        w = await _wallet(c, owner_token)
    assert w["credits"] == 2  # 1 add + 1 vote
    assert w["transactions"][0]["kind"] == "vote"


async def test_poll_rewards():
    owner_token, _member, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        p = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls",
            headers=auth(owner_token),
            json={"question": "¿Sí?", "options": ["A", "B"]},
        )
        assert p.status_code == 201, p.text
        option_id = p.json()["options"][0]["id"]
        await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/polls/{p.json()['id']}/vote",
            headers=auth(owner_token),
            json={"option_id": option_id},
        )
        w = await _wallet(c, owner_token)
    kinds = {t["kind"] for t in w["transactions"]}
    assert kinds == {"poll_created", "poll_vote"}
    assert w["credits"] == 3  # 2 crear + 1 votar


async def test_game_winner_reward_equals_points():
    owner_token, _member_token, jukebox_id, _code = await make_jukebox_x2()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        for i in range(4):
            await add_item(c, owner_token, jukebox_id, f"s{i:03d}")
        await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/play", headers=auth(owner_token))
        for _ in range(4):
            await c.post(f"/api/v1/jukeboxes/{jukebox_id}/player/next", headers=auth(owner_token))
        rr = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/games/guess_the_song/rounds",
            headers=auth(owner_token),
            json={},
        )
        round_ = rr.json()
        answer = f"Titulo {round_['track_id']}"
        a = await c.post(
            f"/api/v1/jukeboxes/{jukebox_id}/games/guess_the_song/rounds/{round_['id']}/answer",
            headers=auth(owner_token),
            json={"title": answer},
        )
        assert a.status_code == 200, a.text
        assert a.json()["correct"] is True
        w = await _wallet(c, owner_token)
    winning = next(t for t in w["transactions"] if t["kind"] == "game_win")
    assert winning["amount"] == a.json()["points"]
