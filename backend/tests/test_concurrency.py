"""Fase 14 — Tests de concurrencia.

Estos tests corren contra un Postgres real (Testcontainers), no el SQLite en
memoria del resto de la suite: solo Postgres tiene semántica real de
`SELECT ... FOR UPDATE` y de bloqueo en `INSERT ... ON CONFLICT`, que es
justo lo que hay que verificar bajo concurrencia real (asyncio.gather con
sesiones/conexiones independientes, como si fueran requests distintas).
"""

from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.core.exceptions import AppError
from app.db.base import Base
from app.domain.game import GameAttempt, GameRound, GameStatus
from app.domain.jukebox import Jukebox, JukeboxMember, Role
from app.domain.payment import Payment, PaymentEvent, PaymentStatus
from app.domain.queue import QueueItem, QueueStatus
from app.domain.user import User
from app.domain.vote import Vote
from app.domain.wallet import Wallet, WalletTransaction
from app.providers.payments import PaymentProvider, ProviderEvent
from app.services import game_service, payment_service, vote_service, wallet_service


@pytest.fixture(scope="module")
def pg_url():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg")


@pytest_asyncio.fixture
async def sessionmaker(pg_url):
    engine = create_async_engine(pg_url, pool_size=20, max_overflow=0)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _make_user(db: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash="x", is_active=True)
    db.add(user)
    await db.flush()
    return user


async def _make_jukebox(db: AsyncSession, owner: User) -> Jukebox:
    jb = Jukebox(name="Concurrency", owner_id=owner.id, invite_code=secrets.token_hex(3).upper())
    db.add(jb)
    await db.flush()
    db.add(JukeboxMember(jukebox_id=jb.id, user_id=owner.id, role=Role.ADMIN.value))
    await db.flush()
    return jb


async def _add_member(db: AsyncSession, jukebox_id: int, user_id: int) -> JukeboxMember:
    member = JukeboxMember(jukebox_id=jukebox_id, user_id=user_id, role=Role.MEMBER.value)
    db.add(member)
    await db.flush()
    return member


async def _add_queue_item(
    db: AsyncSession, jukebox_id: int, added_by: int, track_id: str
) -> QueueItem:
    item = QueueItem(
        jukebox_id=jukebox_id,
        track_id=track_id,
        title=track_id,
        added_by=added_by,
        status=QueueStatus.QUEUED.value,
    )
    db.add(item)
    await db.flush()
    return item


