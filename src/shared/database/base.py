"""
Shared SQLAlchemy database foundation.

Provides:
- Declarative Base
- UUID primary-key support
- timezone-aware created_at timestamps
- timezone-aware updated_at timestamps
- SQLite-compatible timestamp defaults
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """
    Return the current UTC datetime.

    This is intentionally a Python-side default instead of a database
    server-side `now()` expression so that the same model works with
    SQLite test databases and production databases.
    """
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    """

    pass


class UUIDPrimaryKeyMixin:
    """
    Reusable UUID primary-key mixin.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """
    Reusable timestamp mixin.

    Timestamps are generated in Python rather than using
    server_default=text("now()").

    This keeps SQLite tests compatible while still producing
    timezone-aware UTC timestamps in production.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class BaseModel(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """
    Common base model for application entities.
    """

    __abstract__ = True