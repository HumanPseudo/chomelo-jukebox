import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.jukebox import (
    JukeboxCreate,
    JukeboxOut,
    JukeboxUpdate,
    MemberOut,
)
from app.core.exceptions import AppError
from app.domain.jukebox import Jukebox, JukeboxMember, Role
from app.domain.user import User

_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sin caracteres ambiguos (O, 0, I, 1)


def _generate_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(6))


async def _unique_invite_code(db: AsyncSession) -> str:
    for _ in range(20):
        code = _generate_code()
        exists = (await db.execute(select(Jukebox.id).where(Jukebox.invite_code == code))).first()
        if exists is None:
            return code
    raise AppError(
        "no se pudo generar un código de invitación",
        code="code_generation_failed",
        status_code=500,
    )


async def _member_count(db: AsyncSession, jukebox_id: int) -> int:
    total = (
        await db.execute(
            select(func.count())
            .select_from(JukeboxMember)
            .where(JukeboxMember.jukebox_id == jukebox_id)
        )
    ).scalar_one()
    return int(total)


async def create_jukebox(db: AsyncSession, user: User, payload: JukeboxCreate) -> JukeboxOut:
    jukebox = Jukebox(
        name=payload.name,
        description=payload.description,
        owner_id=user.id,
        invite_code=await _unique_invite_code(db),
    )
    jukebox.members.append(JukeboxMember(user_id=user.id, role=Role.ADMIN.value))
    db.add(jukebox)
    await db.commit()
    await db.refresh(jukebox)
    return JukeboxOut(
        id=jukebox.id,
        name=jukebox.name,
        description=jukebox.description,
        owner_id=jukebox.owner_id,
        invite_code=jukebox.invite_code,
        is_active=jukebox.is_active,
        created_at=jukebox.created_at,
        role=Role.ADMIN.value,
        member_count=1,
    )


async def list_my_jukeboxes(db: AsyncSession, user: User) -> list[JukeboxOut]:
    members = (
        (
            await db.execute(
                select(JukeboxMember)
                .where(JukeboxMember.user_id == user.id)
                .options(selectinload(JukeboxMember.jukebox))
                .order_by(JukeboxMember.jukebox_id.desc())
            )
        )
        .scalars()
        .all()
    )
    result: list[JukeboxOut] = []
    for member in members:
        jukebox = member.jukebox
        result.append(
            JukeboxOut(
                id=jukebox.id,
                name=jukebox.name,
                description=jukebox.description,
                owner_id=jukebox.owner_id,
                invite_code=jukebox.invite_code,
                is_active=jukebox.is_active,
                created_at=jukebox.created_at,
                role=member.role,
                member_count=await _member_count(db, jukebox.id),
            )
        )
    return result


async def get_jukebox_out(db: AsyncSession, member: JukeboxMember) -> JukeboxOut:
    jukebox = member.jukebox
    return JukeboxOut(
        id=jukebox.id,
        name=jukebox.name,
        description=jukebox.description,
        owner_id=jukebox.owner_id,
        invite_code=jukebox.invite_code,
        is_active=jukebox.is_active,
        created_at=jukebox.created_at,
        role=member.role,
        member_count=await _member_count(db, jukebox.id),
    )


async def update_jukebox(
    db: AsyncSession, member: JukeboxMember, payload: JukeboxUpdate
) -> JukeboxOut:
    jukebox = member.jukebox
    if payload.name is not None:
        jukebox.name = payload.name
    if payload.description is not None:
        jukebox.description = payload.description
    await db.commit()
    await db.refresh(jukebox)
    return await get_jukebox_out(db, member)


async def delete_jukebox(db: AsyncSession, member: JukeboxMember) -> None:
    await db.delete(member.jukebox)
    await db.commit()


async def regenerate_invite_code(db: AsyncSession, member: JukeboxMember) -> str:
    jukebox = member.jukebox
    jukebox.invite_code = await _unique_invite_code(db)
    await db.commit()
    await db.refresh(jukebox)
    return jukebox.invite_code


