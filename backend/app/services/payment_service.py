from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.payment import CheckoutOut, CheckoutRequest, PaymentOut
from app.core.config import settings
from app.core.exceptions import AppError
from app.domain.payment import Payment, PaymentEvent, PaymentStatus
from app.domain.user import User
from app.infra.db_utils import dialect_insert
from app.providers.payments import PaymentProvider, PaymentProviderError
from app.services import wallet_service

MIN_CREDITS = 5
MAX_CREDITS = 10000


def _price_cents(credits: int) -> int:
    return credits * settings.cents_per_credit


def _to_out(payment: Payment) -> PaymentOut:
    return PaymentOut(
        id=payment.id,
        provider=payment.provider,
        credits=payment.credits,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        status=payment.status,
        created_at=payment.created_at,
    )


async def _get_payment(db: AsyncSession, user: User, payment_id: int) -> Payment:
    payment = await db.get(Payment, payment_id)
    if payment is None or payment.user_id != user.id:
        raise AppError("pago no encontrado", code="payment_not_found", status_code=404)
    return payment


async def create_checkout(
    db: AsyncSession, user: User, provider: PaymentProvider, payload: CheckoutRequest
) -> CheckoutOut:
    credits = payload.credits
    if credits < MIN_CREDITS or credits > MAX_CREDITS:
        raise AppError(
            f"los créditos deben estar entre {MIN_CREDITS} y {MAX_CREDITS}",
            code="invalid_amount",
            status_code=422,
        )
    amount_cents = _price_cents(credits)
    try:
        result = await provider.create_checkout(
            amount_cents=amount_cents,
            currency=payload.currency,
            credits=credits,
            metadata={"user_id": str(user.id), "credits": str(credits)},
            success_url="{{FRONTEND_URL}}/wallet?status=success",
            cancel_url="{{FRONTEND_URL}}/wallet?status=cancelled",
        )
    except PaymentProviderError:
        raise AppError(
            "no se pudo crear el pago, inténtalo más tarde",
            code="checkout_failed",
            status_code=502,
        ) from None
    payment = Payment(
        user_id=user.id,
        provider=provider.key,
        provider_session_id=result.session_id,
        credits=credits,
        amount_cents=amount_cents,
        currency=payload.currency,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return CheckoutOut(payment=_to_out(payment), checkout_url=result.checkout_url)


async def consume_webhook(
    db: AsyncSession, provider: PaymentProvider, payload: bytes, signature: str
) -> dict:
    try:
        event = await provider.verify_event(payload, signature)
    except PaymentProviderError:
        raise AppError(
            "firma de webhook inválida", code="invalid_signature", status_code=400
        ) from None

    payment = (
        (
            await db.execute(
                select(Payment).where(Payment.provider_session_id == event.checkout_session_id)
            )
        ).scalar_one_or_none()
        if event.checkout_session_id
        else None
    )

    # ON CONFLICT DO NOTHING: dos entregas concurrentes del mismo evento
    # (reintento del proveedor) no deben procesarse dos veces (regla dura #3).
    result = await db.execute(
        dialect_insert(db, PaymentEvent)
        .values(
            provider_event_id=event.event_id,
            payment_id=payment.id if payment else None,
            event_type=event.event_type,
            payload=event.raw,
        )
        .on_conflict_do_nothing(index_elements=["provider_event_id"])
    )
    if result.rowcount == 0:
        await db.commit()
        return {"received": True, "duplicate": True}

    if (
        event.is_completed_checkout
        and payment
        and payment.status != PaymentStatus.CREDITS_GRANTED.value
    ):
        payment.status = PaymentStatus.PROCESSED.value
        await wallet_service.credit(
            db,
            payment.user_id,
            payment.credits,
            idempotency_key=f"payment:{payment.provider}:{payment.provider_session_id}",
            kind="payment",
            description=f"Compra de {payment.credits} créditos",
        )
        payment.status = PaymentStatus.CREDITS_GRANTED.value

    await db.commit()
    return {"received": True}


async def list_payments(db: AsyncSession, user: User, limit: int, offset: int) -> list[PaymentOut]:
    stmt = (
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_to_out(p) for p in (await db.execute(stmt)).scalars()]
