"""profiles bio and xp columns

Revision ID: 0006_profile_xp
Revises: 0005_polls
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_profile_xp"
down_revision: Union[str, None] = "0005_polls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("bio", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "profiles",
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("profiles", "xp")
    op.drop_column("profiles", "bio")
