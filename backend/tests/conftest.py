from __future__ import annotations

import os

os.environ.setdefault("CHOMELO_DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("CHOMELO_REDIS_URL", "redis://127.0.0.1:1/0")

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_clock, get_music_provider
from app.db.base import Base
from app.db.session import get_db
from app.main import app

_test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = async_sessionmaker(_test_engine, expire_on_commit=False)


async def _get_test_db():
    async with _TestSession() as session:
        yield session


@pytest_asyncio.fixture(autouse=True, scope="function")
async def _reset_db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides.pop(get_music_provider, None)
    app.dependency_overrides.pop(get_clock, None)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with _TestSession() as session:
        yield session


app.dependency_overrides[get_db] = _get_test_db
