"""
Shared pytest fixtures.

Tests never touch the real Supabase database.

The db_session fixture creates an isolated in-memory SQLite database
for every test and registers all SQLAlchemy ORM models before creating
the database schema.

Model registration is important because several models reference tables
defined in other application modules:

    users
      ↓
    resumes
      ↓
    jobs
      ↓
    job_matches

Without importing the ORM models before Base.metadata.create_all(),
SQLAlchemy cannot resolve cross-module foreign keys such as:

    job_matches.resume_id -> resumes.id
    job_matches.user_id   -> users.id
    jobs / resumes        -> users.id
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


# ----------------------------------------------------------------------
# Test environment
# ----------------------------------------------------------------------

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("LOG_TO_SUPABASE", "false")


# ----------------------------------------------------------------------
# Shared SQLAlchemy Base
# ----------------------------------------------------------------------

from src.shared.database.base import Base  # noqa: E402


# ----------------------------------------------------------------------
# ORM model registration
# ----------------------------------------------------------------------
#
# These imports intentionally happen before Base.metadata.create_all().
#
# Importing the modules causes their SQLAlchemy models to be registered
# against the shared Base.metadata.
#
# Do not remove these imports even if they appear unused. They are
# required for SQLAlchemy metadata registration.
# ----------------------------------------------------------------------

from src.modules.users.infrastructure.models.user_model import (  # noqa: E402,F401
    UserModel,
)

from src.modules.resumes.infrastructure.models.resume_model import (  # noqa: E402,F401
    ResumeModel,
    ResumeVersionModel,
)

from src.modules.job_discovery.infrastructure.models.job_model import (  # noqa: E402,F401
    JobModel,
    JobMatchModel,
)


# ----------------------------------------------------------------------
# Database fixture
# ----------------------------------------------------------------------

@pytest.fixture()
def db_session() -> Iterator[Session]:
    """
    Create an isolated SQLite database for one test.

    Every test receives a completely fresh database.

    The production application can continue using PostgreSQL/Supabase;
    this fixture exists only for deterministic automated testing.
    """

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
    )

    # All ORM models have already been imported above.
    # Therefore Base.metadata contains:
    #
    # users
    # resumes
    # resume_versions
    # jobs
    # job_matches
    #
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        future=True,
        expire_on_commit=False,
    )

    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ----------------------------------------------------------------------
# FastAPI test client
# ----------------------------------------------------------------------

@pytest.fixture()
def api_client() -> Iterator[TestClient]:
    """
    Create a FastAPI test client.

    The application itself decides which routes and services are
    available. This fixture does not connect to production services.
    """

    from src.api.main import create_app

    app = create_app()

    with TestClient(app) as client:
        yield client