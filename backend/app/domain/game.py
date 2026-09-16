from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class GameStatus(StrEnum):
    OPEN = "OPEN"
    FINISHED = "FINISHED"


class GameRound(Base, TimestampMixin):
    __tablename__ = "game_rounds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jukebox_id: Mapped[int] = mapped_column(
        ForeignKey("jukeboxes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_key: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    track_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    artist: Mapped[str] = mapped_column(String(200), nullable=False, server_default="")
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    options: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=GameStatus.OPEN.value
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GameAttempt(Base, TimestampMixin):
    __tablename__ = "game_attempts"
    __table_args__ = (UniqueConstraint("round_id", "user_id", name="uq_game_attempts_round_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(
        ForeignKey("game_rounds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    selected: Mapped[str] = mapped_column(String(300), nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    points: Mapped[int] = mapped_column(nullable=False, server_default="0")
