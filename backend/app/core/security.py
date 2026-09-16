from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import Depends, Header
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import get_db
from app.domain.user import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(subject, "access", timedelta(minutes=settings.jwt_expire_minutes))


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, "refresh", timedelta(days=settings.jwt_refresh_expire_days))


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("autenticación requerida", code="auth_missing", status_code=401)
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise AppError("token inválido o expirado", code="auth_invalid", status_code=401) from exc
    if payload.get("type") != "access":
        raise AppError("token no válido para esta operación", code="auth_invalid", status_code=401)
    try:
        user_id = int(payload.get("sub", "0"))
    except ValueError as exc:
        raise AppError("token inválido", code="auth_invalid", status_code=401) from exc
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("usuario no encontrado", code="auth_invalid", status_code=401)
    return user
