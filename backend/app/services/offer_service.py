from datetime import UTC, datetime
from secrets import token_hex

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.offer import (
    OfferCreate,
    OfferOut,
    OfferUpdate,
    RedemptionOut,
    RedemptionUpdate,
)
from app.core.exceptions import AppError
from app.domain.jukebox import JukeboxMember, Role
from app.domain.offer import (
    Offer,
    OfferRedemption,
    OfferStatus,
    RedemptionStatus,
)
from app.infra.events import notify_jukebox
from app.services import wallet_service


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _offer_out(offer: Offer, redemption: OfferRedemption | None = None) -> OfferOut:
    return OfferOut(
        id=offer.id,
        jukebox_id=offer.jukebox_id,
        merchant=offer.merchant,
        title=offer.title,
        description=offer.description,
        terms=offer.terms,
        image_url=offer.image_url,
        cost_credits=offer.cost_credits,
        stock_total=offer.stock_total,
        stock_remaining=offer.stock_remaining,
        status=offer.status,
        starts_at=offer.starts_at,
        ends_at=offer.ends_at,
        my_redemption_status=redemption.status if redemption else None,
        my_code=redemption.code if redemption and _reveal_code(redemption) else None,
    )


def _reveal_code(redemption: OfferRedemption) -> bool:
    return redemption.status in {RedemptionStatus.APPROVED.value, RedemptionStatus.REDEEMED.value}


def _redemption_out(
    redemption: OfferRedemption, offer_title: str, *, reveal_code: bool
) -> RedemptionOut:
    return RedemptionOut(
        id=redemption.id,
        jukebox_id=redemption.jukebox_id,
        offer_id=redemption.offer_id,
        offer_title=offer_title,
        user_id=redemption.user_id,
        code=redemption.code if reveal_code else None,
        credits_spent=redemption.credits_spent,
        status=redemption.status,
        notes=redemption.notes,
        created_at=redemption.created_at,
        approved_at=redemption.approved_at,
        redeemed_at=redemption.redeemed_at,
    )


async def _get_offer(db: AsyncSession, jukebox_id: int, offer_id: int) -> Offer:
    offer = (
        await db.execute(
            select(Offer).where(Offer.id == offer_id, Offer.jukebox_id == jukebox_id)
        )
    ).scalar_one_or_none()
    if offer is None:
        raise AppError("oferta no encontrada", code="offer_not_found", status_code=404)
    return offer


async def list_offers(db: AsyncSession, member: JukeboxMember) -> list[OfferOut]:
    offers = (
        await db.execute(
            select(Offer).where(Offer.jukebox_id == member.jukebox_id).order_by(Offer.id.desc())
        )
    ).scalars().all()
    mine = {
        row.offer_id: row
        for row in (
            await db.execute(
                select(OfferRedemption).where(
                    OfferRedemption.jukebox_id == member.jukebox_id,
                    OfferRedemption.user_id == member.user_id,
                )
            )
        ).scalars().all()
    }
    return [_offer_out(offer, mine.get(offer.id)) for offer in offers]


