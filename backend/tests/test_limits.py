import pytest
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.domain.jukebox import Jukebox, JukeboxMember, Role
from app.domain.queue import QueueItem, QueueStatus
from app.domain.user import Profile, User
from app.domain.vote import Vote
from app.services import queue_service, vote_service, wallet_service


async def _setup(db):
    owner = User(
        phone_number="+573001000001",
        password_hash="hash",
        profile=Profile(display_name="Owner"),
    )
    listener = User(
        phone_number="+573001000002",
        password_hash="hash",
        profile=Profile(display_name="Listener"),
    )
    db.add_all([owner, listener])
    await db.flush()
    jukebox = Jukebox(name="Limites", owner_id=owner.id, invite_code="LIMITS")
    db.add(jukebox)
    await db.flush()
    admin = JukeboxMember(
        jukebox_id=jukebox.id, user_id=owner.id, role=Role.ADMIN.value
    )
    member = JukeboxMember(
        jukebox_id=jukebox.id, user_id=listener.id, role=Role.MEMBER.value
    )
    db.add_all([admin, member])
    first = QueueItem(
        jukebox_id=jukebox.id,
        track_id="first",
        title="First",
        artist="A",
        added_by=owner.id,
        status=QueueStatus.QUEUED.value,
        position=0,
    )
    second = QueueItem(
        jukebox_id=jukebox.id,
        track_id="second",
        title="Second",
        artist="B",
        added_by=owner.id,
        status=QueueStatus.QUEUED.value,
        position=1,
    )
    db.add_all([first, second])
    await wallet_service.credit(
        db, owner.id, 10, idempotency_key="setup_limits_wallet", kind="bonus"
    )
    await db.commit()
    return admin, member, owner, first, second


@pytest.mark.asyncio
async def test_boost_is_limited_to_once_per_user_and_item(db_session):
    admin, _member, owner, _first, second = await _setup(db_session)

    boosted = await queue_service.boost_item(db_session, admin, second.id, 1)
    assert boosted.boost == 1

    with pytest.raises(AppError) as exc:
        await queue_service.boost_item(db_session, admin, second.id, 1)
    assert exc.value.code == "already_boosted"
    assert await wallet_service.balance(db_session, owner.id) == 9


@pytest.mark.asyncio
async def test_vote_is_limited_to_once_per_user(db_session):
    _admin, member, _owner, first, second = await _setup(db_session)

    await vote_service.cast_vote(db_session, member, first.id)

    with pytest.raises(AppError) as exc:
        await vote_service.cast_vote(db_session, member, second.id)
    assert exc.value.code == "already_voted"

    with pytest.raises(AppError) as exc:
        await vote_service.remove_vote(db_session, member, first.id)
    assert exc.value.code == "vote_locked"

    votes = (
        await db_session.execute(select(Vote).where(Vote.user_id == member.user_id))
    ).scalars().all()
    assert len(votes) == 1
    assert votes[0].queue_item_id == first.id
    assert (
        await db_session.execute(select(func.count()).select_from(Vote))
    ).scalar_one() == 1
