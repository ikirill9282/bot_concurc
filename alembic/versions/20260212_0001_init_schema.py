"""Initial schema for giveaway bot.

Revision ID: 20260212_0001
Revises:
Create Date: 2026-02-12 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_0001"
down_revision = None
branch_labels = None
depends_on = None


referral_status_enum = sa.Enum("pending", "confirmed", name="referral_status", create_type=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("is_subscribed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("referred_by", sa.BigInteger(), nullable=True),
        sa.Column("referrals_confirmed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_participant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_subscription_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["referred_by"], ["users.tg_user_id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tg_user_id", name="uq_users_tg_user_id"),
    )

    op.create_table(
        "referrals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("referrer_id", sa.BigInteger(), nullable=False),
        sa.Column("referral_id", sa.BigInteger(), nullable=False),
        sa.Column("status", referral_status_enum, nullable=False, server_default="pending"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("referrer_id <> referral_id", name="ck_referrals_no_self_referral"),
        sa.ForeignKeyConstraint(["referrer_id"], ["users.tg_user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referral_id"], ["users.tg_user_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("referral_id", name="uq_referrals_referral_id"),
    )
    op.create_index("ix_referrals_referrer_id", "referrals", ["referrer_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_referrals_referrer_id", table_name="referrals")
    op.drop_table("referrals")

    op.drop_table("users")

    referral_status_enum.drop(op.get_bind(), checkfirst=True)
