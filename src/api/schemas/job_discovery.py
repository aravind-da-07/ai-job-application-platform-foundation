"""
API schemas for job discovery.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.shared.config.constants import (
    EmploymentType,
    JobSourceType,
    RemoteStatus,
)


class JobDiscoveryRequest(BaseModel):
    """
    Request body for discovering jobs.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    source: JobSourceType = JobSourceType.LINKEDIN

    keywords: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    locations: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    remote_statuses: list[RemoteStatus] = Field(
        default_factory=list,
    )

    employment_types: list[EmploymentType] = Field(
        default_factory=list,
    )

    minimum_match_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    maximum_results: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    storage_state: str | None = Field(
        default=None,
        max_length=500,
    )


class DiscoveredJobResponse(BaseModel):
    """
    API representation of a discovered job.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

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

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class JobDiscoveryResponse(BaseModel):
    """
    API response for a completed job discovery run.
    """

    source: JobSourceType

    total_found: int
    jobs_received: int

    persisted_count: int
    created_count: int
    updated_count: int
    failed_count: int

    jobs: list[DiscoveredJobResponse] = Field(
        default_factory=list
    )

    created_jobs: list[DiscoveredJobResponse] = Field(
        default_factory=list
    )

    updated_jobs: list[DiscoveredJobResponse] = Field(
        default_factory=list
    )

    failed_jobs: list[DiscoveredJobResponse] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )