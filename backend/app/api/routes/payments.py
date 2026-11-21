from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.api.schemas.payment import (
    CheckoutOut,
    CheckoutRequest,
    PaymentOut,
    PricingOut,
    PricingUpdate,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role
from app.domain.user import User
from app.providers.payments import PaymentProvider, get_payment_provider
from app.services import audit_service, payment_service

router = APIRouter(tags=["payments"])


@router.get("/payments/pricing", response_model=PricingOut)
async def payment_pricing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PricingOut:
    return await payment_service.get_pricing(db)


@router.patch("/jukeboxes/{jukebox_id}/payments/pricing", response_model=PricingOut)
async def update_payment_pricing(
    jukebox_id: int,
    payload: PricingUpdate,
    request: Request,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PricingOut:
    pricing = await payment_service.update_pricing(db, member.user_id, payload)
    await audit_service.log_action(
        db,
        action="payment.pricing.update",
        user_id=member.user_id,
        detail={
            "jukebox_id": jukebox_id,
            "cents_per_credit": pricing.cents_per_credit,
            "currency": pricing.currency,
            "credit_amounts": pricing.credit_amounts,
        },
        request=request,
    )
    await db.commit()
    return pricing


@router.post("/payments/webhook")
async def payments_webhook(
    request: Request,
    provider: PaymentProvider = Depends(get_payment_provider),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Endpoint público: el proveedor notifica el resultado de un pago."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    result = await payment_service.consume_webhook(db, provider, payload, signature)
    await audit_service.log_action(
        db,
        action="payment.webhook",
        detail={"duplicate": bool(result.get("duplicate"))},
        request=request,
    )
    await db.commit()
    return result


@router.post("/users/me/payments/checkout", response_model=CheckoutOut, status_code=201)
async def create_checkout(
    payload: CheckoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    provider: PaymentProvider = Depends(get_payment_provider),
    db: AsyncSession = Depends(get_db),
) -> CheckoutOut:
    checkout = await payment_service.create_checkout(db, current_user, provider, payload)
    await audit_service.log_action(
        db,
        action="payment.checkout",
        user_id=current_user.id,
        resource_type="payment",
        resource_id=checkout.payment.id,
        detail={
            "credits": payload.credits,
            "currency": checkout.payment.currency,
            "amount_cents": checkout.payment.amount_cents,
        },
        request=request,
    )
    await db.commit()
    return checkout


@router.get("/users/me/payments", response_model=list[PaymentOut])
async def my_payments(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentOut]:
    return await payment_service.list_payments(db, current_user, limit=limit, offset=offset)
