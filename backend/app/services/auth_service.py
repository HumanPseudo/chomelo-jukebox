from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_version,
    verify_password,
)
from app.domain.jukebox import Jukebox, JukeboxMember, Role
from app.domain.user import Profile, User
from app.infra.rate_limit import is_rate_limited


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    existing = (
        await db.execute(select(User).where(User.phone_number == payload.phone_number))
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError("el teléfono ya está registrado", code="phone_taken", status_code=409)

    user = User(phone_number=payload.phone_number, password_hash=hash_password(payload.password))
    display_name = payload.display_name or payload.phone_number
    user.profile = Profile(display_name=display_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    default_jb = (
        await db.execute(
            select(Jukebox).where(Jukebox.name == "Jukebox").order_by(Jukebox.id).limit(1)
        )
    ).scalar_one_or_none()
    if default_jb is None:
        default_jb = (
            await db.execute(select(Jukebox).order_by(Jukebox.id).limit(1))
        ).scalar_one_or_none()
    if default_jb is not None:
        already = (
            await db.execute(
                select(JukeboxMember).where(
                    JukeboxMember.jukebox_id == default_jb.id,
                    JukeboxMember.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if already is None:
            db.add(JukeboxMember(jukebox_id=default_jb.id, user_id=user.id, role=Role.MEMBER.value))
            await db.commit()
    return user


async def authenticate(db: AsyncSession, payload: LoginRequest, client_ip: str | None) -> User:
    identifier = payload.identifier or payload.email or payload.phone_number
    if "@" in (identifier or ""):
        lookup = User.email == identifier
    else:
        lookup = User.phone_number == identifier
    if await is_rate_limited(
        f"login:{identifier}", limit=settings.jwt_expire_minutes, window=60
    ):
        raise AppError(
            "demasiados intentos, espera un momento",
            code="rate_limited",
            status_code=429,
        )
    if client_ip and await is_rate_limited(
        f"login_ip:{client_ip}",
        limit=settings.login_rate_limit_per_ip,
        window=settings.login_rate_limit_window,
    ):
        raise AppError(
            "demasiados intentos, espera un momento",
            code="rate_limited",
            status_code=429,
        )

    user = (await db.execute(select(User).where(lookup))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("credenciales inválidas", code="invalid_credentials", status_code=401)
    if not user.is_active:
        raise AppError("usuario inactivo", code="user_inactive", status_code=403)

    membership_exists = (
        await db.execute(
            select(JukeboxMember).where(JukeboxMember.user_id == user.id).limit(1)
        )
    ).scalar_one_or_none()
    if membership_exists is None:
        default_jb = (
            await db.execute(
                select(Jukebox).where(Jukebox.name == "Jukebox").order_by(Jukebox.id).limit(1)
            )
        ).scalar_one_or_none()
        if default_jb is None:
            default_jb = (
                await db.execute(select(Jukebox).order_by(Jukebox.id).limit(1))
            ).scalar_one_or_none()
        if default_jb is not None:
            db.add(JukeboxMember(jukebox_id=default_jb.id, user_id=user.id, role=Role.MEMBER.value))
            await db.commit()
    return user


async def refresh_user(db: AsyncSession, refresh_token: str) -> User:
    try:
        payload = decode_token(refresh_token)
    except JWTError as exc:
        raise AppError(
            "token de refresco inválido o expirado",
            code="auth_invalid",
            status_code=401,
        ) from exc
    if payload.get("type") != "refresh":
        raise AppError("token de refresco inválido", code="auth_invalid", status_code=401)
    try:
        user_id = int(payload.get("sub", "0"))
    except ValueError as exc:
        raise AppError("token de refresco inválido", code="auth_invalid", status_code=401) from exc
    user = (
        await db.execute(select(User).where(User.id == user_id).with_for_update())
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise AppError("usuario no encontrado", code="auth_invalid", status_code=401)
    if token_version(payload) != user.token_version:
        raise AppError("token de refresco revocado", code="auth_invalid", status_code=401)
    user.token_version += 1
    return user


def issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.token_version),
        refresh_token=create_refresh_token(str(user.id), user.token_version),
        expires_in=settings.jwt_expire_minutes * 60,
    )
