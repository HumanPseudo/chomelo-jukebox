"""add add_track cooldown/cost to jukeboxes

Revision ID: 0014_track_cooldown
Revises: 0013_phone_number
Create Date: 2026-11-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014_track_cooldown"
down_revision: Union[str, None] = "0013_phone_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jukeboxes",
        sa.Column("add_track_cooldown_seconds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "jukeboxes",
        sa.Column("add_track_cost_credits", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_column("jukeboxes", "add_track_cost_credits")
    op.drop_column("jukeboxes", "add_track_cooldown_seconds")
