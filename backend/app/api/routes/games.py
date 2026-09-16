from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, get_membership, require_role
from app.api.schemas.game import AnswerRequest, AttemptOut, RoundOut, RoundStartRequest
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role
from app.services import game_service

router = APIRouter(prefix="/jukeboxes", tags=["jukebox", "game"])


@router.post(
    "/{jukebox_id}/games/{game_key}/rounds",
    response_model=RoundOut,
    status_code=201,
)
async def create_round(
    jukebox_id: int,
    game_key: str,
    payload: RoundStartRequest,
    member: JukeboxMember = Depends(require_role(Role.MODERATOR)),
    db: AsyncSession = Depends(get_db),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> RoundOut:
    return await game_service.start_round(db, member, game_key, payload.duration_seconds, clock())


@router.get(
    "/{jukebox_id}/games/{game_key}/rounds",
    response_model=list[RoundOut],
)
async def list_rounds(
    jukebox_id: int,
    game_key: str,
    status: str | None = Query(default=None),
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> list[RoundOut]:
    return await game_service.list_rounds(db, member, game_key, status, clock())


@router.get(
    "/{jukebox_id}/games/{game_key}/rounds/{round_id}",
    response_model=RoundOut,
)
async def get_round(
    jukebox_id: int,
    game_key: str,
    round_id: int,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> RoundOut:
    return await game_service.get_round(db, member, game_key, round_id, clock())


@router.post(
    "/{jukebox_id}/games/{game_key}/rounds/{round_id}/answer",
    response_model=AttemptOut,
)
async def answer_round(
    jukebox_id: int,
    game_key: str,
    round_id: int,
    payload: AnswerRequest,
    member: JukeboxMember = Depends(require_role(Role.MEMBER)),
    db: AsyncSession = Depends(get_db),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> AttemptOut:
    return await game_service.guess(db, member, game_key, round_id, payload.title, clock())
