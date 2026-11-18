"""Datos básicos de prueba para desarrollo local.

Idempotente: se puede correr varias veces sin duplicar usuarios ni jukeboxes.
No toca queue_items (la cola/lista de canciones) — eso requiere metadata real
del worker de música, no datos falsos.

Uso: docker compose exec backend python -m scripts.seed
"""

import asyncio

from sqlalchemy import select

from app.api.schemas.auth import RegisterRequest
from app.api.schemas.jukebox import JukeboxCreate
from app.core.exceptions import AppError
from app.db.session import SessionLocal
from app.domain.jukebox import Jukebox
from app.domain.user import User
from app.services import jukebox_service, wallet_service
from app.services.auth_service import register_user

ADMIN_PHONE = "+573001234567"
MEMBER_PHONES = ["+573009876543", "+573009876544"]
PASSWORD = "chomelo1234"
JUKEBOX_NAME = "Jukebox"
SEED_CREDITS = 20


async def _get_or_create_user(db, phone: str, display_name: str, *, is_superuser: bool = False, email: str | None = None) -> User:
    conditions = [User.phone_number == phone]
    if email:
        conditions = [User.phone_number == phone, User.email == email]
    from sqlalchemy import or_
    existing = (
        await db.execute(select(User).where(or_(*conditions)).order_by(User.id))
    ).scalars().first()
    if existing is not None:
        if email and existing.email != email:
            from sqlalchemy import update
            await db.execute(update(User).where(User.email == email, User.id != existing.id).values(email=None))
            existing.email = email
        if existing.phone_number != phone:
            # avoid unique conflict: clear phone from any other user
            from sqlalchemy import update
            await db.execute(update(User).where(User.phone_number == phone, User.id != existing.id).values(phone_number=None))
            existing.phone_number = phone
        if is_superuser and not existing.is_superuser:
            existing.is_superuser = True
        await db.commit()
        await db.refresh(existing)
        return existing
    user = await register_user(
        db, RegisterRequest(phone_number=phone, password=PASSWORD, display_name=display_name)
    )
    if email:
        user.email = email
    if is_superuser:
        user.is_superuser = True
    await db.commit()
    await db.refresh(user)
    return user


async def _get_or_create_jukebox(db, admin: User) -> Jukebox:
    existing = (
        await db.execute(select(Jukebox).where(Jukebox.owner_id == admin.id))
    ).scalar_one_or_none()
    if existing is not None:
        if existing.name != JUKEBOX_NAME:
            existing.name = JUKEBOX_NAME
            await db.commit()
            await db.refresh(existing)
        return existing
    out = await jukebox_service.create_jukebox(
        db, admin, JukeboxCreate(name=JUKEBOX_NAME, description="Seed de desarrollo")
    )
    return await db.get(Jukebox, out.id)


async def main() -> None:
    async with SessionLocal() as db:
        admin = await _get_or_create_user(db, ADMIN_PHONE, "Admin", is_superuser=True, email="admin@chomelo.dev")
        if not admin.email:
            admin.email = "admin@chomelo.dev"
            await db.commit()
            await db.refresh(admin)
        jukebox = await _get_or_create_jukebox(db, admin)

        members = [await _get_or_create_user(db, p, f"Oyente {i}") for i, p in enumerate(MEMBER_PHONES, start=1)]
        # Los oyentes ya quedan unidos automáticamente al registrarse.

        for user in [admin, *members]:
            await wallet_service.credit(
                db,
                user.id,
                SEED_CREDITS,
                idempotency_key="seed:welcome",
                kind="seed",
                description="créditos iniciales de prueba",
            )

        await db.commit()

        print(f"Admin:   {ADMIN_PHONE} / {PASSWORD}")
        for phone in MEMBER_PHONES:
            print(f"Miembro: {phone} / {PASSWORD}")
        print(f"Jukebox: {jukebox.name} (código: {jukebox.invite_code})")


if __name__ == "__main__":
    asyncio.run(main())
