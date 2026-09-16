from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.payment import CheckoutOut, CheckoutRequest, PaymentOut
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.user import User
from app.providers.payments import PaymentProvider, get_payment_provider
from app.services import payment_service

router = APIRouter(tags=["payments"])


@router.post("/payments/webhook")
async def payments_webhook(
    request: Request,
    provider: PaymentProvider = Depends(get_payment_provider),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Endpoint público: el proveedor notifica el resultado de un pago."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    return await payment_service.consume_webhook(db, provider, payload, signature)


@router.post("/users/me/payments/checkout", response_model=CheckoutOut, status_code=201)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    provider: PaymentProvider = Depends(get_payment_provider),
    db: AsyncSession = Depends(get_db),
) -> CheckoutOut:
    return await payment_service.create_checkout(db, current_user, provider, payload)


@router.get("/users/me/payments", response_model=list[PaymentOut])
async def my_payments(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentOut]:
    return await payment_service.list_payments(db, current_user, limit=limit, offset=offset)
