from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.domain.jukebox import JukeboxMember, Role
from app.domain.queue import Player, QueueItem, QueueStatus
from app.domain.vote import Vote
from app.infra.events import notify_jukebox
from app.providers.music import MusicProvider
from app.services import music_service, wallet_service, xp_service


async def _get_player(db: AsyncSession, jukebox_id: int, *, create: bool) -> Player | None:
    player = await db.get(Player, jukebox_id)
    if player is None and create:
        player = Player(jukebox_id=jukebox_id)
        db.add(player)
        await db.flush()
    return player


async def _queued(db: AsyncSession, jukebox_id: int) -> list[QueueItem]:
    return list(
        (
            await db.execute(
                select(QueueItem)
                .where(
                    QueueItem.jukebox_id == jukebox_id,
                    QueueItem.status == QueueStatus.QUEUED.value,
                )
                .order_by(QueueItem.position.asc())
            )
        ).scalars()
    )


async def _current_item(db: AsyncSession, player: Player) -> QueueItem | None:
    if player.current_item_id is None:
        return None
    return await db.get(QueueItem, player.current_item_id)


async def _item_scores(db: AsyncSession, jukebox_id: int) -> dict[int, int]:
    rows = await db.execute(
        select(Vote.queue_item_id, func.count(Vote.id))
        .where(Vote.jukebox_id == jukebox_id)
        .group_by(Vote.queue_item_id)
    )
    return {item_id: total for item_id, total in rows.all()}


async def _my_voted_item_ids(db: AsyncSession, jukebox_id: int, user_id: int) -> set[int]:
    rows = await db.execute(
        select(Vote.queue_item_id).where(Vote.jukebox_id == jukebox_id, Vote.user_id == user_id)
    )
    return set(rows.scalars())


async def reorder_queue_by_score(db: AsyncSession, jukebox_id: int) -> None:
    """Reordena los ítems QUEUED por (votos + impulso pagado) DESC, posición ASC."""
    queued = await _queued(db, jukebox_id)
    scores = await _item_scores(db, jukebox_id)
    queued.sort(
        key=lambda i: (
            -(scores.get(i.id, 0) + i.boost),
            i.position if i.position is not None else 0,
        )
    )
    for index, item in enumerate(queued):
        item.position = index
    await db.commit()


async def boost_item(
    db: AsyncSession, actor: JukeboxMember, item_id: int, credits: int
) -> QueueItem:
    """Gasta créditos para impulsar la posición de un ítem en la cola."""
    item = await db.get(QueueItem, item_id)
    if item is None or item.jukebox_id != actor.jukebox_id:
        raise AppError("ítem no encontrado", code="queue_item_not_found", status_code=404)
    if item.status != QueueStatus.QUEUED.value:
        raise AppError(
            "solo se pueden impulsar ítems en cola", code="item_not_boostable", status_code=409
        )
    await wallet_service.debit(
        db,
        actor.user_id,
        credits,
        idempotency_key=f"boost:{actor.user_id}:{item_id}:{uuid4().hex}",
        kind="boost",
        description=f"Impulsaste «{item.title}»",
    )
    item.boost += credits
    await db.commit()
    await reorder_queue_by_score(db, actor.jukebox_id)
    await notify_jukebox(actor.jukebox_id, "queue.updated", item_id=item.id)
    return item


async def add_to_queue(
    db: AsyncSession, member: JukeboxMember, provider: MusicProvider, track_id: str
) -> QueueItem:
    track = await music_service.get_track(provider, track_id)
    queued = await _queued(db, member.jukebox_id)
    item = QueueItem(
        jukebox_id=member.jukebox_id,
        track_id=track.track_id,
        title=track.title,
        artist=track.artist,
        duration_seconds=track.duration_seconds,
        thumbnail_url=track.thumbnail_url,
        added_by=member.user_id,
        status=QueueStatus.QUEUED.value,
        position=len(queued),
    )
    db.add(item)
    await db.flush()
    await xp_service.grant_xp(db, member.user_id, xp_service.ADD_TRACK)
    await wallet_service.credit(
        db,
        member.user_id,
        wallet_service.ADD_TRACK_CREDIT,
        idempotency_key=f"add_track:{member.user_id}:{item.id}",
        kind="add_track",
        description="Añadiste una canción a la cola",
    )
    await db.commit()
    await db.refresh(item)
    await notify_jukebox(member.jukebox_id, "queue.updated", item_id=item.id)
    return item


