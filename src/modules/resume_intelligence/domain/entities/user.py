"""
User domain entity.

Represents the business-level user of the AI Job Application Platform.
This entity is intentionally independent of SQLAlchemy and the database.
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AuthProvider(str, Enum):
    """Supported authentication providers."""

    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


class User(BaseModel):
    """
    Domain representation of a platform user.

    This model contains business data only.
    Database-specific concerns belong in the infrastructure layer.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique user identifier.",
    )

    full_name: str = Field(
        min_length=1,
        max_length=150,
        description="User's full name.",
    )

    email: str = Field(
        min_length=3,
        max_length=320,
        description="User's email address.",
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
        description="Optional phone number.",
    )

    auth_provider: AuthProvider = Field(
        default=AuthProvider.LOCAL,
        description="Authentication provider.",
    )

    is_active: bool = Field(
        default=True,
        description="Whether the user account is active.",
    )

    email_verified: bool = Field(
        default=False,
        description="Whether the user's email has been verified.",
    )