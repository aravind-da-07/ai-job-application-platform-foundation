"""
Application eligibility domain models.

These models contain portal-independent decisions about whether a
discovered job is allowed to enter the application workflow.

No Playwright, database, HTTP, or portal-specific logic belongs here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.shared.config.constants import (
    ApplicationStatus,
    DecisionType,
    JobSourceType,
)


class ApplicationEligibilityDecision(str, Enum):
    """
    Final decision produced by the application eligibility layer.
    """

    QUEUE = "queue"
    SKIP = "skip"
    MANUAL_REVIEW = "manual_review"
    AUTHENTICATION_REQUIRED = "authentication_required"
    CAPTCHA_DETECTED = "captcha_detected"


@dataclass(frozen=True)
class ApplicationEligibility:
    """
    Result of evaluating whether a job can enter the application workflow.
    """

    eligible: bool
    decision: ApplicationEligibilityDecision
    reason: str

    external_job_id: str
    source: JobSourceType

    application_status: ApplicationStatus = ApplicationStatus.QUEUED

    duplicate: bool = False
    job_active: bool = True
    authentication_required: bool = False
    captcha_detected: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        if not self.reason.strip():
            raise ValueError(
                "reason cannot be empty."
            )

        if self.decision == ApplicationEligibilityDecision.QUEUE:
            if not self.eligible:
                raise ValueError(
                    "QUEUE decision requires eligible=True."
                )

        if self.decision != ApplicationEligibilityDecision.QUEUE:
            if self.eligible:
                raise ValueError(
                    "Only QUEUE decision can have eligible=True."
                )