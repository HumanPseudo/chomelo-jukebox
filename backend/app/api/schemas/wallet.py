from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class CreditAdjustment(BaseModel):
    amount: int = Field(ge=-10000, le=10000)
    reason: str = Field(min_length=3, max_length=200)
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,120}$")


class CreditAdjustmentOut(BaseModel):
    credits: int
