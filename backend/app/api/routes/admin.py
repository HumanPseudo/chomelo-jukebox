from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.audit import AuditOut
from app.api.schemas.payment import ConfirmOut, ConfirmPaymentRequest
from app.core.exceptions import AppError
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.user import User
from app.providers.payments import PaymentProvider, get_payment_provider
from app.services import audit_service, payment_service

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise AppError("permiso de administrador requerido", code="admin_required", status_code=403)
    return current_user


@router.get("/audit", response_model=list[AuditOut])
async def audit_log(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None),
    _: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
) -> list[AuditOut]:
    return await audit_service.list_audit(db, limit=limit, offset=offset, action=action)


@router.post("/payments/confirm", response_model=ConfirmOut)
async def confirm_payment_as_admin(
    payload: ConfirmPaymentRequest,
    request: Request,
    _: User = Depends(require_superuser),
    provider: PaymentProvider = Depends(get_payment_provider),
    db: AsyncSession = Depends(get_db),
) -> ConfirmOut:
    confirmation = await payment_service.confirm_payment_as_admin(db, provider, payload)
    await audit_service.log_action(
        db,
        action="payment.admin_confirm",
        detail={"status": confirmation.status},
        request=request,
    )
    await db.commit()
    return confirmation
