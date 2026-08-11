"""
Domain entities for job discovery.

These entities contain portal-independent data structures.

No Playwright, SQLAlchemy, HTTP client, or portal-specific logic belongs
in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.shared.config.constants import (
    EmploymentType,
    JobSourceType,
    RemoteStatus,
)


@dataclass(frozen=True)
class JobSearchCriteria:
    """
    Criteria used to search for jobs.

    This object is intentionally independent of any specific job portal.
    """

    keywords: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    remote_statuses: tuple[RemoteStatus, ...] = ()
    employment_types: tuple[EmploymentType, ...] = ()
    minimum_match_score: float | None = None
    maximum_results: int = 50

    def __post_init__(self) -> None:
        if self.maximum_results < 1:
            raise ValueError(
                "maximum_results must be greater than zero."
            )

        if self.minimum_match_score is not None:
            if not 0.0 <= self.minimum_match_score <= 1.0:
                raise ValueError(
                    "minimum_match_score must be between 0 and 1."
                )


@dataclass(frozen=True)
class DiscoveredJob:
    """
    Normalized job discovered from a supported source.

    Portal adapters translate their portal-specific representation into
    this common structure.
    """

    external_id: str
    title: str
    company_name: str
    source: JobSourceType
    url: str

    location: str | None = None
    remote_status: RemoteStatus | None = None
    employment_type: EmploymentType | None = None

    description: str | None = None
    posted_at: str | None = None

    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.external_id.strip():
            raise ValueError(
                "external_id cannot be empty."
            )

        if not self.title.strip():
            raise ValueError(
                "title cannot be empty."
            )

        if not self.company_name.strip():
            raise ValueError(
                "company_name cannot be empty."
            )

        if not self.url.strip():
            raise ValueError(
                "url cannot be empty."
            )


@dataclass(frozen=True)
class DiscoveryResult:
    """
    Result returned by a portal adapter.

    The result contains normalized jobs plus discovery metadata.
    """

    source: JobSourceType
    jobs: tuple[DiscoveredJob, ...] = ()
    total_found: int = 0
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.total_found < 0:
            raise ValueError(
                "total_found cannot be negative."
            )

        if self.total_found < len(self.jobs):
            raise ValueError(
                "total_found cannot be less than the number "
                "of returned jobs."
            )