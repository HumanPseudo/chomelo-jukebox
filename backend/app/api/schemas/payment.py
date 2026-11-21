from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credits: int = Field(ge=5, le=10000)


class PricingOut(BaseModel):
    cents_per_credit: int
    currency: str


class PricingUpdate(BaseModel):
    cents_per_credit: int = Field(ge=1, le=100000)
    currency: Literal["cop", "eur", "usd"] = "cop"


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
