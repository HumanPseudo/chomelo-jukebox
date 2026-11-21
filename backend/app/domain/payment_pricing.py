from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PaymentPricing(Base, TimestampMixin):
    __tablename__ = "payment_pricing"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    cents_per_credit: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="cop")
    credit_amounts: Mapped[list[int]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: [100, 500, 1000],
        server_default="[100, 500, 1000]",
    )
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
