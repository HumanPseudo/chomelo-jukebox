from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.game import AttemptOut, MyAttemptOut, RoundOut
from app.core.exceptions import AppError
from app.domain.game import GameAttempt, GameRound, GameStatus
from app.domain.jukebox import JukeboxMember
from app.games import GAMES
from app.infra import rate_limit
from app.infra.events import notify_jukebox
from app.services import wallet_service, xp_service

DEFAULT_DURATION_SECONDS = 60
ROUND_START_RATE_LIMIT = 10
ROUND_START_RATE_WINDOW = 60
MIN_POINTS = 10
MAX_POINTS = 100

VALID_STATUSES = {s.value for s in GameStatus}


def now_utc() -> datetime:
    return datetime.now(UTC)


def _find_game(game_key: str):
    game = GAMES.get(game_key)
    if game is None:
        raise AppError("juego no encontrado", code="game_not_found", status_code=404)
    return game


def _game_name(game_key: str) -> str:
    return GAMES[game_key].name


async def _get_round(db: AsyncSession, jukebox_id: int, round_id: int) -> GameRound:
    round_ = await db.get(GameRound, round_id)
    if round_ is None or round_.jukebox_id != jukebox_id:
        raise AppError("ronda no encontrada", code="round_not_found", status_code=404)
    return round_


