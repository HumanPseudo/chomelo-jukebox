"""add token_version to users

Revision ID: 0017_token_version
Revises: 0016_credit_price
Create Date: 2026-11-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_token_version"
down_revision: Union[str, None] = "0016_credit_price"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
