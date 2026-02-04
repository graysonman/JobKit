"""
Database connection, session management, and resilience layer.

Supports both SQLite (local development) and PostgreSQL (hosted deployment).
Includes retry logic with exponential backoff for transient database errors.
"""
import logging
import random
import time
from contextlib import contextmanager
from functools import wraps

from sqlalchemy import create_engine, event
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

logger = logging.getLogger("jobkit.database")

Base = declarative_base()


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def create_app_engine(database_url: str = None):
    """
    Create a SQLAlchemy engine appropriate for the database backend.

    SQLite: WAL mode, busy_timeout, check_same_thread=False
    PostgreSQL: connection pooling with pre-ping
    """
    url = database_url or settings.database_url

    if _is_sqlite(url):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        logger.info("Created SQLite engine with WAL mode")
    else:
        engine = create_engine(
            url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_pre_ping=True,
            pool_recycle=settings.db_pool_recycle,
        )
        logger.info("Created PostgreSQL engine with connection pooling")

    return engine


engine = create_app_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _is_transient_error(exc: Exception) -> bool:
    """Check if an exception is a transient/retryable database error."""
    if isinstance(exc, IntegrityError):
        return False
    return isinstance(exc, (OperationalError, DBAPIError))


def with_retry(func):
    """
    Decorator that retries a function on transient database errors
    with exponential backoff and jitter.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = settings.db_retry_max_attempts
        base_delay = settings.db_retry_base_delay
        max_delay = 2.0

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if not _is_transient_error(exc) or attempt == max_retries - 1:
                    raise
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, delay * 0.5)
                sleep_time = delay + jitter
                logger.warning(
                    "Transient DB error (attempt %d/%d), retrying in %.2fs: %s",
                    attempt + 1, max_retries, sleep_time, exc
                )
                time.sleep(sleep_time)

    return wrapper


def get_db():
    """FastAPI dependency that yields a database session with transient error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        if _is_transient_error(exc):
            db.rollback()
            logger.warning("Rolled back session due to transient error: %s", exc)
        raise
    finally:
        db.close()


@contextmanager
def get_resilient_session():
    """
    Context manager for database sessions outside of FastAPI endpoints.

    Usage:
        with get_resilient_session() as db:
            db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as exc:
        db.rollback()
        if _is_transient_error(exc):
            logger.warning("Resilient session rolled back due to transient error: %s", exc)
        raise
    finally:
        db.close()


def init_db():
    """
    Create all tables from model metadata.

    Intended for local development convenience. In production,
    use Alembic migrations instead: `alembic upgrade head`
    """
    logger.warning(
        "init_db() called — this creates tables directly from models. "
        "Use Alembic migrations in production."
    )
    Base.metadata.create_all(bind=engine)
