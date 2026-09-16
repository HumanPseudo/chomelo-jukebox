from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.domain.jukebox import JukeboxMember
from app.domain.queue import QueueItem, QueueStatus
from app.domain.vote import Vote
from app.infra import rate_limit
from app.infra.events import notify_jukebox
from app.services import queue_service, wallet_service, xp_service

VOTE_RATE_LIMIT = 30
VOTE_RATE_WINDOW = 60


async def _existing_vote(
    db: AsyncSession, jukebox_id: int, user_id: int, item_id: int | None = None
) -> Vote | None:
    stmt = select(Vote).where(Vote.jukebox_id == jukebox_id, Vote.user_id == user_id)
    if item_id is not None:
        stmt = stmt.where(Vote.queue_item_id == item_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def cast_vote(db: AsyncSession, actor: JukeboxMember, item_id: int) -> None:
    if await rate_limit.is_rate_limited(
        f"vote:{actor.user_id}:{actor.jukebox_id}",
        limit=VOTE_RATE_LIMIT,
        window=VOTE_RATE_WINDOW,
    ):
        raise AppError("demasiados votos, espera un momento", code="rate_limited", status_code=429)

    item = await db.get(QueueItem, item_id)
    if item is None or item.jukebox_id != actor.jukebox_id:
        raise AppError("ítem no encontrado", code="queue_item_not_found", status_code=404)
    if item.status != QueueStatus.QUEUED.value:
        raise AppError(
            "solo se pueden votar ítems en cola", code="item_not_votable", status_code=409
        )

    current = await _existing_vote(db, actor.jukebox_id, actor.user_id)
    if current is not None:
        if current.queue_item_id == item_id:
            return
        await db.delete(current)
        await db.flush()

    db.add(Vote(jukebox_id=actor.jukebox_id, queue_item_id=item_id, user_id=actor.user_id))
    await xp_service.grant_xp(db, actor.user_id, xp_service.CAST_VOTE)
    await wallet_service.credit(
        db,
        actor.user_id,
        wallet_service.CAST_VOTE_CREDIT,
        idempotency_key=f"vote:{actor.user_id}:{item_id}",
        kind="vote",
        description="Tu voto ayudó a reordenar la cola",
    )
    await db.commit()
    await queue_service.reorder_queue_by_score(db, actor.jukebox_id)
    await notify_jukebox(actor.jukebox_id, "queue.updated", item_id=item_id)


async def remove_vote(db: AsyncSession, actor: JukeboxMember, item_id: int) -> None:
    vote = await _existing_vote(db, actor.jukebox_id, actor.user_id, item_id=item_id)
    if vote is None:
        return
    await db.delete(vote)
    await db.commit()
    await queue_service.reorder_queue_by_score(db, actor.jukebox_id)
    await notify_jukebox(actor.jukebox_id, "queue.updated", item_id=item_id)
