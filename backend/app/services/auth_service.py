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
    verify_password,
)
from app.domain.user import Profile, User
from app.infra.rate_limit import is_rate_limited


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError("el email ya está registrado", code="email_taken", status_code=409)

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    display_name = payload.display_name or payload.email.split("@")[0]
    user.profile = Profile(display_name=display_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, payload: LoginRequest, client_ip: str | None) -> User:
    if await is_rate_limited(
        f"login:{payload.email}", limit=settings.jwt_expire_minutes, window=60
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

    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("credenciales inválidas", code="invalid_credentials", status_code=401)
    if not user.is_active:
        raise AppError("usuario inactivo", code="user_inactive", status_code=403)
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
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("usuario no encontrado", code="auth_invalid", status_code=401)
    return user


def issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.jwt_expire_minutes * 60,
    )
