from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WalletTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    amount: int
    description: str = ""
    created_at: datetime


class WalletOut(BaseModel):
    credits: int
    transactions: list[WalletTransactionOut] = []
