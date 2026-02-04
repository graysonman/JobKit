"""Backfill user_id on existing data.

Creates a local@jobkit.local user if needed and assigns all orphaned
records to that user. System templates (is_default=1) keep user_id=NULL.

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:01.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LOCAL_USER_EMAIL = "local@jobkit.local"


def upgrade() -> None:
    conn = op.get_bind()

    # Ensure local user exists
    result = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": LOCAL_USER_EMAIL}
    )
    row = result.fetchone()

    if row:
        local_user_id = row[0]
    else:
        conn.execute(
            sa.text(
                "INSERT INTO users (email, name, is_active, is_verified, created_at, updated_at) "
                "VALUES (:email, :name, 1, 1, :now, :now)"
            ),
            {
                "email": LOCAL_USER_EMAIL,
                "name": "Local User",
                "now": datetime.utcnow().isoformat(),
            }
        )
        result = conn.execute(
            sa.text("SELECT id FROM users WHERE email = :email"),
            {"email": LOCAL_USER_EMAIL}
        )
        local_user_id = result.fetchone()[0]

    # Backfill all tables except message_templates (handled separately)
    for table in ["contacts", "companies", "applications", "message_history", "user_profile", "interactions"]:
        conn.execute(
            sa.text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": local_user_id}
        )

    # message_templates: only backfill non-default templates
    conn.execute(
        sa.text(
            "UPDATE message_templates SET user_id = :uid "
            "WHERE user_id IS NULL AND (is_default = 0 OR is_default IS NULL)"
        ),
        {"uid": local_user_id}
    )
    # System/default templates stay user_id=NULL


def downgrade() -> None:
    # Set all user_id back to NULL (reversible)
    conn = op.get_bind()
    for table in ["contacts", "companies", "applications", "message_templates",
                   "message_history", "user_profile", "interactions"]:
        conn.execute(sa.text(f"UPDATE {table} SET user_id = NULL"))
