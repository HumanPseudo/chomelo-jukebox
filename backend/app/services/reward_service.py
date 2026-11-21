from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.wallet import WalletOut, WalletTransactionOut
from app.core.exceptions import AppError
from app.domain.jukebox import JukeboxMember
from app.services import wallet_service

MAX_ADJUSTMENT = 10000


def adjustment_key(jukebox_id: int, user_id: int, client_key: str) -> str:
    return f"admin_adjust:{jukebox_id}:{user_id}:{client_key}"


async def _require_member(db: AsyncSession, jukebox_id: int, user_id: int) -> None:
    member_id = (
        await db.execute(
            select(JukeboxMember.id).where(
                JukeboxMember.jukebox_id == jukebox_id,
                JukeboxMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if member_id is None:
        raise AppError("el usuario no es miembro", code="member_not_found", status_code=404)


async def member_wallet(
    db: AsyncSession, *, jukebox_id: int, user_id: int, limit: int = 20
) -> WalletOut:
    await _require_member(db, jukebox_id, user_id)
    transactions = [
        WalletTransactionOut.model_validate(tx)
        for tx in await wallet_service.list_transactions(db, user_id, limit=limit)
    ]
    return WalletOut(credits=await wallet_service.balance(db, user_id), transactions=transactions)


async def adjust_credits(
    db: AsyncSession,
    *,
    jukebox_id: int,
    user_id: int,
    amount: int,
    reason: str,
    idempotency_key: str,
) -> int:
    if amount == 0 or abs(amount) > MAX_ADJUSTMENT:
        raise AppError("importe inválido", code="invalid_amount", status_code=422)
    await _require_member(db, jukebox_id, user_id)
    key = adjustment_key(jukebox_id, user_id, idempotency_key)
    if amount > 0:
        return await wallet_service.credit(
            db,
            user_id,
            amount,
            idempotency_key=key,
            kind="admin_adjust",
            description=reason,
        )
    return await wallet_service.debit(
        db,
        user_id,
        -amount,
        idempotency_key=key,
        kind="admin_adjust",
        description=reason,
    )
