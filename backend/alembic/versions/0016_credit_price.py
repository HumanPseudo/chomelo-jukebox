"""add credit_price_cents to jukeboxes

Revision ID: 0016_credit_price
Revises: 0015_boost_cost
Create Date: 2026-11-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_credit_price"
down_revision: Union[str, None] = "0015_boost_cost"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jukeboxes",
        sa.Column("credit_price_cents", sa.Integer(), nullable=False, server_default="10"),
    )


def downgrade() -> None:
    op.drop_column("jukeboxes", "credit_price_cents")
