"""
Alembic migration environment configuration.

Reads DATABASE_URL from environment or falls back to alembic.ini setting.
Imports all models so autogenerate can detect schema changes.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import Base and all models so Alembic sees them
from app.database import Base
from app.models import (  # noqa: F401
    Contact, Company, Application,
    MessageTemplate, MessageHistory, UserProfile, Interaction
)
from app.auth.models import User, OAuthAccount, RefreshToken, AdminAuditLog  # noqa: F401

config = context.config

# Override sqlalchemy.url from environment variable if set
database_url = os.getenv("DATABASE_URL") or os.getenv("JOBKIT_DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to the database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
