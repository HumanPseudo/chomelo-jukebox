from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import Profile

ADD_TRACK = 10
TRACK_PLAYED = 20
CAST_VOTE = 5
CREATE_POLL = 10
POLL_VOTE = 5


async def grant_xp(db: AsyncSession, user_id: int, amount: int) -> None:
    """Suma XP al perfil. Solo el servidor otorga XP (nunca el cliente)."""
    profile = (
        await db.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none()
    if profile is not None:
        profile.xp = profile.xp + amount
