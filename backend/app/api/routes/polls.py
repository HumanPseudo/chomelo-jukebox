from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_membership, require_role
from app.api.schemas.poll import PollCreate, PollOut, PollVoteRequest
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role
from app.services import audit_service, poll_service

router = APIRouter(prefix="/jukeboxes", tags=["jukebox", "poll"])


@router.post("/{jukebox_id}/polls", response_model=PollOut, status_code=status.HTTP_201_CREATED)
async def create_poll(
    jukebox_id: int,
    payload: PollCreate,
    member: JukeboxMember = Depends(require_role(Role.MODERATOR)),
    db: AsyncSession = Depends(get_db),
) -> PollOut:
    return await poll_service.create_poll(db, member, payload)


@router.get("/{jukebox_id}/polls", response_model=list[PollOut])
async def list_polls(
    jukebox_id: int,
    poll_status: Literal["OPEN", "CLOSED"] | None = Query(default=None, alias="status"),
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[PollOut]:
    return await poll_service.list_polls(db, member, poll_status)


@router.get("/{jukebox_id}/polls/{poll_id}", response_model=PollOut)
async def get_poll(
    jukebox_id: int,
    poll_id: int,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> PollOut:
    return await poll_service.get_poll(db, member, poll_id)


@router.post("/{jukebox_id}/polls/{poll_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def cast_vote(
    jukebox_id: int,
    poll_id: int,
    payload: PollVoteRequest,
    member: JukeboxMember = Depends(require_role(Role.MEMBER)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await poll_service.cast_vote(db, member, poll_id, payload.option_id)


@router.post("/{jukebox_id}/polls/{poll_id}/close", response_model=PollOut)
async def close_poll(
    jukebox_id: int,
    poll_id: int,
    request: Request,
    member: JukeboxMember = Depends(require_role(Role.MODERATOR)),
    db: AsyncSession = Depends(get_db),
) -> PollOut:
    result = await poll_service.close_poll(db, member, poll_id)
    await audit_service.log_action(
        db,
        action="poll.close",
        user_id=member.user_id,
        resource_type="poll",
        resource_id=poll_id,
        detail={"jukebox_id": jukebox_id},
        request=request,
    )
    await db.commit()
    return result


@router.delete("/{jukebox_id}/polls/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll(
    jukebox_id: int,
    poll_id: int,
    request: Request,
    member: JukeboxMember = Depends(require_role(Role.MODERATOR)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await poll_service.delete_poll(db, member, poll_id)
    await audit_service.log_action(
        db,
        action="poll.delete",
        user_id=member.user_id,
        resource_type="poll",
        resource_id=poll_id,
        detail={"jukebox_id": jukebox_id},
        request=request,
    )
    await db.commit()
