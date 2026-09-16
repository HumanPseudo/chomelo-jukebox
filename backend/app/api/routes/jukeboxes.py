from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_membership, require_role
from app.api.schemas.jukebox import (
    JukeboxCreate,
    JukeboxJoin,
    JukeboxOut,
    JukeboxUpdate,
    MemberOut,
    RoleUpdate,
)
from app.core.exceptions import AppError
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role
from app.domain.user import User
from app.infra.rate_limit import is_rate_limited
from app.services import jukebox_service

router = APIRouter(prefix="/jukeboxes", tags=["jukeboxes"])


@router.post("", response_model=JukeboxOut, status_code=status.HTTP_201_CREATED)
async def create_jukebox(
    payload: JukeboxCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JukeboxOut:
    return await jukebox_service.create_jukebox(db, current_user, payload)


@router.get("", response_model=list[JukeboxOut])
async def list_my_jukeboxes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JukeboxOut]:
    return await jukebox_service.list_my_jukeboxes(db, current_user)


@router.post("/join", response_model=JukeboxOut, status_code=status.HTTP_201_CREATED)
async def join_jukebox(
    payload: JukeboxJoin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JukeboxOut:
    client_ip = request.client.host if request.client else None
    if client_ip and await is_rate_limited(f"join:{client_ip}", limit=10, window=60):
        raise AppError(
            "demasiados intentos de unirse, espera un momento",
            code="rate_limited",
            status_code=429,
        )
    return await jukebox_service.join_by_code(db, current_user, payload.invite_code)


@router.get("/{jukebox_id}", response_model=JukeboxOut)
async def get_jukebox(
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> JukeboxOut:
    return await jukebox_service.get_jukebox_out(db, member)


@router.patch("/{jukebox_id}", response_model=JukeboxOut)
async def update_jukebox(
    payload: JukeboxUpdate,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> JukeboxOut:
    return await jukebox_service.update_jukebox(db, member, payload)


@router.delete("/{jukebox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jukebox(
    member: JukeboxMember = Depends(require_role(Role.OWNER)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await jukebox_service.delete_jukebox(db, member)


@router.post("/{jukebox_id}/invite", response_model=dict[str, str])
async def regenerate_invite(
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    code = await jukebox_service.regenerate_invite_code(db, member)
    return {"invite_code": code}


@router.get("/{jukebox_id}/members", response_model=list[MemberOut])
async def list_jukebox_members(
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[MemberOut]:
    return await jukebox_service.list_members(db, member.jukebox_id)


@router.patch("/{jukebox_id}/members/{user_id}", response_model=MemberOut)
async def set_member_role(
    user_id: int,
    payload: RoleUpdate,
    actor: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    return await jukebox_service.set_member_role(db, actor, actor.jukebox_id, user_id, payload.role)


@router.delete("/{jukebox_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_jukebox_member(
    user_id: int,
    actor: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> None:
    await jukebox_service.remove_member(db, actor, actor.jukebox_id, user_id)
