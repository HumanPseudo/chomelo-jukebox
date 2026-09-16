from __future__ import annotations

from enum import StrEnum

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    CREDITS_GRANTED = "CREDITS_GRANTED"
    FAILED = "FAILED"


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_session_id: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, server_default="eur")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=PaymentStatus.PENDING.value
    )


class PaymentEvent(Base, TimestampMixin):
    """Registro append-only de eventos del proveedor.

    `provider_event_id` es UNIQUE (regla dura #3): cada evento se procesa una vez.
    """

    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider_event_id: Mapped[str] = mapped_column(
        String(200), unique=True, index=True, nullable=False
    )
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    verified: Mapped[bool] = mapped_column(default=True, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
