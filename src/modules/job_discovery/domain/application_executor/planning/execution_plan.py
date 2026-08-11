"""
Application execution planning domain.

Defines the immutable plan produced after form detection, field mapping,
and answer resolution.

This module does not perform browser interaction or form submission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApplicationExecutionDecision(str, Enum):
    """Decision controlling whether execution may continue."""

    EXECUTE = "execute"
    MANUAL_REVIEW = "manual_review"
    SKIP = "skip"


@dataclass(frozen=True)
class ApplicationExecutionPlan:
    """
    Immutable application execution plan.

    The plan is the boundary between answer resolution and the browser
    executor.
    """

    application_id: str
    external_job_id: str

    decision: ApplicationExecutionDecision

    total_fields: int = 0
    auto_answer_fields: int = 0
    manual_review_fields: int = 0
    skipped_fields: int = 0

    reason: str = ""

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

        counts = (
            self.total_fields,
            self.auto_answer_fields,
            self.manual_review_fields,
            self.skipped_fields,
        )

        if any(count < 0 for count in counts):
            raise ValueError(
                "Field counts cannot be negative."
            )

        calculated_total = (
            self.auto_answer_fields
            + self.manual_review_fields
            + self.skipped_fields
        )

        if self.total_fields != calculated_total:
            raise ValueError(
                "total_fields must equal the sum of "
                "auto_answer_fields, manual_review_fields, "
                "and skipped_fields."
            )

        if (
            self.decision
            == ApplicationExecutionDecision.EXECUTE
            and self.manual_review_fields > 0
        ):
            raise ValueError(
                "EXECUTE plan cannot contain manual-review fields."
            )

    @property
    def can_execute(self) -> bool:
        """Return True only when execution is explicitly allowed."""

        return (
            self.decision
            == ApplicationExecutionDecision.EXECUTE
        )

    @property
    def requires_manual_review(self) -> bool:
        """Return True when one or more fields require review."""

        return (
            self.decision
            == ApplicationExecutionDecision.MANUAL_REVIEW
            or self.manual_review_fields > 0
        )

    @property
    def is_skipped(self) -> bool:
        """Return True when execution should be skipped."""

        return (
            self.decision
            == ApplicationExecutionDecision.SKIP
        )