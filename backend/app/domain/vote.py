from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Vote(Base, TimestampMixin):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("queue_item_id", "user_id", name="uq_votes_item_user"),
        UniqueConstraint("jukebox_id", "user_id", name="uq_votes_jukebox_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jukebox_id: Mapped[int] = mapped_column(
        ForeignKey("jukeboxes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    queue_item_id: Mapped[int] = mapped_column(
        ForeignKey("queue_items.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
