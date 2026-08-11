"""
Application queue domain models.

These models are independent of browsers, portals, databases,
and external services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.shared.config.constants import (
    ApplicationStatus,
    JobSourceType,
)


@dataclass(frozen=True)
class ApplicationQueueItem:
    """
    Represents a job waiting to be processed by the application runner.
    """

    application_id: str
    external_job_id: str
    job_title: str
    company_name: str
    job_url: str
    source: JobSourceType

    match_score: float
    priority: int = 0

    status: ApplicationStatus = ApplicationStatus.QUEUED

    attempt_count: int = 0
    max_attempts: int = 3

    created_at: datetime = field(
        default_factory=datetime.utcnow
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

        if not self.job_title.strip():
            raise ValueError(
                "job_title cannot be empty."
            )

        if not self.company_name.strip():
            raise ValueError(
                "company_name cannot be empty."
            )

        if not self.job_url.strip():
            raise ValueError(
                "job_url cannot be empty."
            )

        if not 0.0 <= self.match_score <= 1.0:
            raise ValueError(
                "match_score must be between 0 and 1."
            )

        if self.priority < 0:
            raise ValueError(
                "priority cannot be negative."
            )

        if self.attempt_count < 0:
            raise ValueError(
                "attempt_count cannot be negative."
            )

        if self.max_attempts < 1:
            raise ValueError(
                "max_attempts must be greater than zero."
            )

        if self.attempt_count > self.max_attempts:
            raise ValueError(
                "attempt_count cannot exceed max_attempts."
            )


@dataclass(frozen=True)
class ApplicationQueueDecision:
    """
    Result produced when deciding whether a job can enter the queue.
    """

    accepted: bool
    reason: str
    item: ApplicationQueueItem | None = None

    duplicate: bool = False
    queue_full: bool = False

    metadata: dict[str, Any] = field(
        default_factory=dict
    )