from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.user import User


class Role(StrEnum):
    """Solo dos roles: ADMIN administra (reproductor, cola, encuestas,
    minijuegos, miembros), MEMBER (oyente) participa. `Jukebox.owner_id`
    guarda quién la creó, pero no da poderes por encima de otro ADMIN."""

    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


_ROLE_RANK = {
    Role.ADMIN: 100,
    Role.MEMBER: 50,
}


def role_rank(role: Role) -> int:
    return _ROLE_RANK[role]


class Jukebox(Base, TimestampMixin):
    __tablename__ = "jukeboxes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    invite_code: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    members: Mapped[list[JukeboxMember]] = relationship(
        back_populates="jukebox",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="JukeboxMember.id",
    )


class JukeboxMember(Base, TimestampMixin):
    __tablename__ = "jukebox_members"
    __table_args__ = (
        UniqueConstraint("jukebox_id", "user_id", name="uq_jukebox_members_jukebox_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jukebox_id: Mapped[int] = mapped_column(
        ForeignKey("jukeboxes.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default=Role.MEMBER.value)

    jukebox: Mapped[Jukebox] = relationship(
        back_populates="members", lazy="selectin", single_parent=True
    )
    user: Mapped[User] = relationship(lazy="selectin")
