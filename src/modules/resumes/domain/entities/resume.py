"""
Resume domain entities.

These models represent the business-level resume and resume-version
concepts of the AI Job Application Platform.

They are intentionally independent of SQLAlchemy and database concerns.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ResumeStatus(str, Enum):
    """Lifecycle status of a resume."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class Resume(BaseModel):
    """
    Logical resume belonging to a platform user.

    A Resume can have multiple ResumeVersion records over time.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique resume identifier.",
    )

    user_id: UUID = Field(
        description="User who owns this resume.",
    )

    name: str = Field(
        min_length=1,
        max_length=150,
        description="Human-readable resume name.",
    )

    status: ResumeStatus = Field(
        default=ResumeStatus.ACTIVE,
        description="Current lifecycle status of the resume.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the resume record was created.",
    )


class ResumeVersion(BaseModel):
    """
    Immutable version of an actual resume file.

    Each time the user updates their resume, a new version is created.
    Historical versions remain available for application auditing.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique resume-version identifier.",
    )

    resume_id: UUID = Field(
        description="Logical resume this version belongs to.",
    )

    version_number: int = Field(
        ge=1,
        description="Sequential version number.",
    )

    filename: str = Field(
        min_length=1,
        max_length=255,
        description="Original or normalized resume filename.",
    )

    file_extension: str = Field(
        min_length=1,
        max_length=10,
        description="Resume file extension.",
    )

    storage_path: str = Field(
        min_length=1,
        max_length=500,
        description="Path of the resume file in storage.",
    )

    file_hash: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 hash of the resume file.",
    )

    file_size_bytes: int = Field(
        ge=0,
        description="Resume file size in bytes.",
    )

    is_active: bool = Field(
        default=False,
        description="Whether this is the active resume version.",
    )

    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when this version was created.",
    )