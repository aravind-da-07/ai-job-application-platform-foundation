"""
SQLAlchemy ORM model for the users table.

This model represents the persistence layer for the User domain entity.

The domain entity is intentionally kept separate from this ORM model so
business logic does not become coupled to SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.users.domain.entities.user import AuthProvider
from src.shared.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class UserModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    PostgreSQL representation of a platform user.
    """

    __tablename__ = "users"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    auth_provider: Mapped[AuthProvider] = mapped_column(
        String(20),
        nullable=False,
        default=AuthProvider.LOCAL,
        server_default=text("'local'"),
    )

    # ------------------------------------------------------------------
    # Account state
    # ------------------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    __table_args__ = (
        Index(
            "ix_users_active_created_at",
            "is_active",
            "created_at",
        ),
    )