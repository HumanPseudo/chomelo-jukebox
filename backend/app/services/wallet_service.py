from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.domain.wallet import Wallet, WalletTransaction

ADD_TRACK_CREDIT = 1
TRACK_PLAYED_CREDIT = 1
CAST_VOTE_CREDIT = 1
CREATE_POLL_CREDIT = 2
POLL_VOTE_CREDIT = 1


def _insert(db: AsyncSession):
    """Insert dialect-specific para usar ON CONFLICT DO NOTHING (SQLite y Postgres)."""
    if db.get_bind().dialect.name == "postgresql":
        return pg_insert(WalletTransaction)
    return sqlite_insert(WalletTransaction)


async def get_wallet(db: AsyncSession, user_id: int, *, create: bool = False) -> Wallet | None:
    wallet = (
        await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    ).scalar_one_or_none()
    if wallet is None and create:
        wallet = Wallet(user_id=user_id, credits=0)
        db.add(wallet)
        await db.flush()
    return wallet


async def _locked_wallet(db: AsyncSession, user_id: int) -> Wallet:
    wallet = await get_wallet(db, user_id, create=True)
    assert wallet is not None
    if wallet.id is not None:
        wallet = (
            await db.execute(select(Wallet).where(Wallet.id == wallet.id).with_for_update())
        ).scalar_one()
    return wallet


async def _ledger(
    db: AsyncSession,
    wallet: Wallet,
    *,
    idempotency_key: str,
    kind: str,
    amount: int,
    description: str,
) -> int:
    """Inserta el movimiento en el ledger si no existe (idempotente) y actualiza el saldo."""
    result = await db.execute(
        _insert(db)
        .values(
            wallet_id=wallet.id,
            idempotency_key=idempotency_key,
            kind=kind,
            amount=amount,
            description=description,
        )
        .on_conflict_do_nothing(index_elements=["wallet_id", "idempotency_key"])
    )
    if result.rowcount is not None and result.rowcount >= 1:
        wallet.credits += amount
    return wallet.credits


async def credit(
    db: AsyncSession,
    user_id: int,
    amount: int,
    *,
    idempotency_key: str,
    kind: str,
    description: str = "",
) -> int:
    """Abona créditos en la wallet. Solo el servidor abona (nunca el cliente)."""
    if amount <= 0:
        raise AppError("importe inválido", code="invalid_amount", status_code=422)
    wallet = await _locked_wallet(db, user_id)
    return await _ledger(
        db,
        wallet,
        idempotency_key=idempotency_key,
        kind=kind,
        amount=amount,
        description=description,
    )


async def debit(
    db: AsyncSession,
    user_id: int,
    amount: int,
    *,
    idempotency_key: str,
    kind: str,
    description: str = "",
) -> int:
    """Cobra créditos de la wallet si hay saldo (con lock). Idempotente por key."""
    if amount <= 0:
        raise AppError("importe inválido", code="invalid_amount", status_code=422)
    wallet = await _locked_wallet(db, user_id)
    already_applied = (
        await db.execute(
            select(WalletTransaction.id).where(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if already_applied is None and wallet.credits < amount:
        raise AppError("saldo insuficiente", code="insufficient_balance", status_code=409)
    return await _ledger(
        db,
        wallet,
        idempotency_key=idempotency_key,
        kind=kind,
        amount=-amount,
        description=description,
    )


async def balance(db: AsyncSession, user_id: int) -> int:
    wallet = await get_wallet(db, user_id, create=False)
    return wallet.credits if wallet is not None else 0


async def list_transactions(
    db: AsyncSession, user_id: int, limit: int = 20, offset: int = 0
) -> list[WalletTransaction]:
    wallet = await get_wallet(db, user_id, create=False)
    if wallet is None:
        return []
    stmt = (
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await db.execute(stmt)).scalars())
