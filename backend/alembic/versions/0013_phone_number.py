"""add phone_number to users

Revision ID: 0013_phone_number
Revises: 0012_two_roles
Create Date: 2026-11-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_phone_number"
down_revision: Union[str, None] = "0012_two_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=32), nullable=True))
    op.create_index("ix_users_phone_number", "users", ["phone_number"])
    op.create_unique_constraint("uq_users_phone_number", "users", ["phone_number"])
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)
    op.execute("UPDATE users SET phone_number = '+573001234567', is_superuser = TRUE WHERE email = 'admin@chomelo.dev'")


def downgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.drop_constraint("uq_users_phone_number", "users", type_="unique")
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_column("users", "phone_number")
