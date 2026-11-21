from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_membership, require_role
from app.api.schemas.activity import ActivityOut
from app.api.schemas.jukebox import (
    JukeboxCreate,
    JukeboxJoin,
    JukeboxOut,
    JukeboxUpdate,
    MemberOut,
    RoleUpdate,
)
from app.api.schemas.wallet import CreditAdjustment, CreditAdjustmentOut, WalletOut
from app.core.exceptions import AppError
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role
from app.domain.user import User
from app.infra.rate_limit import is_rate_limited
from app.services import (
    activity_service,
    audit_service,
    jukebox_service,
    reward_service,
    wallet_service,
)

router = APIRouter(prefix="/jukeboxes", tags=["jukeboxes"])


@router.post("", response_model=JukeboxOut, status_code=status.HTTP_201_CREATED)
async def create_jukebox(
    payload: JukeboxCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JukeboxOut:
    if not current_user.is_superuser:
        raise AppError("solo el admin puede crear transmisiones", code="forbidden", status_code=403)
    jb = await jukebox_service.create_jukebox(db, current_user, payload)
    await audit_service.log_action(
        db,
        action="jukebox.create",
        user_id=current_user.id,
        resource_type="jukebox",
        resource_id=jb.id,
        request=request,
    )
    await db.commit()
    return jb


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
    request: Request,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await jukebox_service.delete_jukebox(db, member)
    await audit_service.log_action(
        db,
        action="jukebox.delete",
        user_id=member.user_id,
        resource_type="jukebox",
        resource_id=member.jukebox_id,
        request=request,
    )
    await db.commit()


@router.post("/{jukebox_id}/invite", response_model=dict[str, str])
async def regenerate_invite(
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    code = await jukebox_service.regenerate_invite_code(db, member)
    return {"invite_code": code}


@router.get("/{jukebox_id}/activity", response_model=list[ActivityOut])
async def jukebox_activity(
    jukebox_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityOut]:
    return await activity_service.recent_activity(db, member.jukebox_id, limit=limit)


@router.get("/{jukebox_id}/members", response_model=list[MemberOut])
async def list_jukebox_members(
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[MemberOut]:
    return await jukebox_service.list_members(db, member.jukebox_id)


@router.patch("/{jukebox_id}/members/{user_id}", response_model=MemberOut)
async def set_member_role(
    user_id: int,
    payload: RoleUpdate,
    request: Request,
    actor: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    updated = await jukebox_service.set_member_role(
        db, actor, actor.jukebox_id, user_id, payload.role
    )
    await audit_service.log_action(
        db,
        action="member.role_change",
        user_id=actor.user_id,
        resource_type="jukebox_member",
        resource_id=user_id,
        detail={"jukebox_id": actor.jukebox_id, "role": payload.role},
        request=request,
    )
    await db.commit()
    return updated


@router.delete("/{jukebox_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_jukebox_member(
    user_id: int,
    request: Request,
    actor: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await jukebox_service.remove_member(db, actor, actor.jukebox_id, user_id)
    await audit_service.log_action(
        db,
        action="member.remove",
        user_id=actor.user_id,
        resource_type="jukebox_member",
        resource_id=user_id,
        detail={"jukebox_id": actor.jukebox_id},
        request=request,
    )
    await db.commit()


@router.get("/{jukebox_id}/members/{user_id}/wallet", response_model=WalletOut)
async def member_wallet(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=200),
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WalletOut:
    return await reward_service.member_wallet(
        db, jukebox_id=member.jukebox_id, user_id=user_id, limit=limit
    )


@router.post("/{jukebox_id}/members/{user_id}/credits", response_model=CreditAdjustmentOut)
async def adjust_member_credits(
    user_id: int,
    payload: CreditAdjustment,
    request: Request,
    actor: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> CreditAdjustmentOut:
    key = reward_service.adjustment_key(actor.jukebox_id, user_id, payload.idempotency_key)
    applied = await wallet_service.has_transaction(db, user_id, key)
    credits = await reward_service.adjust_credits(
        db,
        jukebox_id=actor.jukebox_id,
        user_id=user_id,
        amount=payload.amount,
        reason=payload.reason,
        idempotency_key=payload.idempotency_key,
    )
    if not applied:
        await audit_service.log_action(
            db,
            action="wallet.admin_adjust",
            user_id=actor.user_id,
            resource_type="jukebox_member",
            resource_id=user_id,
            detail={
                "jukebox_id": actor.jukebox_id,
                "amount": payload.amount,
                "reason": payload.reason,
                "idempotency_key": key,
            },
            request=request,
        )
    await db.commit()
    return CreditAdjustmentOut(credits=credits)
