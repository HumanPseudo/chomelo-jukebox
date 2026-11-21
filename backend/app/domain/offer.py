from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OfferStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXHAUSTED = "EXHAUSTED"
    CLOSED = "CLOSED"


class RedemptionStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REDEEMED = "REDEEMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class Offer(Base, TimestampMixin):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jukebox_id: Mapped[int] = mapped_column(
        ForeignKey("jukeboxes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    merchant: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    terms: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cost_credits: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_total: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=OfferStatus.ACTIVE.value
    )
    starts_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(nullable=True)


class OfferRedemption(Base, TimestampMixin):
    __tablename__ = "offer_redemptions"
    __table_args__ = (
        UniqueConstraint("offer_id", "user_id", name="uq_offer_redemptions_offer_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jukebox_id: Mapped[int] = mapped_column(
        ForeignKey("jukeboxes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    credits_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=RedemptionStatus.PENDING.value
    )
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    redeemed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str] = mapped_column(String(300), nullable=False, server_default="")