async def test_concurrent_votes_same_user_never_exceeds_one(sessionmaker):
    async with sessionmaker() as setup:
        owner = await _make_user(setup, "owner@conc.test")
        jb = await _make_jukebox(setup, owner)
        voter = await _make_user(setup, "voter@conc.test")
        member = await _add_member(setup, jb.id, voter.id)
        item_a = await _add_queue_item(setup, jb.id, owner.id, "track-a")
        item_b = await _add_queue_item(setup, jb.id, owner.id, "track-b")
        await setup.commit()
        member_id, item_a_id, item_b_id, jb_id, user_id = (
            member.id,
            item_a.id,
            item_b.id,
            jb.id,
            voter.id,
        )

    async def _vote(item_id: int):
        async with sessionmaker() as db:
            actor = await db.get(JukeboxMember, member_id)
            await vote_service.cast_vote(db, actor, item_id)

    results = await asyncio.gather(_vote(item_a_id), _vote(item_b_id), return_exceptions=True)

    async with sessionmaker() as check:
        votes = (
            (
                await check.execute(
                    select(Vote).where(Vote.jukebox_id == jb_id, Vote.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )

    # Regla dura #8 (UNIQUE(jukebox_id, user_id)): pase lo que pase con el
    # interleaving, el usuario nunca termina con más de un voto.
    assert len(votes) == 1
    assert votes[0].queue_item_id in (item_a_id, item_b_id)
    # Si hubo carrera real, una de las dos llamadas pudo fallar con un error
    # de integridad; nunca deberían fallar ambas.
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(failures) <= 1


async def test_concurrent_wallet_credit_same_idempotency_key_applies_once(sessionmaker):
    async with sessionmaker() as setup:
        user = await _make_user(setup, "credit@conc.test")
        await setup.commit()
        user_id = user.id

    async def _credit():
        async with sessionmaker() as db:
            await wallet_service.credit(
                db,
                user_id,
                50,
                idempotency_key="bonus:welcome",
                kind="bonus",
                description="bienvenida",
            )
            await db.commit()

    await asyncio.gather(*[_credit() for _ in range(8)])

    async with sessionmaker() as check:
        wallet = (await check.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one()
        txs = (
            (
                await check.execute(
                    select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.id)
                )
            )
            .scalars()
            .all()
        )

    assert wallet.credits == 50
    assert len(txs) == 1


async def test_concurrent_wallet_debits_never_overdraw(sessionmaker):
    async with sessionmaker() as setup:
        user = await _make_user(setup, "debit@conc.test")
        await setup.commit()
        user_id = user.id

    async with sessionmaker() as db:
        await wallet_service.credit(
            db, user_id, 100, idempotency_key="seed", kind="bonus", description="seed"
        )
        await db.commit()

    async def _debit(n: int):
        async with sessionmaker() as db:
            await wallet_service.debit(
                db,
                user_id,
                30,
                idempotency_key=f"spend:{n}",
                kind="spend",
                description="compra",
            )
            await db.commit()

    results = await asyncio.gather(*[_debit(n) for n in range(5)], return_exceptions=True)

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, AppError)]

    async with sessionmaker() as check:
        wallet = (await check.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one()

    # 100 // 30 == 3: el lock FOR UPDATE serializa los débitos, así que el
    # resultado es determinista pase lo que pase con el orden de llegada.
    assert len(successes) == 3
    assert len(failures) == 2
    assert all(f.code == "insufficient_balance" for f in failures)
    assert wallet.credits == 10
    assert wallet.credits >= 0


class _DuplicateWebhookProvider(PaymentProvider):
    key = "fake"

    def __init__(self, session_id: str, event_id: str) -> None:
        self.session_id = session_id
        self.event_id = event_id

    async def create_checkout(self, **kwargs):  # pragma: no cover - no usado aquí
        raise NotImplementedError

    async def verify_event(self, payload: bytes, signature: str) -> ProviderEvent:
        return ProviderEvent(
            event_id=self.event_id,
            event_type="checkout.session.completed",
            checkout_session_id=self.session_id,
            paid=True,
            amount_cents=1000,
            currency="eur",
            raw={},
        )


async def test_concurrent_duplicate_webhook_grants_credits_once(sessionmaker):
    async with sessionmaker() as setup:
        user = await _make_user(setup, "payer@conc.test")
        payment = Payment(
            user_id=user.id,
            provider="fake",
            provider_session_id="cs_dup_1",
            credits=200,
            amount_cents=1000,
            currency="eur",
            status=PaymentStatus.PENDING.value,
        )
        setup.add(payment)
        await setup.commit()
        user_id = user.id

    provider = _DuplicateWebhookProvider(session_id="cs_dup_1", event_id="evt_dup_1")

    async def _deliver():
        async with sessionmaker() as db:
            return await payment_service.consume_webhook(db, provider, b"{}", "any-sig")

    results = await asyncio.gather(_deliver(), _deliver(), return_exceptions=True)

    # La segunda entrega del mismo evento nunca debe reventar con un error
    # de integridad sin manejar; ambas deben devolver una respuesta normal.
    assert all(not isinstance(r, Exception) for r in results)
    assert sum(1 for r in results if r.get("duplicate")) == 1

    async with sessionmaker() as check:
        wallet = (await check.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one()
        events = (
            (
                await check.execute(
                    select(PaymentEvent).where(PaymentEvent.provider_event_id == "evt_dup_1")
                )
            )
            .scalars()
            .all()
        )

    assert wallet.credits == 200
    assert len(events) == 1


async def test_concurrent_correct_answers_only_first_wins(sessionmaker):
    async with sessionmaker() as setup:
        owner = await _make_user(setup, "gowner@conc.test")
        jb = await _make_jukebox(setup, owner)
        u1 = await _make_user(setup, "player1@conc.test")
        u2 = await _make_user(setup, "player2@conc.test")
        m1 = await _add_member(setup, jb.id, u1.id)
        m2 = await _add_member(setup, jb.id, u2.id)
        now = datetime.now(UTC)
        round_ = GameRound(
            jukebox_id=jb.id,
            game_key="guess_the_song",
            created_by=owner.id,
            track_id="t1",
            title="Correct Song",
            artist="Someone",
            options=["Correct Song", "A", "B", "C"],
            status=GameStatus.OPEN.value,
            starts_at=now,
            expires_at=now + timedelta(seconds=60),
        )
        setup.add(round_)
        await setup.flush()
        await setup.commit()
        m1_id, m2_id, round_id = m1.id, m2.id, round_.id

    async def _answer(member_id: int):
        async with sessionmaker() as db:
            actor = await db.get(JukeboxMember, member_id)
            return await game_service.guess(
                db, actor, "guess_the_song", round_id, "Correct Song", datetime.now(UTC)
            )

    results = await asyncio.gather(_answer(m1_id), _answer(m2_id), return_exceptions=True)

    async with sessionmaker() as check:
        round_after = await check.get(GameRound, round_id)
        correct_attempts = (
            (
                await check.execute(
                    select(GameAttempt).where(
                        GameAttempt.round_id == round_id, GameAttempt.correct.is_(True)
                    )
                )
            )
            .scalars()
            .all()
        )
        rewards = (
            (
                await check.execute(
                    select(WalletTransaction).where(WalletTransaction.kind == "game_win")
                )
            )
            .scalars()
            .all()
        )

    # "Primer acierto gana" (regla de Fase 9): el lock FOR UPDATE en la ronda
    # impide que dos respuestas correctas simultáneas cierren la ronda y
    # cobren la recompensa las dos.
    assert round_after.status == GameStatus.FINISHED.value
    assert len(correct_attempts) == 1
    assert len(rewards) == 1

    non_exceptions = [r for r in results if not isinstance(r, Exception)]
    app_errors = [r for r in results if isinstance(r, AppError)]
    assert len(non_exceptions) == 1
    assert len(app_errors) == 1
    assert app_errors[0].code == "round_finished"
