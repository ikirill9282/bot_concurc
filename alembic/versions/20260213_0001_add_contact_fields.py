"""Add contact fields to users table.

Revision ID: 20260213_0001
Revises: 20260212_0001
Create Date: 2026-02-13 11:23:59.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260213_0001"
down_revision = "20260212_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("contact_name", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("contact_phone", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("contact_email", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "contact_email")
    op.drop_column("users", "contact_phone")
    op.drop_column("users", "contact_name")
