"""
SQLAlchemy engine and session management for the Supabase Postgres database.

Design notes:
  - A single module-level Engine is created lazily and reused (connection
    pooling). Do not create a new Engine per request/repository.
  - `get_db_session()` is a generator meant for FastAPI's dependency
    injection (`Depends(get_db_session)`); it guarantees the session is
    closed, and rolled back on error, regardless of how the request ends.
  - `session_scope()` is a plain context manager for use outside FastAPI
    (scheduler jobs, CLI scripts, tests).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.shared.config.settings import get_settings
from src.shared.core.exceptions import ConfigurationError, DatabaseError
from src.shared.logging.logger import get_logger
from src.shared.database import models as _models

logger = get_logger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _build_engine() -> Engine:
    settings = get_settings()
    if not settings.database_url:
        raise ConfigurationError(
            "DATABASE_URL is not set. Set it to your Supabase Postgres "
            "connection string, e.g. postgresql+psycopg://postgres:"
            "<password>@<project>.supabase.co:5432/postgres"
        )

    return create_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_pre_ping=True,  # detects and recycles dead connections
        echo=settings.database_echo,
        future=True,
    )


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
    return _SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency. Usage: `db: Session = Depends(get_db_session)`."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for non-request contexts (scheduler jobs, scripts, tests)."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_health() -> bool:
    """Runs a trivial query to confirm connectivity. Used by the /health endpoint."""
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - deliberately broad for a health probe
        logger.error("Database health check failed: {}", exc)
        raise DatabaseError("Database health check failed", details={"cause": str(exc)}) from exc


def reset_engine_for_testing() -> None:
    """Clears cached engine/session-factory. Only intended for use in tests."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
