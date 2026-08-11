"""
Application answer-resolution domain models.

These models represent answers that may be used during an application
execution workflow.

This layer does not interact with Playwright and does not submit forms.
It only represents whether an answer is safe and sufficiently supported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApplicationAnswerDecision(str, Enum):
    """
    Decision made by the answer resolver.
    """

    AUTO_ANSWER = "auto_answer"
    MANUAL_REVIEW = "manual_review"
    SKIP = "skip"


class ApplicationAnswerSource(str, Enum):
    """
    Source from which an answer was obtained.
    """

    CANDIDATE_PROFILE = "candidate_profile"
    RESUME = "resume"
    USER_PREFERENCE = "user_preference"
    SYSTEM_CONFIGURATION = "system_configuration"
    JOB_CONTEXT = "job_context"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ApplicationAnswer:
    """
    Normalized answer candidate for an application field.
    """

    field_id: str
    normalized_field_name: str
    value: str | None

    decision: ApplicationAnswerDecision

    confidence: float = 0.0

    source: ApplicationAnswerSource = (
        ApplicationAnswerSource.UNKNOWN
    )

    reason: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.field_id.strip():
            raise ValueError(
                "field_id cannot be empty."
            )

        if not self.normalized_field_name.strip():
            raise ValueError(
                "normalized_field_name cannot be empty."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1."
            )

        if (
            self.decision
            == ApplicationAnswerDecision.AUTO_ANSWER
            and not self.value
        ):
            raise ValueError(
                "AUTO_ANSWER requires a non-empty value."
            )

        if (
            self.decision
            in (
                ApplicationAnswerDecision.MANUAL_REVIEW,
                ApplicationAnswerDecision.SKIP,
            )
            and self.value is not None
            and not isinstance(self.value, str)
        ):
            raise ValueError(
                "Answer value must be a string or None."
            )


@dataclass(frozen=True)
class AnswerResolutionResult:
    """
    Result containing resolved answers for an application form.
    """

    answers: tuple[ApplicationAnswer, ...] = ()

    auto_answer_count: int = 0
    manual_review_count: int = 0
    skipped_count: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        calculated_auto = sum(
            answer.decision
            == ApplicationAnswerDecision.AUTO_ANSWER
            for answer in self.answers
        )

        calculated_manual = sum(
            answer.decision
            == ApplicationAnswerDecision.MANUAL_REVIEW
            for answer in self.answers
        )

        calculated_skipped = sum(
            answer.decision
            == ApplicationAnswerDecision.SKIP
            for answer in self.answers
        )

        if self.auto_answer_count != calculated_auto:
            raise ValueError(
                "auto_answer_count does not match answers."
            )

        if self.manual_review_count != calculated_manual:
            raise ValueError(
                "manual_review_count does not match answers."
            )

        if self.skipped_count != calculated_skipped:
            raise ValueError(
                "skipped_count does not match answers."
            )

    @property
    def requires_manual_review(self) -> bool:
        """Return True when at least one answer needs review."""

        return self.manual_review_count > 0