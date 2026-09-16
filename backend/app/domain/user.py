from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.wallet import Wallet


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)

    profile: Mapped[Profile] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    wallet: Mapped[Wallet] = relationship(
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    user: Mapped[User] = relationship(back_populates="profile")


def level_for_xp(xp: int) -> int:
    """Nivel: +1 por cada 100 XP (100 XP = nivel 2, etc.)."""
    return xp // 100 + 1
