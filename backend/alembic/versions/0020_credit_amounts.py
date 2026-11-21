"""add credit amounts to payment pricing

Revision ID: 0020_credit_amounts
Revises: 0019_payment_pricing
Create Date: 2026-11-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0020_credit_amounts"
down_revision: Union[str, None] = "0019_payment_pricing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_pricing",
        sa.Column(
            "credit_amounts",
            sa.JSON(),
            nullable=False,
            server_default="[100, 500, 1000]",
        ),
    )


def downgrade() -> None:
    op.drop_column("payment_pricing", "credit_amounts")
