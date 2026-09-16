from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession


def dialect_insert(db: AsyncSession, model):
    """Insert dialect-specific para usar ON CONFLICT DO NOTHING (SQLite y Postgres)."""
    if db.get_bind().dialect.name == "postgresql":
        return pg_insert(model)
    return sqlite_insert(model)