async def join_by_code(db: AsyncSession, user: User, invite_code: str) -> JukeboxOut:
    code = invite_code.upper()
    jukebox = (
        await db.execute(
            select(Jukebox)
            .where(Jukebox.invite_code == code)
            .options(selectinload(Jukebox.members))
        )
    ).scalar_one_or_none()
    if jukebox is None or not jukebox.is_active:
        raise AppError("código de invitación inválido", code="invite_invalid", status_code=404)
    for existing in jukebox.members:
        if existing.user_id == user.id:
            raise AppError(
                "ya eres miembro de este jukebox", code="already_member", status_code=409
            )
    jukebox.members.append(JukeboxMember(user_id=user.id, role=Role.MEMBER.value))
    await db.commit()
    await db.refresh(jukebox)
    return JukeboxOut(
        id=jukebox.id,
        name=jukebox.name,
        description=jukebox.description,
        owner_id=jukebox.owner_id,
        invite_code=jukebox.invite_code,
        is_active=jukebox.is_active,
        created_at=jukebox.created_at,
        role=Role.MEMBER.value,
        member_count=len(jukebox.members),
    )


async def list_members(db: AsyncSession, jukebox_id: int) -> list[MemberOut]:
    members = (
        (
            await db.execute(
                select(JukeboxMember)
                .where(JukeboxMember.jukebox_id == jukebox_id)
                .options(selectinload(JukeboxMember.user).selectinload(User.profile))
            )
        )
        .scalars()
        .all()
    )
    return [
        MemberOut(
            user_id=member.user_id,
            role=member.role,
            display_name=member.user.profile.display_name if member.user.profile else "",
        )
        for member in members
    ]


async def _count_admins(db: AsyncSession, jukebox_id: int) -> int:
    total = (
        await db.execute(
            select(func.count())
            .select_from(JukeboxMember)
            .where(
                JukeboxMember.jukebox_id == jukebox_id,
                JukeboxMember.role == Role.ADMIN.value,
            )
        )
    ).scalar_one()
    return int(total)


async def set_member_role(
    db: AsyncSession,
    actor: JukeboxMember,
    jukebox_id: int,
    target_user_id: int,
    new_role: Role,
) -> MemberOut:
    # El route ya exige que `actor` sea ADMIN (require_role); con solo dos
    # roles, cualquier ADMIN administra a cualquier otro miembro. La única
    # red de seguridad es no dejar la jukebox sin ningún ADMIN.
    target = (
        await db.execute(
            select(JukeboxMember)
            .where(
                JukeboxMember.jukebox_id == jukebox_id,
                JukeboxMember.user_id == target_user_id,
            )
            .options(selectinload(JukeboxMember.user).selectinload(User.profile))
        )
    ).scalar_one_or_none()
    if target is None:
        raise AppError("el usuario no es miembro", code="member_not_found", status_code=404)

    if (
        Role(target.role) is Role.ADMIN
        and new_role is Role.MEMBER
        and await _count_admins(db, jukebox_id) <= 1
    ):
        raise AppError(
            "la jukebox se quedaría sin ningún admin", code="last_admin", status_code=409
        )

    target.role = new_role.value
    await db.commit()
    return MemberOut(
        user_id=target.user_id,
        role=target.role,
        display_name=_display(target),
    )


def _display(member: JukeboxMember) -> str:
    if member.user and member.user.profile:
        return member.user.profile.display_name
    return ""


async def remove_member(
    db: AsyncSession, actor: JukeboxMember, jukebox_id: int, target_user_id: int
) -> None:
    target = (
        await db.execute(
            select(JukeboxMember).where(
                JukeboxMember.jukebox_id == jukebox_id,
                JukeboxMember.user_id == target_user_id,
            )
        )
    ).scalar_one_or_none()
    if target is None:
        raise AppError("el usuario no es miembro", code="member_not_found", status_code=404)

    if Role(target.role) is Role.ADMIN and await _count_admins(db, jukebox_id) <= 1:
        raise AppError(
            "la jukebox se quedaría sin ningún admin", code="last_admin", status_code=409
        )
    await db.delete(target)
    await db.commit()
