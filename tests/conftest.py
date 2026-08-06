"""
Shared pytest fixtures.

Tests never touch the real Supabase database. Instead, `db_session`
spins up an isolated in-memory SQLite database per test, using the same
SQLAlchemy `Base.metadata` that Supabase Postgres uses in production.
This keeps the test suite fast, hermetic, and safe to run in CI without
credentials.
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("LOG_TO_SUPABASE", "false")

from src.shared.database.base import Base  # noqa: E402


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def api_client() -> Iterator[TestClient]:
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client
