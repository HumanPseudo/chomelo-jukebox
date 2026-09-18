from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_membership, get_music_provider, require_role
from app.api.schemas.queue import (
    BoostRequest,
    ItemMove,
    PlayerStateOut,
    QueueAdd,
    QueueItemOut,
    QueueOut,
    SeekRequest,
)
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role
from app.providers.music import MusicProvider
from app.services import audit_service, queue_service, vote_service

router = APIRouter(prefix="/jukeboxes", tags=["jukebox", "queue"])

_PLAYER_IDLE = PlayerStateOut(is_playing=False, position_ms=0, current_item_id=None)


def _item_out(item, score: int = 0, voted_by_me: bool = False) -> QueueItemOut:
    return QueueItemOut(
        id=item.id,
        track_id=item.track_id,
        title=item.title,
        artist=item.artist,
        duration_seconds=item.duration_seconds,
        thumbnail_url=item.thumbnail_url,
        added_by=item.added_by,
        status=item.status,
        position=item.position,
        created_at=item.created_at,
        score=score,
        voted_by_me=voted_by_me,
        boost=item.boost,
    )


@router.get("/{jukebox_id}/queue", response_model=QueueOut)
async def get_queue(
    jukebox_id: int,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> QueueOut:
    items, player, scores, my_votes = await queue_service.get_queue(
        db, jukebox_id=member.jukebox_id, user_id=member.user_id
    )
    if player is None:
        player_state = _PLAYER_IDLE
    else:
        current = next((i for i in items if i.id == player.current_item_id), None)
        player_state = PlayerStateOut(
            is_playing=player.is_playing,
            position_ms=queue_service.live_position_ms(
                player, duration_seconds=current.duration_seconds if current else None
            ),
            current_item_id=player.current_item_id,
        )
    return QueueOut(
        items=[_item_out(i, scores.get(i.id, 0), i.id in my_votes) for i in items],
        player=player_state,
    )


@router.post(
    "/{jukebox_id}/queue", response_model=QueueItemOut, status_code=status.HTTP_201_CREATED
)
async def add_to_queue(
    jukebox_id: int,
    payload: QueueAdd,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    provider: MusicProvider = Depends(get_music_provider),
) -> QueueItemOut:
    item = await queue_service.add_to_queue(db, member, provider, payload.track_id)
    return _item_out(item)


@router.delete("/{jukebox_id}/queue/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_queue(
    jukebox_id: int,
    item_id: int,
    request: Request,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> None:
    await queue_service.remove_item(db, member, item_id)
    await audit_service.log_action(
        db,
        action="queue.remove",
        user_id=member.user_id,
        resource_type="queue_item",
        resource_id=item_id,
        detail={"jukebox_id": jukebox_id},
        request=request,
    )
    await db.commit()


@router.patch("/{jukebox_id}/queue/{item_id}/move", response_model=QueueItemOut)
async def move_queue_item(
    jukebox_id: int,
    item_id: int,
    payload: ItemMove,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> QueueItemOut:
    item = await queue_service.move_item(db, member, item_id, payload.position)
    return _item_out(item)


@router.get("/{jukebox_id}/history", response_model=list[QueueItemOut])
async def get_history(
    jukebox_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[QueueItemOut]:
    items = await queue_service.get_history(db, member.jukebox_id, limit=limit)
    return [_item_out(i) for i in items]


@router.post("/{jukebox_id}/player/play", status_code=status.HTTP_204_NO_CONTENT)
async def player_play(
    jukebox_id: int,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await queue_service.player_play(db, member.jukebox_id)


@router.post("/{jukebox_id}/player/pause", status_code=status.HTTP_204_NO_CONTENT)
async def player_pause(
    jukebox_id: int,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await queue_service.player_pause(db, member.jukebox_id)


@router.post("/{jukebox_id}/player/resume", status_code=status.HTTP_204_NO_CONTENT)
async def player_resume(
    jukebox_id: int,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await queue_service.player_resume(db, member.jukebox_id)


@router.post("/{jukebox_id}/player/next", status_code=status.HTTP_204_NO_CONTENT)
async def player_next(
    jukebox_id: int,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await queue_service.player_skip(db, member.jukebox_id)


@router.post("/{jukebox_id}/player/previous", status_code=status.HTTP_204_NO_CONTENT)
async def player_previous(
    jukebox_id: int,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await queue_service.player_previous(db, member.jukebox_id)


@router.post("/{jukebox_id}/player/seek", status_code=status.HTTP_204_NO_CONTENT)
async def player_seek(
    jukebox_id: int,
    payload: SeekRequest,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await queue_service.player_seek(db, member.jukebox_id, payload.position_ms)


# ---------- votos ----------


@router.post("/{jukebox_id}/queue/{item_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def cast_vote(
    jukebox_id: int,
    item_id: int,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> None:
    await vote_service.cast_vote(db, member, item_id)


@router.delete("/{jukebox_id}/queue/{item_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def remove_vote(
    jukebox_id: int,
    item_id: int,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> None:
    await vote_service.remove_vote(db, member, item_id)


# ---------- impulso pagado ----------


@router.post("/{jukebox_id}/queue/{item_id}/boost", response_model=QueueItemOut)
async def boost_item(
    jukebox_id: int,
    item_id: int,
    payload: BoostRequest,
    request: Request,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> QueueItemOut:
    item = await queue_service.boost_item(db, member, item_id, payload.credits)
    await audit_service.log_action(
        db,
        action="queue.boost",
        user_id=member.user_id,
        resource_type="queue_item",
        resource_id=item_id,
        detail={"jukebox_id": jukebox_id, "credits": payload.credits},
        request=request,
    )
    await db.commit()
    return _item_out(item)
