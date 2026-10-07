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

ADMIN_EMAIL = "admin@chomelo.dev"
MEMBER_EMAILS = ["member1@chomelo.dev", "member2@chomelo.dev"]
PASSWORD = "chomelo1234"
JUKEBOX_NAME = "Jukebox de Prueba"
SEED_CREDITS = 20


async def _get_or_create_user(db, email: str, display_name: str) -> User:
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        return existing
    return await register_user(
        db, RegisterRequest(email=email, password=PASSWORD, display_name=display_name)
    )


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
        admin = await _get_or_create_user(db, ADMIN_EMAIL, "Admin")
        jukebox = await _get_or_create_jukebox(db, admin)

        members = [await _get_or_create_user(db, e, f"Oyente {i}") for i, e in enumerate(MEMBER_EMAILS, start=1)]
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

        print(f"Admin:   {ADMIN_EMAIL} / {PASSWORD}")
        for email in MEMBER_EMAILS:
            print(f"Miembro: {email} / {PASSWORD}")
        print(f"Jukebox: {jukebox.name} (código: {jukebox.invite_code})")


if __name__ == "__main__":
    asyncio.run(main())
