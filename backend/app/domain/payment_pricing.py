from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PaymentPricing(Base, TimestampMixin):
    __tablename__ = "payment_pricing"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    cents_per_credit: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="cop")
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
