"""0011 queue item boost (impulso pagado con créditos)

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_boost"
down_revision = "0010_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "queue_items",
        sa.Column("boost", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("queue_items", "boost")
