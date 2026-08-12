"""
Application execution history domain model.

This module represents the normalized result of an application
execution attempt.

It intentionally contains no browser, Playwright, LinkedIn, database,
or infrastructure-specific logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.shared.config.constants import JobSourceType


class ApplicationExecutionHistoryStatus(str, Enum):
    """
    Normalized lifecycle status for an application execution attempt.
    """

    SUBMITTED = "submitted"
    FAILED = "failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True)
class ApplicationExecutionHistory:
    """
    Immutable record of one application execution attempt.

    The object captures the final execution state while retaining
    enough information for auditing and future persistence.
    """

    application_id: str
    external_job_id: str
    source: JobSourceType
    status: ApplicationExecutionHistoryStatus

    started_at: datetime
    completed_at: datetime

    form_type: str | None = None

    fields_detected: int = 0
    fields_filled: int = 0

    confirmation_id: str | None = None

    manual_intervention_required: bool = False

    reason: str | None = None
    error_code: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        Validate the history record at construction time.
        """

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

        if self.completed_at < self.started_at:
            raise ValueError(
                "completed_at cannot be earlier than started_at."
            )

        if (
            self.status
            == ApplicationExecutionHistoryStatus.SUBMITTED
        ):
            if not self.confirmation_id:
                raise ValueError(
                    "SUBMITTED history requires "
                    "confirmation_id."
                )

            if self.manual_intervention_required:
                raise ValueError(
                    "SUBMITTED history cannot require "
                    "manual intervention."
                )

        if (
            self.status
            == ApplicationExecutionHistoryStatus.FAILED
        ):
            if not self.error_code:
                raise ValueError(
                    "FAILED history requires error_code."
                )

        if (
            self.status
            == ApplicationExecutionHistoryStatus.MANUAL_REVIEW_REQUIRED
        ):
            if not self.manual_intervention_required:
                raise ValueError(
                    "MANUAL_REVIEW_REQUIRED history must "
                    "require manual intervention."
                )