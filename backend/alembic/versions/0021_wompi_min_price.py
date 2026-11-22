"""raise default credit price for Wompi minimum

Revision ID: 0021_wompi_min_price
Revises: 0020_credit_amounts
Create Date: 2026-11-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0021_wompi_min_price"
down_revision: Union[str, None] = "0020_credit_amounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE payment_pricing SET cents_per_credit = 1500 WHERE id = 1")
    op.execute(
        "INSERT INTO payment_pricing (id, cents_per_credit, currency, credit_amounts) "
        "SELECT 1, 1500, 'cop', '[100, 500, 1000]' "
        "WHERE NOT EXISTS (SELECT 1 FROM payment_pricing WHERE id = 1)"
    )


def downgrade() -> None:
    op.execute("UPDATE payment_pricing SET cents_per_credit = 10 WHERE id = 1")
