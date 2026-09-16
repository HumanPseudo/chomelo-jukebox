from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PollStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Poll(Base, TimestampMixin):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jukebox_id: Mapped[int] = mapped_column(
        ForeignKey("jukeboxes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(String(300), nullable=False)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=PollStatus.OPEN.value
    )
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    options: Mapped[list[PollOption]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PollOption.id",
    )


class PollOption(Base, TimestampMixin):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(200), nullable=False)

    poll: Mapped[Poll] = relationship(back_populates="options", single_parent=True)


class PollVote(Base, TimestampMixin):
    __tablename__ = "poll_votes"
    __table_args__ = (
        UniqueConstraint("poll_id", "user_id", name="uq_poll_votes_poll_user"),
        UniqueConstraint("poll_id", "option_id", "user_id", name="uq_poll_votes_poll_option_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_id: Mapped[int] = mapped_column(
        ForeignKey("poll_options.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
