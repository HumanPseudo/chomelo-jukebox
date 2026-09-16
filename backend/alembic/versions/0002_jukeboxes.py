"""jukeboxes and jukebox_members tables

Revision ID: 0002_jukeboxes
Revises: 0001_users_profiles
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_jukeboxes"
down_revision: Union[str, None] = "0001_users_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jukeboxes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("invite_code", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_jukeboxes_owner_id_users"),
        sa.UniqueConstraint("invite_code", name="uq_jukeboxes_invite_code"),
    )

    op.create_table(
        "jukebox_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jukebox_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="MEMBER"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["jukebox_id"],
            ["jukeboxes.id"],
            name="fk_jukebox_members_jukebox_id_jukeboxes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_jukebox_members_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("jukebox_id", "user_id", name="uq_jukebox_members_jukebox_id_user_id"),
    )


def downgrade() -> None:
    op.drop_table("jukebox_members")
    op.drop_table("jukeboxes")
