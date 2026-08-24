"""
API schemas for job applications.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.shared.config.constants import ApplicationStatus


class ApplicationQueueRequest(BaseModel):
    """
    Request body for queueing one discovered job for application.

    The candidate profile is supplied by the caller because the
    discovery layer remains independent of user-specific preferences.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    user_id: UUID

    job_id: UUID

    resume_id: UUID | None = None

    resume_version_id: UUID | None = None

    target_roles: list[str] = Field(
        min_length=1,
        max_length=20,
    )

    preferred_locations: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    preferred_remote_statuses: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    required_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    preferred_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    excluded_roles: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    excluded_companies: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    minimum_experience_years: float | None = Field(
        default=None,
        ge=0.0,
    )

    maximum_experience_years: float | None = Field(
        default=None,
        ge=0.0,
    )

    minimum_match_score: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
    )

    priority: int = Field(
        default=0,
        ge=0,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class ApplicationQueueResponse(BaseModel):
    """
    API representation of a queued application.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    application_id: str

    user_id: UUID

    job_id: UUID

    resume_id: UUID | None = None

    resume_version_id: UUID | None = None

    external_job_id: str

    source: str

    job_url: str

    job_title: str

    company_name: str

    match_score: float

    status: ApplicationStatus

    priority: int

    attempt_count: int

    max_attempts: int

    queued_at: Any | None = None

    confirmation_id: str | None = None

    error_code: str | None = None

    error_message: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class ApplicationQueueResult(BaseModel):
    """
    Result of queueing an application.
    """

    application: ApplicationQueueResponse | None = None

    queued: bool

    persisted: bool

    reason: str

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )