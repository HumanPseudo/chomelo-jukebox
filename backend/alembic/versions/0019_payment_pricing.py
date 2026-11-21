"""add payment pricing row

Revision ID: 0019_payment_pricing
Revises: 0018_offers
Create Date: 2026-11-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0019_payment_pricing"
down_revision: Union[str, None] = "0018_offers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_pricing",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("cents_per_credit", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="cop"),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(
        "INSERT INTO payment_pricing (id, cents_per_credit, currency) "
        "VALUES (1, 10, 'cop')"
    )


def downgrade() -> None:
    op.drop_table("payment_pricing")
