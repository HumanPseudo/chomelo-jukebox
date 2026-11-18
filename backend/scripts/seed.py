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
JUKEBOX_NAME = "Jukebox de Prueba"
SEED_CREDITS = 20


async def _get_or_create_user(db, phone: str, display_name: str, *, is_superuser: bool = False) -> User:
    existing = (await db.execute(select(User).where(User.phone_number == phone))).scalar_one_or_none()
    if existing is not None:
        if is_superuser and not existing.is_superuser:
            existing.is_superuser = True
            await db.commit()
        return existing
    user = await register_user(
        db, RegisterRequest(phone_number=phone, password=PASSWORD, display_name=display_name)
    )
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
        return existing
    out = await jukebox_service.create_jukebox(
        db, admin, JukeboxCreate(name=JUKEBOX_NAME, description="Seed de desarrollo")
    )
    return await db.get(Jukebox, out.id)


async def main() -> None:
    async with SessionLocal() as db:
        admin = await _get_or_create_user(db, ADMIN_PHONE, "Admin", is_superuser=True)
        jukebox = await _get_or_create_jukebox(db, admin)

        members = [await _get_or_create_user(db, p, f"Oyente {i}") for i, p in enumerate(MEMBER_PHONES, start=1)]
        for member in members:
            try:
                await jukebox_service.join_by_code(db, member, jukebox.invite_code)
            except AppError:
                pass  # ya es miembro

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
