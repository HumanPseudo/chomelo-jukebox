from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class QueueStatus(StrEnum):
    QUEUED = "QUEUED"
    PLAYING = "PLAYING"
    PLAYED = "PLAYED"
    SKIPPED = "SKIPPED"


class QueueItem(Base, TimestampMixin):
    __tablename__ = "queue_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jukebox_id: Mapped[int] = mapped_column(
        ForeignKey("jukeboxes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    track_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    artist: Mapped[str] = mapped_column(String(200), nullable=False, server_default="")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    added_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=QueueStatus.QUEUED.value,
        index=True,
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Player(Base, TimestampMixin):
    __tablename__ = "players"

    jukebox_id: Mapped[int] = mapped_column(
        ForeignKey("jukeboxes.id", ondelete="CASCADE"), primary_key=True
    )
    current_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("queue_items.id", ondelete="SET NULL"), nullable=True
    )
    is_playing: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    position_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
