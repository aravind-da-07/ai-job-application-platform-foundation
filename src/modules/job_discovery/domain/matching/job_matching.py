"""
Domain entities for job matching.

This module contains portal-independent structures used to determine
whether a discovered job matches the candidate's target profile.

No Playwright, SQLAlchemy, HTTP client, or portal-specific logic belongs
in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CandidateJobProfile:
    """
    Candidate preferences and matching signals.

    The profile describes what types of jobs the candidate wants.
    It is intentionally independent of any job portal.
    """

    target_roles: tuple[str, ...] = ()
    preferred_locations: tuple[str, ...] = ()
    preferred_remote_statuses: tuple[str, ...] = ()

    required_skills: tuple[str, ...] = ()
    preferred_skills: tuple[str, ...] = ()

    excluded_roles: tuple[str, ...] = ()
    excluded_companies: tuple[str, ...] = ()

    minimum_experience_years: float | None = None
    maximum_experience_years: float | None = None

    minimum_match_score: float = 0.70

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.target_roles:
            raise ValueError(
                "At least one target role is required."
            )

        if not 0.0 <= self.minimum_match_score <= 1.0:
            raise ValueError(
                "minimum_match_score must be between 0 and 1."
            )

        if self.minimum_experience_years is not None:
            if self.minimum_experience_years < 0:
                raise ValueError(
                    "minimum_experience_years cannot be negative."
                )

        if self.maximum_experience_years is not None:
            if self.maximum_experience_years < 0:
                raise ValueError(
                    "maximum_experience_years cannot be negative."
                )

        if (
            self.minimum_experience_years is not None
            and self.maximum_experience_years is not None
            and self.minimum_experience_years
            > self.maximum_experience_years
        ):
            raise ValueError(
                "minimum_experience_years cannot be greater "
                "than maximum_experience_years."
            )


@dataclass(frozen=True)
class JobMatchBreakdown:
    """
    Individual scoring components for a job match.

    Each score is normalized between 0 and 1.
    """

    title_score: float = 0.0
    skill_score: float = 0.0
    location_score: float = 0.0
    remote_score: float = 0.0
    experience_score: float = 0.0

    matched_skills: tuple[str, ...] = ()
    missing_required_skills: tuple[str, ...] = ()

    matched_roles: tuple[str, ...] = ()
    excluded_reasons: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        scores = {
            "title_score": self.title_score,
            "skill_score": self.skill_score,
            "location_score": self.location_score,
            "remote_score": self.remote_score,
            "experience_score": self.experience_score,
        }

        for name, score in scores.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1."
                )


@dataclass(frozen=True)
class JobMatchResult:
    """
    Final normalized result of matching a job against a candidate profile.

    The decision is deliberately represented as a string here so the
    matching domain remains independent from application workflow enums.
    """

    external_job_id: str
    overall_score: float

    decision: str

    breakdown: JobMatchBreakdown

    reason: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        if not 0.0 <= self.overall_score <= 1.0:
            raise ValueError(
                "overall_score must be between 0 and 1."
            )

        allowed_decisions = {
            "apply",
            "skip",
            "manual_review",
        }

        if self.decision not in allowed_decisions:
            raise ValueError(
                "decision must be one of: "
                "apply, skip, manual_review."
            )

        if not self.reason.strip():
            raise ValueError(
                "reason cannot be empty."
            )