async def get_queue(
    db: AsyncSession, jukebox_id: int, *, user_id: int
) -> tuple[list[QueueItem], Player | None, dict[int, int], set[int]]:
    items = list(
        (
            await db.execute(
                select(QueueItem)
                .where(
                    QueueItem.jukebox_id == jukebox_id,
                    QueueItem.status.in_([QueueStatus.QUEUED.value, QueueStatus.PLAYING.value]),
                )
                .order_by(QueueItem.position.asc())
            )
        ).scalars()
    )
    items.sort(
        key=lambda i: (
            0 if i.status == QueueStatus.PLAYING.value else 1,
            i.position if i.position is not None else 10**9,
        )
    )
    player = await _get_player(db, jukebox_id, create=False)
    scores = await _item_scores(db, jukebox_id)
    my_votes = await _my_voted_item_ids(db, jukebox_id, user_id)
    return items, player, scores, my_votes


async def get_history(db: AsyncSession, jukebox_id: int, limit: int = 50) -> list[QueueItem]:
    return list(
        (
            await db.execute(
                select(QueueItem)
                .where(
                    QueueItem.jukebox_id == jukebox_id,
                    QueueItem.status == QueueStatus.PLAYED.value,
                )
                .order_by(QueueItem.played_at.desc())
                .limit(limit)
            )
        ).scalars()
    )


async def remove_item(db: AsyncSession, actor: JukeboxMember, item_id: int) -> None:
    item = await db.get(QueueItem, item_id)
    if item is None or item.jukebox_id != actor.jukebox_id:
        raise AppError("ítem no encontrado", code="queue_item_not_found", status_code=404)
    if item.status != QueueStatus.QUEUED.value:
        raise AppError(
            "solo se pueden quitar ítems en cola", code="item_not_removable", status_code=409
        )
    can_moderate = Role(actor.role) is Role.ADMIN
    if not can_moderate and item.added_by != actor.user_id:
        raise AppError("permiso insuficiente", code="insufficient_role", status_code=403)

    original_position = item.position
    await db.delete(item)
    for queued in await _queued(db, actor.jukebox_id):
        if (
            queued.position is not None
            and original_position is not None
            and queued.position > original_position
        ):
            queued.position -= 1
    await db.commit()
    await notify_jukebox(actor.jukebox_id, "queue.updated", item_id=item_id)


async def move_item(
    db: AsyncSession, actor: JukeboxMember, item_id: int, position: int
) -> QueueItem:
    item = await db.get(QueueItem, item_id)
    if item is None or item.jukebox_id != actor.jukebox_id:
        raise AppError("ítem no encontrado", code="queue_item_not_found", status_code=404)
    if item.status != QueueStatus.QUEUED.value:
        raise AppError("ítem no es movible", code="item_not_removable", status_code=409)

    order = await _queued(db, actor.jukebox_id)
    if item not in order:
        raise AppError("ítem no encontrado", code="queue_item_not_found", status_code=404)
    order.remove(item)
    clamped = min(max(position, 0), len(order))
    order.insert(clamped, item)
    for index, queued in enumerate(order):
        queued.position = index
    await db.commit()
    await db.refresh(item)
    await notify_jukebox(actor.jukebox_id, "queue.updated", item_id=item.id)
    return item


async def player_play(db: AsyncSession, jukebox_id: int) -> None:
    player = await _get_player(db, jukebox_id, create=True)
    current = await _current_item(db, player)
    if current is not None and current.status == QueueStatus.PLAYING.value:
        player.is_playing = True
        await db.commit()
        await notify_jukebox(jukebox_id, "player.updated")
        return
    queued = await _queued(db, jukebox_id)
    if not queued:
        raise AppError("la cola está vacía", code="queue_empty", status_code=409)
    item = queued[0]
    item.status = QueueStatus.PLAYING.value
    item.played_at = datetime.now(UTC)
    player.current_item_id = item.id
    player.is_playing = True
    player.position_ms = 0
    await xp_service.grant_xp(db, item.added_by, xp_service.TRACK_PLAYED)
    await wallet_service.credit(
        db,
        item.added_by,
        wallet_service.TRACK_PLAYED_CREDIT,
        idempotency_key=f"track_played:{item.added_by}:{item.id}",
        kind="track_played",
        description="Tu canción se reprodujo",
    )
    await db.commit()
    await notify_jukebox(jukebox_id, "player.updated")
    return


