"""0022 queue item credits spent (coste de añadir reembolsable)

Revision ID: 0022_queue_item_credits_spent
Revises: 0021_wompi_min_price
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0022_queue_item_credits_spent"
down_revision: Union[str, None] = "0021_wompi_min_price"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "queue_items",
        sa.Column("credits_spent", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("queue_items", "credits_spent")
