"""Add is_admin to users table and create admin_audit_log table.

Production-safe migration: adds new column with default, creates new table.
No existing data is modified or deleted.

Revision ID: 004
Revises: 003
Create Date: 2026-02-16 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_admin column to users table (existing rows get False)
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    # Create admin_audit_log table
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_table("admin_audit_log")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_admin")
