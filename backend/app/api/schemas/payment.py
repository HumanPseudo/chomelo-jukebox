from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credits: int = Field(ge=5, le=10000)


class PricingOut(BaseModel):
    cents_per_credit: int
    currency: str
    credit_amounts: list[int]


class PricingUpdate(BaseModel):
    cents_per_credit: int = Field(ge=1, le=100000)
    currency: Literal["cop", "eur", "usd"] = "cop"
    credit_amounts: list[int] = Field(
        default_factory=lambda: [100, 500, 1000], min_length=1, max_length=12
    )

    @field_validator("credit_amounts")
    @classmethod
    def _validate_credit_amounts(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("las cantidades no pueden repetirse")
        if any(amount < 1 or amount > 100000 for amount in value):
            raise ValueError("cada cantidad debe estar entre 1 y 100000")
        return sorted(value)


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
