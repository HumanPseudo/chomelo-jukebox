"""polls tables

Revision ID: 0005_polls
Revises: 0004_votes
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_polls"
down_revision: Union[str, None] = "0004_votes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "polls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jukebox_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_polls_jukebox_id_jukeboxes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_polls_created_by_users",
        ),
    )
    op.create_index("ix_polls_jukebox_id", "polls", ["jukebox_id"])

    op.create_table(
        "poll_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=200), nullable=False),
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
            ["poll_id"],
            ["polls.id"],
            name="fk_poll_options_poll_id_polls",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_poll_options_poll_id", "poll_options", ["poll_id"])

    op.create_table(
        "poll_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
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
            ["poll_id"],
            ["polls.id"],
            name="fk_poll_votes_poll_id_polls",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["option_id"],
            ["poll_options.id"],
            name="fk_poll_votes_option_id_poll_options",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_poll_votes_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("poll_id", "user_id", name="uq_poll_votes_poll_user"),
        sa.UniqueConstraint(
            "poll_id", "option_id", "user_id", name="uq_poll_votes_poll_option_user"
        ),
    )
    op.create_index("ix_poll_votes_poll_id", "poll_votes", ["poll_id"])


def downgrade() -> None:
    op.drop_table("poll_votes")
    op.drop_table("poll_options")
    op.drop_table("polls")
