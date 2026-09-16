from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.poll import PollCreate, PollOptionOut, PollOut
from app.core.exceptions import AppError
from app.domain.jukebox import JukeboxMember
from app.domain.poll import Poll, PollOption, PollStatus, PollVote
from app.infra import rate_limit
from app.services import wallet_service, xp_service

POLL_VOTE_RATE_LIMIT = 30
POLL_VOTE_RATE_WINDOW = 60


def _now() -> datetime:
    return datetime.now(UTC)


def _is_past(closes_at: datetime) -> bool:
    naive = closes_at.tzinfo is None
    closes_at = closes_at.replace(tzinfo=UTC) if naive else closes_at
    return closes_at <= _now()


async def _get_poll(db: AsyncSession, jukebox_id: int, poll_id: int) -> Poll:
    poll = await db.get(Poll, poll_id)
    if poll is None or poll.jukebox_id != jukebox_id:
        raise AppError("encuesta no encontrada", code="poll_not_found", status_code=404)
    return poll


async def _auto_close(db: AsyncSession, poll: Poll) -> None:
    if poll.status == PollStatus.OPEN.value and poll.closes_at is not None:
        if _is_past(poll.closes_at):
            poll.status = PollStatus.CLOSED.value
            await db.flush()


async def _counts(db: AsyncSession, poll_id: int) -> dict[int, int]:
    rows = await db.execute(
        select(PollVote.option_id, func.count(PollVote.id))
        .where(PollVote.poll_id == poll_id)
        .group_by(PollVote.option_id)
    )
    return {option_id: total for option_id, total in rows.all()}


async def _my_option(db: AsyncSession, poll_id: int, user_id: int) -> int | None:
    vote = (
        await db.execute(
            select(PollVote.option_id).where(
                PollVote.poll_id == poll_id, PollVote.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    return vote


def _to_out(poll: Poll, counts: dict[int, int], my_option_id: int | None = None) -> PollOut:
    options = [
        PollOptionOut(id=opt.id, text=opt.text, votes=counts.get(opt.id, 0)) for opt in poll.options
    ]
    return PollOut(
        id=poll.id,
        question=poll.question,
        status=poll.status,
        closes_at=poll.closes_at,
        created_at=poll.created_at,
        created_by=poll.created_by,
        options=options,
        my_option_id=my_option_id,
        total_votes=sum(counts.values()),
    )


async def create_poll(db: AsyncSession, member: JukeboxMember, payload: PollCreate) -> PollOut:
    options = payload.clean_options
    if len(options) < 2:
        raise AppError(
            "la encuesta necesita al menos 2 opciones", code="invalid_poll_options", status_code=422
        )
    poll = Poll(
        jukebox_id=member.jukebox_id,
        question=payload.question,
        created_by=member.user_id,
        closes_at=payload.closes_at,
    )
    poll.options = [PollOption(text=text) for text in options]
    db.add(poll)
    await db.flush()
    await xp_service.grant_xp(db, member.user_id, xp_service.CREATE_POLL)
    await wallet_service.credit(
        db,
        member.user_id,
        wallet_service.CREATE_POLL_CREDIT,
        idempotency_key=f"poll_created:{member.user_id}:{poll.id}",
        kind="poll_created",
        description="Creaste una encuesta",
    )
    await db.commit()
    await db.refresh(poll)
    return _to_out(poll, {})


async def list_polls(
    db: AsyncSession, member: JukeboxMember, status: str | None = None
) -> list[PollOut]:
    stmt = select(Poll).where(Poll.jukebox_id == member.jukebox_id).order_by(Poll.id.desc())
    if status is not None:
        stmt = stmt.where(Poll.status == status)
    polls = (await db.execute(stmt)).scalars().all()

    result: list[PollOut] = []
    for poll in polls:
        await _auto_close(db, poll)
        result.append(
            _to_out(poll, await _counts(db, poll.id), await _my_option(db, poll.id, member.user_id))
        )
    if any(p.status == PollStatus.CLOSED.value for p in polls):
        await db.commit()
    return result


async def get_poll(db: AsyncSession, member: JukeboxMember, poll_id: int) -> PollOut:
    poll = await _get_poll(db, member.jukebox_id, poll_id)
    await _auto_close(db, poll)
    await db.commit()
    return _to_out(poll, await _counts(db, poll.id), await _my_option(db, poll.id, member.user_id))


async def close_poll(db: AsyncSession, member: JukeboxMember, poll_id: int) -> PollOut:
    poll = await _get_poll(db, member.jukebox_id, poll_id)
    poll.status = PollStatus.CLOSED.value
    await db.commit()
    await db.refresh(poll)
    return _to_out(poll, await _counts(db, poll.id), await _my_option(db, poll.id, member.user_id))


async def delete_poll(db: AsyncSession, member: JukeboxMember, poll_id: int) -> None:
    poll = await _get_poll(db, member.jukebox_id, poll_id)
    await db.delete(poll)
    await db.commit()


async def cast_vote(db: AsyncSession, member: JukeboxMember, poll_id: int, option_id: int) -> None:
    if await rate_limit.is_rate_limited(
        f"poll:{member.user_id}:{member.jukebox_id}",
        limit=POLL_VOTE_RATE_LIMIT,
        window=POLL_VOTE_RATE_WINDOW,
    ):
        raise AppError(
            "demasiados votos en encuestas, espera un momento", code="rate_limited", status_code=429
        )

    poll = await _get_poll(db, member.jukebox_id, poll_id)
    await _auto_close(db, poll)
    if poll.status != PollStatus.OPEN.value:
        raise AppError("la encuesta está cerrada", code="poll_closed", status_code=409)

    option = await db.get(PollOption, option_id)
    if option is None or option.poll_id != poll.id:
        raise AppError("opción no encontrada", code="poll_option_not_found", status_code=404)

    existing = (
        await db.execute(
            select(PollVote).where(PollVote.poll_id == poll.id, PollVote.user_id == member.user_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError("ya votaste en esta encuesta", code="poll_already_voted", status_code=409)

    vote = PollVote(poll_id=poll.id, option_id=option_id, user_id=member.user_id)
    db.add(vote)
    await db.flush()
    await xp_service.grant_xp(db, member.user_id, xp_service.POLL_VOTE)
    await wallet_service.credit(
        db,
        member.user_id,
        wallet_service.POLL_VOTE_CREDIT,
        idempotency_key=f"poll_vote:{member.user_id}:{vote.id}",
        kind="poll_vote",
        description="Participaste en una encuesta",
    )
    await db.commit()
