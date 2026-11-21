from httpx import AsyncClient
from sqlalchemy import func, select

from app.domain.audit import AuditLog
from app.domain.jukebox import Jukebox, JukeboxMember, Role
from app.domain.wallet import WalletTransaction
from tests.helpers import BASE, auth, transport


async def _register(client: AsyncClient, phone: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"phone_number": phone, "password": "secure123"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


async def _user_id(client: AsyncClient, token: str) -> int:
    r = await client.get("/api/v1/users/me", headers=auth(token))
    assert r.status_code == 200, r.text
    return int(r.json()["id"])


async def _setup(db_session) -> tuple[str, str, int, int, int]:
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        owner_token = await _register(c, "+12025550101")
        member_token = await _register(c, "+12025550102")
        owner_id = await _user_id(c, owner_token)
        member_id = await _user_id(c, member_token)

    jb = Jukebox(name="Recompensas", owner_id=owner_id, invite_code="RWARDS1")
    db_session.add(jb)
    await db_session.flush()
    db_session.add_all(
        [
            JukeboxMember(jukebox_id=jb.id, user_id=owner_id, role=Role.ADMIN.value),
            JukeboxMember(jukebox_id=jb.id, user_id=member_id, role=Role.MEMBER.value),
        ]
    )
    await db_session.commit()
    return owner_token, member_token, int(jb.id), owner_id, member_id


def _body(amount: int, key: str, reason: str = "bono de prueba") -> dict:
    return {"amount": amount, "reason": reason, "idempotency_key": key}


async def _adjust(client: AsyncClient, token: str, jbid: int, user_id: int, body: dict):
    return await client.post(
        f"/api/v1/jukeboxes/{jbid}/members/{user_id}/credits",
        headers=auth(token),
        json=body,
    )


async def _wallet(client: AsyncClient, token: str, jbid: int, user_id: int) -> dict:
    r = await client.get(f"/api/v1/jukeboxes/{jbid}/members/{user_id}/wallet", headers=auth(token))
    assert r.status_code == 200, r.text
    return r.json()


async def test_admin_can_read_member_wallet(db_session):
    owner_token, _member_token, jbid, _owner_id, member_id = await _setup(db_session)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await _adjust(c, owner_token, jbid, member_id, _body(8, "viewkey01"))
        assert r.status_code == 200, r.text
        w = await _wallet(c, owner_token, jbid, member_id)
    assert w["credits"] == 8
    assert w["transactions"][0]["description"] == "bono de prueba"


async def test_admin_adjust_grant_and_debit(db_session):
    owner_token, _member_token, jbid, owner_id, member_id = await _setup(db_session)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        granted = await _adjust(c, owner_token, jbid, member_id, _body(25, "grantkey01"))
        assert granted.status_code == 200, granted.text
        assert granted.json()["credits"] == 25

        removed = await _adjust(c, owner_token, jbid, member_id, _body(-10, "removkey01"))
        assert removed.status_code == 200, removed.text
        assert removed.json()["credits"] == 15

        failed = await _adjust(c, owner_token, jbid, member_id, _body(-100, "toomuch01"))
        assert failed.status_code == 409
        assert failed.json()["code"] == "insufficient_balance"

        assert (await _wallet(c, owner_token, jbid, member_id))["credits"] == 15

    txs = (
        (
            await db_session.execute(
                select(WalletTransaction)
                .where(WalletTransaction.kind == "admin_adjust")
                .order_by(WalletTransaction.id)
            )
        )
        .scalars()
        .all()
    )
    assert [tx.amount for tx in txs] == [25, -10]

    audits = (
        (await db_session.execute(select(AuditLog).where(AuditLog.action == "wallet.admin_adjust")))
        .scalars()
        .all()
    )
    assert len(audits) == 2
    assert audits[0].detail["amount"] == 25
    assert audits[0].user_id == owner_id


async def test_admin_adjust_is_idempotent(db_session):
    owner_token, _member_token, jbid, _owner_id, member_id = await _setup(db_session)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        body = _body(5, "idemkey001")
        first = await _adjust(c, owner_token, jbid, member_id, body)
        retry = await _adjust(c, owner_token, jbid, member_id, body)
        assert first.status_code == retry.status_code == 200
        assert first.json() == retry.json() == {"credits": 5}

    txs = (
        await db_session.execute(
            select(func.count())
            .select_from(WalletTransaction)
            .where(WalletTransaction.kind == "admin_adjust")
        )
    ).scalar_one()
    audits = (
        await db_session.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "wallet.admin_adjust")
        )
    ).scalar_one()
    assert txs == 1
    assert audits == 1


async def test_adjust_and_wallet_require_admin_role(db_session):
    _owner_token, member_token, jbid, _owner_id, member_id = await _setup(db_session)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await _adjust(c, member_token, jbid, member_id, _body(5, "denied001"))
        assert r.status_code == 403
        assert r.json()["code"] == "insufficient_role"
        w = await c.get(
            f"/api/v1/jukeboxes/{jbid}/members/{member_id}/wallet", headers=auth(member_token)
        )
        assert w.status_code == 403
        assert w.json()["code"] == "insufficient_role"


async def test_adjust_target_must_be_member(db_session):
    owner_token, _member_token, jbid, _owner_id, _member_id = await _setup(db_session)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await _adjust(c, owner_token, jbid, 999999, _body(5, "nomember01"))
        assert r.status_code == 404
        assert r.json()["code"] == "member_not_found"
        w = await c.get(
            f"/api/v1/jukeboxes/{jbid}/members/999999/wallet", headers=auth(owner_token)
        )
        assert w.status_code == 404


async def test_adjust_rejects_invalid_payload(db_session):
    owner_token, _member_token, jbid, _owner_id, member_id = await _setup(db_session)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        for body in (
            _body(0, "zerovalue1"),
            _body(10001, "toobig001"),
            _body(5, "short"),
            {"amount": 5, "reason": "x", "idempotency_key": "shortreasonkey"},
        ):
            r = await _adjust(c, owner_token, jbid, member_id, body)
            assert r.status_code == 422, r.text
