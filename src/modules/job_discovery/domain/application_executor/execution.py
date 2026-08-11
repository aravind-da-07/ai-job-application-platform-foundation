"""
Domain contracts for application execution.

This module contains portal-independent application execution data.

No Playwright, browser, HTTP, or portal-specific implementation belongs
here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.shared.config.constants import JobSourceType


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


class ApplicationExecutionStatus(str, Enum):
    """Normalized application execution states."""

    READY = "ready"
    STARTED = "started"
    FORM_DETECTED = "form_detected"
    FIELDS_MAPPED = "fields_mapped"
    SUBMISSION_READY = "submission_ready"
    SUBMITTED = "submitted"
    FAILED = "failed"
    AUTHENTICATION_REQUIRED = "authentication_required"
    CAPTCHA_DETECTED = "captcha_detected"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True)
class ApplicationExecutionRequest:
    """
    Request to execute an application.

    The request contains identifiers and references needed by an
    infrastructure executor. It does not contain browser-specific
    objects.
    """

    application_id: str
    external_job_id: str
    job_url: str
    source: JobSourceType

    resume_id: str | None = None
    cover_letter_id: str | None = None

    candidate_data: dict[str, Any] = field(
        default_factory=dict
    )

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


@dataclass(frozen=True)
class ApplicationExecutionResult:
    """
    Normalized result returned by an application executor.
    """

    application_id: str
    external_job_id: str
    source: JobSourceType

    status: ApplicationExecutionStatus

    submitted: bool = False

    requires_manual_intervention: bool = False

    reason: str | None = None

    error_code: str | None = None

    fields_detected: int = 0
    fields_filled: int = 0

    started_at: datetime | None = None
    completed_at: datetime | None = None

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

        if self.fields_detected < 0:
            raise ValueError(
                "fields_detected cannot be negative."
            )

        if self.fields_filled < 0:
            raise ValueError(
                "fields_filled cannot be negative."
            )

        if self.fields_filled > self.fields_detected:
            raise ValueError(
                "fields_filled cannot exceed fields_detected."
            )

        if (
            self.status
            == ApplicationExecutionStatus.SUBMITTED
            and not self.submitted
        ):
            raise ValueError(
                "Submitted execution status requires "
                "submitted=True."
            )

        intervention_statuses = {
            ApplicationExecutionStatus.AUTHENTICATION_REQUIRED,
            ApplicationExecutionStatus.CAPTCHA_DETECTED,
            ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED,
        }

        if (
            self.status in intervention_statuses
            and not self.requires_manual_intervention
        ):
            raise ValueError(
                "Authentication, CAPTCHA, and manual-review "
                "states require manual intervention."
            )


@dataclass(frozen=True)
class ApplicationExecutionContext:
    """
    Runtime context maintained by an executor.

    This remains browser-independent at the domain level.
    """

    application_id: str
    external_job_id: str
    source: JobSourceType

    status: ApplicationExecutionStatus = (
        ApplicationExecutionStatus.READY
    )

    started_at: datetime | None = None
    completed_at: datetime | None = None

    fields_detected: int = 0
    fields_filled: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def start(self) -> "ApplicationExecutionContext":
        """Transition context to started."""

        return ApplicationExecutionContext(
            application_id=self.application_id,
            external_job_id=self.external_job_id,
            source=self.source,
            status=ApplicationExecutionStatus.STARTED,
            started_at=utc_now(),
            completed_at=None,
            fields_detected=self.fields_detected,
            fields_filled=self.fields_filled,
            metadata=dict(self.metadata),
        )

    def form_detected(
        self,
        *,
        fields_detected: int,
    ) -> "ApplicationExecutionContext":
        """Record that an application form was detected."""

        if fields_detected < 0:
            raise ValueError(
                "fields_detected cannot be negative."
            )

        return ApplicationExecutionContext(
            application_id=self.application_id,
            external_job_id=self.external_job_id,
            source=self.source,
            status=ApplicationExecutionStatus.FORM_DETECTED,
            started_at=self.started_at,
            completed_at=None,
            fields_detected=fields_detected,
            fields_filled=self.fields_filled,
            metadata=dict(self.metadata),
        )

    def fields_mapped(
        self,
        *,
        fields_filled: int,
    ) -> "ApplicationExecutionContext":
        """Record mapped/fillable application fields."""

        if fields_filled < 0:
            raise ValueError(
                "fields_filled cannot be negative."
            )

        if fields_filled > self.fields_detected:
            raise ValueError(
                "fields_filled cannot exceed fields_detected."
            )

        return ApplicationExecutionContext(
            application_id=self.application_id,
            external_job_id=self.external_job_id,
            source=self.source,
            status=ApplicationExecutionStatus.FIELDS_MAPPED,
            started_at=self.started_at,
            completed_at=None,
            fields_detected=self.fields_detected,
            fields_filled=fields_filled,
            metadata=dict(self.metadata),
        )


__all__ = [
    "ApplicationExecutionContext",
    "ApplicationExecutionRequest",
    "ApplicationExecutionResult",
    "ApplicationExecutionStatus",
    "utc_now",
]