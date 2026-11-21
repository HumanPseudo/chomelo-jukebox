from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OfferStatusValue = Literal["ACTIVE", "PAUSED", "EXHAUSTED", "CLOSED"]
RedemptionStatusValue = Literal["PENDING", "APPROVED", "REDEEMED", "CANCELLED", "EXPIRED"]


class OfferCreate(BaseModel):
    merchant: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=500)
    terms: str = Field(default="", max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    cost_credits: int = Field(ge=1, le=100000)
    stock_total: int = Field(ge=1, le=100000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_window(self) -> "OfferCreate":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at debe ser posterior a starts_at")
        return self


class OfferUpdate(BaseModel):
    merchant: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    terms: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    cost_credits: int | None = Field(default=None, ge=1, le=100000)
    stock_total: int | None = Field(default=None, ge=1, le=100000)
    status: OfferStatusValue | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jukebox_id: int
    merchant: str
    title: str
    description: str
    terms: str
    image_url: str | None
    cost_credits: int
    stock_total: int
    stock_remaining: int
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    my_redemption_status: str | None = None
    my_code: str | None = None


class RedemptionUpdate(BaseModel):
    status: Literal["APPROVED", "REDEEMED", "CANCELLED", "EXPIRED"]
    notes: str = Field(default="", max_length=300)


class RedemptionOut(BaseModel):
    id: int
    jukebox_id: int
    offer_id: int
    offer_title: str
    user_id: int
    code: str | None
    credits_spent: int
    status: str
    notes: str
    created_at: datetime
    approved_at: datetime | None
    redeemed_at: datetime | None
