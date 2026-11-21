"""add offers and offer redemptions

Revision ID: 0018_offers
Revises: 0017_token_version
Create Date: 2026-11-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018_offers"
down_revision: Union[str, None] = "0017_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "jukebox_id",
            sa.Integer(),
            sa.ForeignKey("jukeboxes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("merchant", sa.String(100), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("terms", sa.String(500), nullable=False, server_default=""),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("cost_credits", sa.Integer(), nullable=False),
        sa.Column("stock_total", sa.Integer(), nullable=False),
        sa.Column("stock_remaining", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_offers_jukebox_id", "offers", ["jukebox_id"])
    op.create_table(
        "offer_redemptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "jukebox_id",
            sa.Integer(),
            sa.ForeignKey("jukeboxes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "offer_id",
            sa.Integer(),
            sa.ForeignKey("offers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("credits_spent", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(300), nullable=False, server_default=""),
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
        sa.UniqueConstraint("offer_id", "user_id", name="uq_offer_redemptions_offer_user"),
        sa.UniqueConstraint("code", name="uq_offer_redemptions_code"),
        sa.UniqueConstraint("idempotency_key", name="uq_offer_redemptions_idem_key"),
    )
    op.create_index("ix_offer_redemptions_jukebox_id", "offer_redemptions", ["jukebox_id"])
    op.create_index("ix_offer_redemptions_offer_id", "offer_redemptions", ["offer_id"])
    op.create_index("ix_offer_redemptions_user_id", "offer_redemptions", ["user_id"])
    op.create_index("ix_offer_redemptions_code", "offer_redemptions", ["code"])


def downgrade() -> None:
    op.drop_table("offer_redemptions")
    op.drop_table("offers")
