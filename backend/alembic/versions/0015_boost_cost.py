"""add boost_cost_credits to jukeboxes

Revision ID: 0015_boost_cost
Revises: 0014_track_cooldown
Create Date: 2026-11-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015_boost_cost"
down_revision: Union[str, None] = "0014_track_cooldown"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jukeboxes",
        sa.Column("boost_cost_credits", sa.Integer(), nullable=False, server_default="10"),
    )


def downgrade() -> None:
    op.drop_column("jukeboxes", "boost_cost_credits")
