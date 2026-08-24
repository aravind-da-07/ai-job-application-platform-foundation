"""
API schemas for user management.

These schemas define the HTTP request and response contracts
for the user API.

The schemas intentionally remain independent of:
    - FastAPI routers
    - SQLAlchemy
    - repositories
    - application services
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.users.domain.entities.user import AuthProvider


class CreateUserRequest(BaseModel):
    """
    Request body for creating a platform user.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    full_name: str = Field(
        min_length=1,
        max_length=150,
    )

    email: str = Field(
        min_length=3,
        max_length=320,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )


class UpdateUserRequest(BaseModel):
    """
    Request body for updating a platform user.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    full_name: str = Field(
        min_length=1,
        max_length=150,
    )

    email: str = Field(
        min_length=3,
        max_length=320,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    email_verified: bool = False

    is_active: bool = True


class UserResponse(BaseModel):
    """
    API representation of a platform user.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    full_name: str

    email: str

    phone: str | None = None

    auth_provider: AuthProvider

    is_active: bool

    email_verified: bool

    created_at: datetime | None = None


__all__ = [
    "CreateUserRequest",
    "UpdateUserRequest",
    "UserResponse",
]