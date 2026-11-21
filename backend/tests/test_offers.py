import pytest
from sqlalchemy import select

from app.api.schemas.offer import OfferCreate, RedemptionUpdate
from app.core.exceptions import AppError
from app.domain.jukebox import Jukebox, JukeboxMember, Role
from app.domain.offer import OfferRedemption
from app.domain.user import User
from app.services import offer_service, wallet_service


async def _setup(db, *, credits: int = 500):
    owner = User(phone_number="+573000000001", password_hash="hash")
    member = User(phone_number="+573000000002", password_hash="hash")
    db.add_all([owner, member])
    await db.flush()
    jukebox = Jukebox(name="Ofertas", owner_id=owner.id, invite_code="OFERTA")
    db.add(jukebox)
    await db.flush()
    db.add_all(
        [
            JukeboxMember(jukebox_id=jukebox.id, user_id=owner.id, role=Role.ADMIN.value),
            JukeboxMember(jukebox_id=jukebox.id, user_id=member.id, role=Role.MEMBER.value),
        ]
    )
    await wallet_service.credit(
        db, member.id, credits, idempotency_key="setup_wallet", kind="bonus"
    )
    await db.commit()
    admin = (
        await db.execute(
            select(JukeboxMember).where(
                JukeboxMember.jukebox_id == jukebox.id,
                JukeboxMember.user_id == owner.id,
            )
        )
    ).scalar_one()
    listener = (
        await db.execute(
            select(JukeboxMember).where(
                JukeboxMember.jukebox_id == jukebox.id,
                JukeboxMember.user_id == member.id,
            )
        )
    ).scalar_one()
    return admin, listener, member


def _payload(**overrides) -> OfferCreate:
    data = {
        "merchant": "Café del Puerto",
        "title": "Café gratis",
        "description": "Un café en la esquina",
        "terms": "Mostrar código",
        "cost_credits": 100,
        "stock_total": 2,
    }
    data.update(overrides)
    return OfferCreate(**data)


@pytest.mark.asyncio
async def test_claim_hides_code_until_admin_approves(db_session):
    admin, listener, user = await _setup(db_session)
    offer = await offer_service.create_offer(db_session, admin, _payload())

    claimed = await offer_service.claim_offer(db_session, listener, offer.id)
    assert claimed.my_redemption_status == "PENDING"
    assert claimed.my_code is None
    assert claimed.stock_remaining == 1
    assert await wallet_service.balance(db_session, user.id) == 400

    mine = await offer_service.my_redemptions(db_session, user.id)
    assert mine[0].code is None

    pending = await offer_service.list_redemptions(db_session, admin)
    assert pending[0].code is not None
    approved = await offer_service.update_redemption(
        db_session, admin, pending[0].id, RedemptionUpdate(status="APPROVED")
    )
    assert approved.status == "APPROVED"

    mine = await offer_service.my_redemptions(db_session, user.id)
    assert mine[0].code == pending[0].code

    delivered = await offer_service.update_redemption(
        db_session, admin, pending[0].id, RedemptionUpdate(status="REDEEMED")
    )
    assert delivered.status == "REDEEMED"


@pytest.mark.asyncio
async def test_cancel_refunds_credits_and_restores_stock(db_session):
    admin, listener, user = await _setup(db_session)
    offer = await offer_service.create_offer(db_session, admin, _payload())
    await offer_service.claim_offer(db_session, listener, offer.id)
    assert await wallet_service.balance(db_session, user.id) == 400

    pending = (await offer_service.list_redemptions(db_session, admin))[0]
    cancelled = await offer_service.update_redemption(
        db_session, admin, pending.id, RedemptionUpdate(status="CANCELLED")
    )
    assert cancelled.status == "CANCELLED"
    assert await wallet_service.balance(db_session, user.id) == 500

    offers = await offer_service.list_offers(db_session, listener)
    assert offers[0].stock_remaining == 2
    assert offers[0].status == "ACTIVE"


@pytest.mark.asyncio
async def test_claim_requires_balance_and_is_single_per_offer(db_session):
    admin, listener, _user = await _setup(db_session, credits=50)
    offer = await offer_service.create_offer(db_session, admin, _payload())
    with pytest.raises(AppError) as exc:
        await offer_service.claim_offer(db_session, listener, offer.id)
    assert exc.value.code == "insufficient_balance"

    await wallet_service.credit(
        db_session,
        listener.user_id,
        100,
        idempotency_key="extra_wallet",
        kind="bonus",
    )
    await db_session.commit()
    await offer_service.claim_offer(db_session, listener, offer.id)
    with pytest.raises(AppError) as exc:
        await offer_service.claim_offer(db_session, listener, offer.id)
    assert exc.value.code == "already_claimed"
    assert (
        await db_session.execute(
            select(OfferRedemption).where(OfferRedemption.offer_id == offer.id)
        )
    ).scalar_one_or_none() is not None
