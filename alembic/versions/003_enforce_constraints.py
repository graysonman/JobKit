"""Enforce NOT NULL and foreign key constraints on user_id.

Makes user_id non-nullable on all tables except message_templates.
Adds foreign key to users.id. Replaces Company global unique(name)
with unique(name, user_id).

Revision ID: 003
Revises: 002
Create Date: 2025-01-01 00:00:02.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables where user_id becomes NOT NULL
NOT_NULL_TABLES = [
    "contacts",
    "companies",
    "applications",
    "message_history",
    "user_profile",
    "interactions",
]


def upgrade() -> None:
    # Make user_id NOT NULL and add FK on non-nullable tables
    for table in NOT_NULL_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "user_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
            batch_op.create_foreign_key(
                f"fk_{table}_user_id",
                "users",
                ["user_id"],
                ["id"],
            )

    # message_templates: add FK but keep nullable
    with op.batch_alter_table("message_templates") as batch_op:
        batch_op.create_foreign_key(
            "fk_message_templates_user_id",
            "users",
            ["user_id"],
            ["id"],
        )

    # Replace Company global unique(name) with unique(name, user_id)
    # First check if old constraint exists before trying to drop it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_unique = [
        c["name"] for c in inspector.get_unique_constraints("companies")
    ]

    if "uq_companies_name" in existing_unique:
        with op.batch_alter_table("companies") as batch_op:
            batch_op.drop_constraint("uq_companies_name", type_="unique")

    with op.batch_alter_table("companies") as batch_op:
        batch_op.create_unique_constraint(
            "uix_company_name_user", ["name", "user_id"]
        )

    # UserProfile: add unique constraint on user_id
    with op.batch_alter_table("user_profile") as batch_op:
        batch_op.create_unique_constraint(
            "uix_user_profile_user_id", ["user_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("user_profile") as batch_op:
        batch_op.drop_constraint("uix_user_profile_user_id", type_="unique")

    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_constraint("uix_company_name_user", type_="unique")
        batch_op.create_unique_constraint("uq_companies_name", ["name"])

    with op.batch_alter_table("message_templates") as batch_op:
        batch_op.drop_constraint("fk_message_templates_user_id", type_="foreignkey")

    for table in NOT_NULL_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(f"fk_{table}_user_id", type_="foreignkey")
            batch_op.alter_column(
                "user_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
