"""games tables

Revision ID: 0007_games
Revises: 0006_profile_xp
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_games"
down_revision: Union[str, None] = "0006_profile_xp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jukebox_id", sa.Integer(), nullable=False),
        sa.Column("game_key", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("artist", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
            ["jukebox_id"],
            ["jukeboxes.id"],
            name="fk_game_rounds_jukebox_id_jukeboxes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_game_rounds_created_by_users",
        ),
    )
    op.create_index("ix_game_rounds_jukebox_id", "game_rounds", ["jukebox_id"])

    op.create_table(
        "game_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("selected", sa.String(length=300), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
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
            ["round_id"],
            ["game_rounds.id"],
            name="fk_game_attempts_round_id_game_rounds",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_game_attempts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("round_id", "user_id", name="uq_game_attempts_round_user"),
    )
    op.create_index("ix_game_attempts_round_id", "game_attempts", ["round_id"])


def downgrade() -> None:
    op.drop_table("game_attempts")
    op.drop_table("game_rounds")