async def player_pause(db: AsyncSession, jukebox_id: int) -> None:
    player = await _get_player(db, jukebox_id, create=True)
    current = await _current_item(db, player)
    if current is None:
        raise AppError("no hay nada reproduciéndose", code="nothing_playing", status_code=409)
    player.is_playing = False
    await db.commit()
    await notify_jukebox(jukebox_id, "player.updated")


async def player_resume(db: AsyncSession, jukebox_id: int) -> None:
    player = await _get_player(db, jukebox_id, create=True)
    current = await _current_item(db, player)
    if current is None:
        raise AppError("no hay nada reproduciéndose", code="nothing_playing", status_code=409)
    player.is_playing = True
    await db.commit()
    await notify_jukebox(jukebox_id, "player.updated")


async def player_skip(db: AsyncSession, jukebox_id: int) -> None:
    player = await _get_player(db, jukebox_id, create=True)
    current = await _current_item(db, player)
    if current is not None and current.status == QueueStatus.PLAYING.value:
        current.status = QueueStatus.PLAYED.value
        current.played_at = datetime.now(UTC)
        current.position = None

    queued = await _queued(db, jukebox_id)
    if queued:
        item = queued[0]
        item.status = QueueStatus.PLAYING.value
        item.played_at = datetime.now(UTC)
        player.current_item_id = item.id
        player.is_playing = True
        player.position_ms = 0
        await xp_service.grant_xp(db, item.added_by, xp_service.TRACK_PLAYED)
        await wallet_service.credit(
            db,
            item.added_by,
            wallet_service.TRACK_PLAYED_CREDIT,
            idempotency_key=f"track_played:{item.added_by}:{item.id}",
            kind="track_played",
            description="Tu canción se reprodujo",
        )
    else:
        player.current_item_id = None
        player.is_playing = False
        player.position_ms = 0
    await db.commit()
    await notify_jukebox(jukebox_id, "player.updated")


async def player_previous(db: AsyncSession, jukebox_id: int) -> None:
    """Vuelve a poner en PLAYING la última canción reproducida antes de la
    actual. La que estaba sonando regresa al frente de la cola (QUEUED),
    no se pierde. No vuelve a otorgar XP/créditos: eso ya pasó la primera
    vez que sonó."""
    player = await _get_player(db, jukebox_id, create=True)
    current = await _current_item(db, player)

    previous = (
        await db.execute(
            select(QueueItem)
            .where(
                QueueItem.jukebox_id == jukebox_id,
                QueueItem.status == QueueStatus.PLAYED.value,
            )
            .order_by(QueueItem.played_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if previous is None:
        raise AppError(
            "no hay una canción anterior en el historial",
            code="no_previous_track",
            status_code=409,
        )

    if current is not None and current.status == QueueStatus.PLAYING.value:
        for queued in await _queued(db, jukebox_id):
            if queued.position is not None:
                queued.position += 1
        current.status = QueueStatus.QUEUED.value
        current.played_at = None
        current.position = 0

    previous.status = QueueStatus.PLAYING.value
    previous.played_at = datetime.now(UTC)
    previous.position = None
    player.current_item_id = previous.id
    player.is_playing = True
    player.position_ms = 0
    await db.commit()
    await notify_jukebox(jukebox_id, "player.updated")


async def player_seek(db: AsyncSession, jukebox_id: int, position_ms: int) -> None:
    player = await _get_player(db, jukebox_id, create=True)
    current = await _current_item(db, player)
    if current is None:
        raise AppError("no hay nada reproduciéndose", code="nothing_playing", status_code=409)
    clamped = position_ms
    if current.duration_seconds:
        clamped = min(position_ms, current.duration_seconds * 1000)
    player.position_ms = clamped
    await db.commit()
    await notify_jukebox(jukebox_id, "player.updated")
