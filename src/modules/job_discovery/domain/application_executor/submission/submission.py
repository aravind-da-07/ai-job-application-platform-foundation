"""
Application submission domain models.

These models describe the outcome of an application submission
independently of any browser or portal implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApplicationSubmissionStatus(str, Enum):
    """
    Possible application submission outcomes.
    """

    READY = "ready"
    SUBMITTED = "submitted"
    FAILED = "failed"
    AUTHENTICATION_REQUIRED = "authentication_required"
    CAPTCHA_DETECTED = "captcha_detected"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True)
class ApplicationSubmissionRequest:
    """
    Request to submit an already-completed application.

    Submission must only occur after the execution layer has
    successfully completed and verified the approved fields.
    """

    application_id: str
    external_job_id: str

    verified_field_count: int = 0

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

        if self.verified_field_count < 0:
            raise ValueError(
                "verified_field_count cannot be negative."
            )


@dataclass(frozen=True)
class ApplicationSubmissionResult:
    """
    Structured result of an application submission attempt.
    """

    application_id: str
    external_job_id: str

    status: ApplicationSubmissionStatus

    submitted: bool = False

    verified_field_count: int = 0

    confirmation_id: str | None = None

    error_code: str | None = None
    error_message: str | None = None

    manual_intervention_required: bool = False

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

        if self.verified_field_count < 0:
            raise ValueError(
                "verified_field_count cannot be negative."
            )

        if self.submitted:
            if (
                self.status
                != ApplicationSubmissionStatus.SUBMITTED
            ):
                raise ValueError(
                    "submitted=True requires SUBMITTED status."
                )

        if (
            self.status
            == ApplicationSubmissionStatus.SUBMITTED
            and not self.submitted
        ):
            raise ValueError(
                "SUBMITTED status requires submitted=True."
            )

        if self.status == ApplicationSubmissionStatus.SUBMITTED:
            if not self.confirmation_id:
                raise ValueError(
                    "SUBMITTED status requires a confirmation_id."
                )