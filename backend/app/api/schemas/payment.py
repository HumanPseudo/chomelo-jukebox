from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credits: int = Field(ge=5, le=10000)
    currency: str = Field(default="eur", min_length=3, max_length=3)


class PaymentOut(BaseModel):
    id: int
    provider: str
    credits: int
    amount_cents: int
    currency: str
    status: str
    created_at: datetime


class CheckoutOut(BaseModel):
    payment: PaymentOut
    checkout_url: str
