from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.profile import ListenHistoryItem, ProfileOut, ProfileUpdate
from app.core.exceptions import AppError
from app.domain.jukebox import Jukebox
from app.domain.poll import Poll, PollVote
from app.domain.queue import QueueItem
from app.domain.user import Profile, User, level_for_xp
from app.domain.vote import Vote


async def _load_profile(db: AsyncSession, user_id: int) -> Profile:
    profile = (
        await db.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None:
        raise AppError("perfil no encontrado", code="profile_not_found", status_code=404)
    return profile


async def _stats(db: AsyncSession, user_id: int) -> dict[str, int]:
    tracks_added = int(
        (
            await db.execute(
                select(func.count()).select_from(QueueItem).where(QueueItem.added_by == user_id)
            )
        ).scalar_one()
    )
    tracks_played = int(
        (
            await db.execute(
                select(func.count())
                .select_from(QueueItem)
                .where(
                    QueueItem.added_by == user_id,
                    QueueItem.played_at.is_not(None),
                )
            )
        ).scalar_one()
    )
    votes_cast = int(
        (
            await db.execute(select(func.count()).select_from(Vote).where(Vote.user_id == user_id))
        ).scalar_one()
    )
    polls_created = int(
        (
            await db.execute(
                select(func.count()).select_from(Poll).where(Poll.created_by == user_id)
            )
        ).scalar_one()
    )
    poll_votes_cast = int(
        (
            await db.execute(
                select(func.count()).select_from(PollVote).where(PollVote.user_id == user_id)
            )
        ).scalar_one()
    )
    return {
        "tracks_added": tracks_added,
        "tracks_played": tracks_played,
        "votes_cast": votes_cast,
        "polls_created": polls_created,
        "poll_votes_cast": poll_votes_cast,
    }


async def get_profile(db: AsyncSession, user: User) -> ProfileOut:
    profile = await _load_profile(db, user.id)
    stats = await _stats(db, user.id)
    return ProfileOut(
        user_id=user.id,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        xp=profile.xp,
        level=level_for_xp(profile.xp),
        created_at=profile.created_at,
        **stats,
    )


async def update_profile(db: AsyncSession, user: User, payload: ProfileUpdate) -> ProfileOut:
    profile = await _load_profile(db, user.id)
    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.avatar_url is not None:
        profile.avatar_url = payload.avatar_url
    if payload.bio is not None:
        profile.bio = payload.bio
    await db.commit()
    await db.refresh(profile)
    return await get_profile(db, user)


async def listen_history(db: AsyncSession, user: User, limit: int = 50) -> list[ListenHistoryItem]:
    rows = (
        await db.execute(
            select(QueueItem, Jukebox.name)
            .join(Jukebox, Jukebox.id == QueueItem.jukebox_id)
            .where(
                QueueItem.added_by == user.id,
                QueueItem.played_at.is_not(None),
            )
            .order_by(QueueItem.played_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        ListenHistoryItem(
            track_id=item.track_id,
            title=item.title,
            artist=item.artist,
            thumbnail_url=item.thumbnail_url,
            jukebox_name=jukebox_name,
            played_at=item.played_at,
        )
        for item, jukebox_name in rows
    ]
