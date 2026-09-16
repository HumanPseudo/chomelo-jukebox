"""votes table

Revision ID: 0004_votes
Revises: 0003_queue
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_votes"
down_revision: Union[str, None] = "0003_queue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jukebox_id", sa.Integer(), nullable=False),
        sa.Column("queue_item_id", sa.Integer(), nullable=False),
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
            ["jukebox_id"],
            ["jukeboxes.id"],
            name="fk_votes_jukebox_id_jukeboxes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["queue_item_id"],
            ["queue_items.id"],
            name="fk_votes_queue_item_id_queue_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_votes_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("queue_item_id", "user_id", name="uq_votes_item_user"),
        sa.UniqueConstraint("jukebox_id", "user_id", name="uq_votes_jukebox_user"),
    )
    op.create_index("ix_votes_jukebox_id", "votes", ["jukebox_id"])


def downgrade() -> None:
    op.drop_table("votes")
