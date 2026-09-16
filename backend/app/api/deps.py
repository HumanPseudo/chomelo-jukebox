from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role, role_rank
from app.domain.user import User
from app.providers.music import MusicProvider
from app.providers.ytdlp import YtDlpProvider

_music_provider: MusicProvider = YtDlpProvider()


def get_music_provider() -> MusicProvider:
    return _music_provider


def get_clock() -> Callable[[], datetime]:
    """Fuente de tiempo inyectable para probar expiración sin esperar."""
    return lambda: datetime.now(UTC)


async def get_membership(
    jukebox_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JukeboxMember:
    member = (
        await db.execute(
            select(JukeboxMember)
            .where(
                JukeboxMember.jukebox_id == jukebox_id,
                JukeboxMember.user_id == current_user.id,
            )
            .options(selectinload(JukeboxMember.jukebox))
        )
    ).scalar_one_or_none()
    if member is None:
        raise AppError("no eres miembro de este jukebox", code="not_member", status_code=404)
    if not member.jukebox.is_active:
        raise AppError("jukebox no encontrado", code="jukebox_not_found", status_code=404)
    return member


def require_role(min_role: Role) -> Callable[..., JukeboxMember]:
    async def _dependency(member: JukeboxMember = Depends(get_membership)) -> JukeboxMember:
        if role_rank(Role(member.role)) < role_rank(min_role):
            raise AppError("permiso insuficiente", code="insufficient_role", status_code=403)
        return member

    return _dependency
