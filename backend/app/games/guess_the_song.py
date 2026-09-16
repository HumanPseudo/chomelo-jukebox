import random
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.domain.queue import QueueItem
from app.games.base import Game, RoundData

DECOYS = 3


class GuessTheSongGame(Game):
    key = "guess_the_song"
    name = "Guess the Song"

    async def build(self, db: AsyncSession, jukebox_id: int, now: datetime) -> RoundData:
        distinct_tracks = (
            select(
                QueueItem.track_id,
                QueueItem.title,
                QueueItem.artist,
                QueueItem.thumbnail_url,
            )
            .where(
                QueueItem.jukebox_id == jukebox_id,
                QueueItem.played_at.is_not(None),
            )
            .distinct()
            .subquery()
        )
        rows = (
            await db.execute(select(distinct_tracks).order_by(func.random()).limit(DECOYS + 1))
        ).all()
        if len(rows) < DECOYS + 1:
            raise AppError(
                f"se necesitan al menos {DECOYS + 1} canciones reproducidas en el jukebox",
                code="not_enough_songs",
                status_code=409,
            )

        answer = rows[0]
        options = [answer.title] + [row.title for row in rows[1:]]
        random.shuffle(options)
        return RoundData(
            track_id=answer.track_id,
            title=answer.title,
            artist=answer.artist,
            thumbnail_url=answer.thumbnail_url,
            options=options,
        )
