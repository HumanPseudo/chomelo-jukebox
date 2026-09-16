"""queue_items and players tables

Revision ID: 0003_queue
Revises: 0002_jukeboxes
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_queue"
down_revision: Union[str, None] = "0002_jukeboxes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "queue_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jukebox_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("artist", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("added_by", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], name="fk_queue_items_added_by_users"),
        sa.ForeignKeyConstraint(
            ["jukebox_id"],
            ["jukeboxes.id"],
            name="fk_queue_items_jukebox_id_jukeboxes",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_queue_items_jukebox_id", "queue_items", ["jukebox_id"])
    op.create_index("ix_queue_items_status", "queue_items", ["status"])

    op.create_table(
        "players",
        sa.Column("jukebox_id", sa.Integer(), primary_key=True),
        sa.Column("current_item_id", sa.Integer(), nullable=True),
        sa.Column("is_playing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["current_item_id"],
            ["queue_items.id"],
            name="fk_players_current_item_id_queue_items",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["jukebox_id"],
            ["jukeboxes.id"],
            name="fk_players_jukebox_id_jukeboxes",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("players")
    op.drop_table("queue_items")
