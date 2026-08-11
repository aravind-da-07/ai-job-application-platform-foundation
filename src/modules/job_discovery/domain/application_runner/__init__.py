"""
Application runner domain.

This module defines the domain-level contract for executing a queued
job application.

No Playwright, browser, HTTP, database, or portal-specific logic
belongs here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.shared.config.constants import (
    ApplicationResult,
    ApplicationStatus,
    JobSourceType,
)


@dataclass(frozen=True)
class ApplicationRunRequest:
    """
    Request to execute one queued job application.

    This object contains only information required to identify and
    execute the application. Browser-specific implementation belongs
    to infrastructure.
    """

    application_id: str
    external_job_id: str
    job_url: str
    source: JobSourceType

    resume_id: str | None = None
    cover_letter_id: str | None = None

    attempt_number: int = 1
    maximum_attempts: int = 3

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        if not self.external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        if not self.job_url.strip():
            raise ValueError(
                "job_url cannot be empty."
            )

        if self.attempt_number < 1:
            raise ValueError(
                "attempt_number must be greater than zero."
            )

        if self.maximum_attempts < 1:
            raise ValueError(
                "maximum_attempts must be greater than zero."
            )

        if self.attempt_number > self.maximum_attempts:
            raise ValueError(
                "attempt_number cannot exceed maximum_attempts."
            )


@dataclass(frozen=True)
class ApplicationRunResult:
    """
    Result of one application execution attempt.

    The result is normalized so every application portal can expose
    the same state model to the application service and dashboard.
    """

    application_id: str
    external_job_id: str
    source: JobSourceType

    status: ApplicationStatus
    result: ApplicationResult

    attempt_number: int = 1

    started_at: datetime | None = None
    completed_at: datetime | None = None

    reason: str | None = None
    error_code: str | None = None

    requires_manual_intervention: bool = False

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        if not self.external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        if self.attempt_number < 1:
            raise ValueError(
                "attempt_number must be greater than zero."
            )


@dataclass(frozen=True)
class ApplicationRunState:
    """
    Current lifecycle state of an application run.

    This object is useful for persistence, API responses, and
    dashboard status rendering.
    """

    application_id: str
    external_job_id: str
    source: JobSourceType

    status: ApplicationStatus = ApplicationStatus.QUEUED

    attempt_number: int = 0
    maximum_attempts: int = 3

    last_result: ApplicationResult = ApplicationResult.PENDING

    reason: str | None = None
    error_code: str | None = None

    started_at: datetime | None = None
    completed_at: datetime | None = None

    requires_manual_intervention: bool = False

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        if not self.external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        if self.attempt_number < 0:
            raise ValueError(
                "attempt_number cannot be negative."
            )

        if self.maximum_attempts < 1:
            raise ValueError(
                "maximum_attempts must be greater than zero."
            )

        if self.attempt_number > self.maximum_attempts:
            raise ValueError(
                "attempt_number cannot exceed maximum_attempts."
            )


def utc_now() -> datetime:
    """
    Return the current timezone-aware UTC timestamp.

    Kept as a small domain utility so lifecycle transitions use
    consistent timestamps.
    """

    return datetime.now(timezone.utc)


__all__ = [
    "ApplicationRunRequest",
    "ApplicationRunResult",
    "ApplicationRunState",
    "utc_now",
]