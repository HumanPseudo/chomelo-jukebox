from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.wallet import WalletOut, WalletTransactionOut
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.user import User
from app.services import wallet_service

router = APIRouter(prefix="/users", tags=["users", "wallet"])


@router.get("/me/wallet", response_model=WalletOut)
async def my_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletOut:
    credits = await wallet_service.balance(db, current_user.id)
    transactions = [
        WalletTransactionOut.model_validate(t)
        for t in await wallet_service.list_transactions(db, current_user.id, limit=20)
    ]
    return WalletOut(credits=credits, transactions=transactions)


@router.get("/me/wallet/transactions", response_model=list[WalletTransactionOut])
async def my_wallet_transactions(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WalletTransactionOut]:
    transactions = await wallet_service.list_transactions(
        db, current_user.id, limit=limit, offset=offset
    )
    return [WalletTransactionOut.model_validate(t) for t in transactions]
