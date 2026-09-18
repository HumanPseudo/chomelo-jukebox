from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.activity import ActivityOut
from app.domain.game import GameAttempt, GameRound
from app.domain.jukebox import JukeboxMember
from app.domain.poll import Poll, PollOption, PollVote
from app.domain.queue import QueueItem
from app.domain.user import Profile
from app.domain.vote import Vote

_Entry = tuple[datetime, str, int | None, str | None, str | None, int]


async def _display_names(db: AsyncSession, user_ids: set[int | None]) -> dict[int, str]:
    ids = [uid for uid in user_ids if uid is not None]
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_(ids))
        )
    ).all()
    return {user_id: display_name for user_id, display_name in rows}


async def recent_activity(
    db: AsyncSession, jukebox_id: int, *, limit: int = 30
) -> list[ActivityOut]:
    """Actividad reciente del jukebox mezclada por fecha (desc).

    Es una consulta agregada de tablas existentes — no un segundo sistema de
    eventos. Órdenes por campo temporal propio de cada fuente y junta todo
    para quedarse con las `limit` más recientes. Nunca expone el título de
    una ronda abierta (la respuesta del juego es secreta hasta el cierre).
    """

    entries: list[_Entry] = []

    items = (
        await db.execute(
            select(
                QueueItem.id,
                QueueItem.created_at,
                QueueItem.added_by,
                QueueItem.title,
                QueueItem.artist,
            )
            .where(QueueItem.jukebox_id == jukebox_id)
            .order_by(QueueItem.created_at.desc())
            .limit(limit)
        )
    ).all()
    for row in items:
        entries.append((row.created_at, "queue.add", row.added_by, row.title, row.artist, row.id))

    played = (
        await db.execute(
            select(
                QueueItem.id,
                QueueItem.played_at,
                QueueItem.added_by,
                QueueItem.title,
                QueueItem.artist,
            )
            .where(QueueItem.jukebox_id == jukebox_id, QueueItem.played_at.is_not(None))
            .order_by(QueueItem.played_at.desc())
            .limit(limit)
        )
    ).all()
    for row in played:
        entries.append((row.played_at, "track.played", row.added_by, row.title, row.artist, row.id))

    votes = (
        await db.execute(
            select(Vote.id, Vote.created_at, Vote.user_id, QueueItem.title, QueueItem.artist)
            .join(QueueItem, Vote.queue_item_id == QueueItem.id)
            .where(Vote.jukebox_id == jukebox_id)
            .order_by(Vote.created_at.desc())
            .limit(limit)
        )
    ).all()
    for row in votes:
        entries.append((row.created_at, "vote", row.user_id, row.title, row.artist, row.id))

    polls = (
        await db.execute(
            select(Poll.id, Poll.created_at, Poll.created_by, Poll.question)
            .where(Poll.jukebox_id == jukebox_id)
            .order_by(Poll.created_at.desc())
            .limit(limit)
        )
    ).all()
    for row in polls:
        entries.append((row.created_at, "poll.created", row.created_by, row.question, None, row.id))

    poll_votes = (
        await db.execute(
            select(
                PollVote.id, PollVote.created_at, PollVote.user_id, Poll.question, PollOption.text
            )
            .join(Poll, PollVote.poll_id == Poll.id)
            .join(PollOption, PollVote.option_id == PollOption.id)
            .where(Poll.jukebox_id == jukebox_id)
            .order_by(PollVote.created_at.desc())
            .limit(limit)
        )
    ).all()
    for row in poll_votes:
        entries.append((row.created_at, "poll.vote", row.user_id, row.question, row.text, row.id))

    rounds = (
        await db.execute(
            select(GameRound.id, GameRound.starts_at, GameRound.created_by, GameRound.game_key)
            .where(GameRound.jukebox_id == jukebox_id)
            .order_by(GameRound.starts_at.desc())
            .limit(limit)
        )
    ).all()
    for row in rounds:
        entries.append(
            (
                row.starts_at,
                "game.round",
                row.created_by,
                f"ronda {row.id} de {row.game_key}",
                None,
                row.id,
            )
        )

    winners = (
        await db.execute(
            select(
                GameAttempt.id,
                GameAttempt.created_at,
                GameAttempt.user_id,
                GameRound.id,
                GameRound.game_key,
                GameAttempt.selected,
            )
            .join(GameRound, GameAttempt.round_id == GameRound.id)
            .where(GameRound.jukebox_id == jukebox_id, GameAttempt.correct.is_(True))
            .order_by(GameAttempt.created_at.desc())
            .limit(limit)
        )
    ).all()
    for row in winners:
        entries.append(
            (
                row.created_at,
                "game.won",
                row.user_id,
                f"ronda {row.id} de {row.game_key}",
                row.selected,
                row.id,
            )
        )

    members = (
        await db.execute(
            select(
                JukeboxMember.id,
                JukeboxMember.created_at,
                JukeboxMember.user_id,
                JukeboxMember.role,
            )
            .where(JukeboxMember.jukebox_id == jukebox_id)
            .order_by(JukeboxMember.created_at.desc())
            .limit(limit)
        )
    ).all()
    for row in members:
        entries.append((row.created_at, "member.joined", row.user_id, None, row.role, row.id))

    entries.sort(key=lambda e: e[0], reverse=True)
    entries = entries[:limit]

    names = await _display_names(db, {e[2] for e in entries})

    out: list[ActivityOut] = []
    for created_at, kind, user_id, title, subtitle, entry_id in entries:
        display_name = names.get(user_id, "")
        if kind == "member.joined":
            title = title or display_name or "miembro nuevo"
        out.append(
            ActivityOut(
                id=entry_id,
                kind=kind,
                user_id=user_id,
                display_name=display_name,
                title=title,
                subtitle=subtitle,
                created_at=created_at,
            )
        )
    return out