async def create_offer(db: AsyncSession, member: JukeboxMember, payload: OfferCreate) -> OfferOut:
    offer = Offer(
        jukebox_id=member.jukebox_id,
        created_by=member.user_id,
        merchant=payload.merchant,
        title=payload.title,
        description=payload.description,
        terms=payload.terms,
        image_url=payload.image_url,
        cost_credits=payload.cost_credits,
        stock_total=payload.stock_total,
        stock_remaining=payload.stock_total,
        status=OfferStatus.ACTIVE.value,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    await notify_jukebox(member.jukebox_id, "offer.updated", offer_id=offer.id)
    return _offer_out(offer)


async def update_offer(
    db: AsyncSession, member: JukeboxMember, offer_id: int, payload: OfferUpdate
) -> OfferOut:
    offer = (
        await db.execute(
            select(Offer)
            .where(Offer.id == offer_id, Offer.jukebox_id == member.jukebox_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if offer is None:
        raise AppError("oferta no encontrada", code="offer_not_found", status_code=404)

    data = payload.model_dump(exclude_unset=True)
    if "stock_total" in data:
        delta = data["stock_total"] - offer.stock_total
        offer.stock_total = data["stock_total"]
        offer.stock_remaining = max(0, offer.stock_remaining + delta)
    fields = (
        "merchant",
        "title",
        "description",
        "terms",
        "image_url",
        "cost_credits",
        "status",
        "starts_at",
        "ends_at",
    )
    for field in fields:
        if field in data:
            setattr(offer, field, data[field])
    if offer.stock_remaining == 0 and offer.status == OfferStatus.ACTIVE.value:
        offer.status = OfferStatus.EXHAUSTED.value
    elif offer.stock_remaining > 0 and offer.status == OfferStatus.EXHAUSTED.value:
        offer.status = OfferStatus.ACTIVE.value

    await db.commit()
    await db.refresh(offer)
    await notify_jukebox(member.jukebox_id, "offer.updated", offer_id=offer.id)
    return _offer_out(offer)


async def claim_offer(db: AsyncSession, member: JukeboxMember, offer_id: int) -> OfferOut:
    offer = (
        await db.execute(
            select(Offer)
            .where(Offer.id == offer_id, Offer.jukebox_id == member.jukebox_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if offer is None:
        raise AppError("oferta no encontrada", code="offer_not_found", status_code=404)

    existing = (
        await db.execute(
            select(OfferRedemption).where(
                OfferRedemption.offer_id == offer.id,
                OfferRedemption.user_id == member.user_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError("ya canjeaste esta oferta", code="already_claimed", status_code=409)

    now = datetime.now(UTC)
    starts_at = _aware(offer.starts_at)
    ends_at = _aware(offer.ends_at)
    if offer.status != OfferStatus.ACTIVE.value:
        raise AppError("oferta no disponible", code="offer_unavailable", status_code=409)
    if starts_at and now < starts_at:
        raise AppError("oferta no disponible", code="offer_unavailable", status_code=409)
    if ends_at and now > ends_at:
        raise AppError("oferta no disponible", code="offer_unavailable", status_code=409)
    if offer.stock_remaining <= 0:
        raise AppError("no queda stock", code="offer_out_of_stock", status_code=409)

    idempotency_key = f"offer_claim:{offer.id}:{member.user_id}"
    await wallet_service.debit(
        db,
        member.user_id,
        offer.cost_credits,
        idempotency_key=idempotency_key,
        kind="offer_claim",
        description=f"Canje de «{offer.title}»",
    )
    redemption = OfferRedemption(
        jukebox_id=offer.jukebox_id,
        offer_id=offer.id,
        user_id=member.user_id,
        code=token_hex(4).upper(),
        idempotency_key=idempotency_key,
        credits_spent=offer.cost_credits,
        status=RedemptionStatus.PENDING.value,
    )
    db.add(redemption)
    offer.stock_remaining -= 1
    if offer.stock_remaining == 0:
        offer.status = OfferStatus.EXHAUSTED.value
    await db.commit()
    await db.refresh(redemption)
    await notify_jukebox(offer.jukebox_id, "offer.updated", offer_id=offer.id)
    await notify_jukebox(offer.jukebox_id, "redemption.updated", redemption_id=redemption.id)
    return _offer_out(offer, redemption)


async def list_redemptions(db: AsyncSession, member: JukeboxMember) -> list[RedemptionOut]:
    if Role(member.role) is not Role.ADMIN:
        raise AppError("permiso insuficiente", code="insufficient_role", status_code=403)
    rows = (
        await db.execute(
            select(OfferRedemption, Offer.title)
            .join(Offer, Offer.id == OfferRedemption.offer_id)
            .where(OfferRedemption.jukebox_id == member.jukebox_id)
            .order_by(OfferRedemption.id.desc())
        )
    ).all()
    return [_redemption_out(row, title, reveal_code=True) for row, title in rows]


async def my_redemptions(db: AsyncSession, user_id: int) -> list[RedemptionOut]:
    rows = (
        await db.execute(
            select(OfferRedemption, Offer.title)
            .join(Offer, Offer.id == OfferRedemption.offer_id)
            .where(OfferRedemption.user_id == user_id)
            .order_by(OfferRedemption.id.desc())
        )
    ).all()
    return [
        _redemption_out(row, title, reveal_code=_reveal_code(row)) for row, title in rows
    ]


async def update_redemption(
    db: AsyncSession, member: JukeboxMember, redemption_id: int, payload: RedemptionUpdate
) -> RedemptionOut:
    if Role(member.role) is not Role.ADMIN:
        raise AppError("permiso insuficiente", code="insufficient_role", status_code=403)
    result = (
        await db.execute(
            select(OfferRedemption, Offer)
            .join(Offer, Offer.id == OfferRedemption.offer_id)
            .where(
                OfferRedemption.id == redemption_id,
                OfferRedemption.jukebox_id == member.jukebox_id,
            )
            .with_for_update(of=OfferRedemption)
        )
    ).one_or_none()
    if result is None:
        raise AppError("canje no encontrado", code="redemption_not_found", status_code=404)
    redemption, offer = result
    current = RedemptionStatus(redemption.status)
    target = RedemptionStatus(payload.status)
    allowed = {
        RedemptionStatus.PENDING: {
            RedemptionStatus.APPROVED,
            RedemptionStatus.CANCELLED,
            RedemptionStatus.EXPIRED,
        },
        RedemptionStatus.APPROVED: {
            RedemptionStatus.REDEEMED,
            RedemptionStatus.CANCELLED,
            RedemptionStatus.EXPIRED,
        },
    }
    if target not in allowed.get(current, set()):
        raise AppError(
            "transición de canje inválida", code="invalid_redemption_status", status_code=409
        )

    now = datetime.now(UTC)
    redemption.status = target.value
    redemption.notes = payload.notes
    if target is RedemptionStatus.APPROVED:
        redemption.approved_by = member.user_id
        redemption.approved_at = now
    if target is RedemptionStatus.REDEEMED:
        redemption.redeemed_at = now
    if target is RedemptionStatus.CANCELLED:
        offer.stock_remaining += 1
        if offer.status == OfferStatus.EXHAUSTED.value:
            offer.status = OfferStatus.ACTIVE.value
        await wallet_service.credit(
            db,
            redemption.user_id,
            redemption.credits_spent,
            idempotency_key=f"offer_refund:{redemption.id}",
            kind="offer_refund",
            description=f"Reembolso de «{offer.title}»",
        )

    await db.commit()
    await db.refresh(redemption)
    await notify_jukebox(member.jukebox_id, "offer.updated", offer_id=offer.id)
    await notify_jukebox(member.jukebox_id, "redemption.updated", redemption_id=redemption.id)
    return _redemption_out(redemption, offer.title, reveal_code=True)
