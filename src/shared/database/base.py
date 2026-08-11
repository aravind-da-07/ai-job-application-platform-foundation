"""
Declarative base and reusable mixins for every ORM model in the platform.

Every table-backed model must inherit `Base` and, unless there is a
specific documented reason not to, `UUIDPrimaryKeyMixin` and
`TimestampMixin`.

This ensures that database tables consistently use:

- UUID primary keys
- timezone-aware created_at timestamps
- timezone-aware updated_at timestamps
- application-side timestamp generation
- PostgreSQL server-side timestamp defaults
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


def _utcnow() -> datetime:
    """
    Return the current UTC time.

    Used as the application-side timestamp default.
    """

    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    """
    Adds a UUID primary key named `id`.

    UUIDs are generated application-side using uuid4().
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    """
    Adds timezone-aware `created_at` and `updated_at` columns.

    Both application-side and PostgreSQL server-side defaults are provided.

    Application side:
        default=_utcnow
        onupdate=_utcnow

    Database side:
        server_default=now()
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=text("now()"),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("now()"),
        nullable=False,
    )