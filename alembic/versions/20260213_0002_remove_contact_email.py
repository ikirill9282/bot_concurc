"""Remove contact_email field from users table.

Revision ID: 20260213_0002
Revises: 20260213_0001
Create Date: 2026-02-13 11:57:24.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260213_0002"
down_revision = "20260213_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем существование колонки перед удалением
    from alembic import op
    from sqlalchemy import text
    
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='contact_email'
    """))
    if result.fetchone():
        op.drop_column("users", "contact_email")


def downgrade() -> None:
    op.add_column("users", sa.Column("contact_email", sa.Text(), nullable=True))