async def _get_round_locked(db: AsyncSession, jukebox_id: int, round_id: int) -> GameRound:
    """Como `_get_round` pero con FOR UPDATE: dos jugadores respondiendo a la
    vez no deben poder cerrar la ronda y cobrar la recompensa los dos
    ("primer acierto gana", regla de Fase 9)."""
    round_ = (
        await db.execute(
            select(GameRound)
            .where(GameRound.id == round_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if round_ is None or round_.jukebox_id != jukebox_id:
        raise AppError("ronda no encontrada", code="round_not_found", status_code=404)
    return round_


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def _lazy_finish(db: AsyncSession, round_: GameRound, now: datetime) -> bool:
    if round_.status == GameStatus.OPEN.value and now >= _aware(round_.expires_at):
        round_.status = GameStatus.FINISHED.value
        round_.finished_at = round_.expires_at
        await db.flush()
        return True
    return False


async def _my_attempt(db: AsyncSession, round_id: int, user_id: int) -> MyAttemptOut | None:
    attempt = (
        await db.execute(
            select(GameAttempt).where(
                GameAttempt.round_id == round_id, GameAttempt.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if attempt is None:
        return None
    return MyAttemptOut(selected=attempt.selected, correct=attempt.correct, points=attempt.points)


def _to_out(round_: GameRound, my_attempt: MyAttemptOut | None = None) -> RoundOut:
    finished = round_.status == GameStatus.FINISHED.value
    return RoundOut(
        id=round_.id,
        jukebox_id=round_.jukebox_id,
        game_key=round_.game_key,
        game_name=_game_name(round_.game_key),
        status=round_.status,
        track_id=round_.track_id,
        artist=round_.artist,
        thumbnail_url=round_.thumbnail_url,
        options=round_.options,
        starts_at=round_.starts_at,
        expires_at=round_.expires_at,
        finished_at=round_.finished_at,
        created_by=round_.created_by,
        my_attempt=my_attempt,
        correct_title=round_.title if finished else None,
    )


async def start_round(
    db: AsyncSession,
    member: JukeboxMember,
    game_key: str,
    duration_seconds: int | None,
    now: datetime,
) -> RoundOut:
    if await rate_limit.is_rate_limited(
        f"game:{member.user_id}:{member.jukebox_id}",
        limit=ROUND_START_RATE_LIMIT,
        window=ROUND_START_RATE_WINDOW,
    ):
        raise AppError(
            "demasiadas rondas seguidas, espera un momento", code="rate_limited", status_code=429
        )

    game = _find_game(game_key)
    open_round = (
        await db.execute(
            select(GameRound.id)
            .where(
                GameRound.jukebox_id == member.jukebox_id,
                GameRound.game_key == game.key,
                GameRound.status == GameStatus.OPEN.value,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if open_round is not None:
        raise AppError("ya hay una ronda en curso", code="round_in_progress", status_code=409)

    data = await game.build(db, member.jukebox_id, now)
    duration = duration_seconds if duration_seconds is not None else DEFAULT_DURATION_SECONDS
    round_ = GameRound(
        jukebox_id=member.jukebox_id,
        game_key=game.key,
        created_by=member.user_id,
        track_id=data.track_id,
        title=data.title,
        artist=data.artist,
        thumbnail_url=data.thumbnail_url,
        options=data.options,
        starts_at=now,
        expires_at=now + timedelta(seconds=duration),
    )
    db.add(round_)
    await db.commit()
    await db.refresh(round_)
    await notify_jukebox(member.jukebox_id, "game.updated", round_id=round_.id)
    return _to_out(round_)


async def list_rounds(
    db: AsyncSession,
    member: JukeboxMember,
    game_key: str,
    status: str | None,
    now: datetime,
) -> list[RoundOut]:
    game = _find_game(game_key)
    stmt = (
        select(GameRound)
        .where(GameRound.jukebox_id == member.jukebox_id, GameRound.game_key == game.key)
        .order_by(GameRound.id.desc())
    )
    if status is not None:
        if status not in VALID_STATUSES:
            raise AppError("estado inválido", code="invalid_status", status_code=422)
        stmt = stmt.where(GameRound.status == status)
    rounds = (await db.execute(stmt)).scalars().all()

    result: list[RoundOut] = []
    changed_ids: list[int] = []
    for round_ in rounds:
        if await _lazy_finish(db, round_, now):
            changed_ids.append(round_.id)
        result.append(_to_out(round_, await _my_attempt(db, round_.id, member.user_id)))
    if changed_ids:
        await db.commit()
        for rid in changed_ids:
            await notify_jukebox(member.jukebox_id, "game.updated", round_id=rid)
    return result


async def get_round(
    db: AsyncSession, member: JukeboxMember, game_key: str, round_id: int, now: datetime
) -> RoundOut:
    game = _find_game(game_key)
    round_ = await _get_round(db, member.jukebox_id, round_id)
    if round_.game_key != game.key:
        raise AppError("ronda no encontrada", code="round_not_found", status_code=404)
    changed = await _lazy_finish(db, round_, now)
    await db.commit()
    if changed:
        await notify_jukebox(member.jukebox_id, "game.updated", round_id=round_.id)
    return _to_out(round_, await _my_attempt(db, round_.id, member.user_id))


async def guess(
    db: AsyncSession,
    member: JukeboxMember,
    game_key: str,
    round_id: int,
    selected: str,
    now: datetime,
) -> AttemptOut:
    game = _find_game(game_key)
    round_ = await _get_round_locked(db, member.jukebox_id, round_id)
    if round_.game_key != game.key:
        raise AppError("ronda no encontrada", code="round_not_found", status_code=404)

    changed = await _lazy_finish(db, round_, now)
    if round_.status != GameStatus.OPEN.value:
        await db.commit()
        if changed:
            await notify_jukebox(member.jukebox_id, "game.updated", round_id=round_.id)
        raise AppError("la ronda ya terminó", code="round_finished", status_code=409)

    existing = (
        await db.execute(
            select(GameAttempt).where(
                GameAttempt.round_id == round_.id, GameAttempt.user_id == member.user_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError("ya respondiste en esta ronda", code="already_answered", status_code=409)

    selected = selected.strip()
    if selected not in round_.options:
        raise AppError("opción no disponible en la ronda", code="invalid_guess", status_code=422)

    correct = game.grade(round_, selected)
    points = 0
    if correct:
        elapsed = max(0, (now - _aware(round_.starts_at)).total_seconds())
        points = max(MIN_POINTS, MAX_POINTS - int(elapsed * 2))
        round_.status = GameStatus.FINISHED.value
        round_.finished_at = now

    db.add(
        GameAttempt(
            round_id=round_.id,
            user_id=member.user_id,
            selected=selected,
            correct=correct,
            points=points,
        )
    )
    if correct:
        await xp_service.grant_xp(db, member.user_id, points)
        await wallet_service.credit(
            db,
            member.user_id,
            points,
            idempotency_key=f"game_win:{member.user_id}:{round_.id}",
            kind="game_win",
            description="Ganaste la ronda de Guess the Song",
        )

    await db.commit()
    await notify_jukebox(member.jukebox_id, "game.updated", round_id=round_.id)

    return AttemptOut(
        round_id=round_.id,
        selected=selected,
        correct=correct,
        points=points,
        correct_title=round_.title if correct else None,
        round_status=round_.status,
    )
