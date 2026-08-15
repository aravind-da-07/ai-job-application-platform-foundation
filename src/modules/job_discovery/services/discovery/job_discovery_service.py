"""
Job discovery processing service.

This service connects portal-independent discovery results to the
job repository.

Responsibilities:
    - Validate DiscoveryResult objects.
    - Persist discovered jobs through JobRepository.
    - Preserve portal-independent domain models.
    - Detect whether a discovered job is new or already persisted.
    - Return a normalized processing result.

This service does NOT:
    - interact with browsers,
    - call LinkedIn directly,
    - perform job matching,
    - evaluate application eligibility,
    - enqueue applications,
    - submit applications.

Those responsibilities belong to their respective layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
)
from src.modules.job_discovery.domain.repositories.job.job_repository import (
    JobRepository,
)
from src.shared.config.constants import JobSourceType


@dataclass(frozen=True)
class JobDiscoveryProcessResult:
    """
    Result of processing one DiscoveryResult.

    persisted_jobs:
        Jobs successfully persisted through the repository.

    created_jobs:
        Jobs that did not previously exist.

    updated_jobs:
        Jobs that already existed and were refreshed.

    failed_jobs:
        Jobs that could not be persisted.

    reasons:
        Human-readable processing information.

    metadata:
        Additional non-domain processing information.
    """

    source: JobSourceType

    total_found: int
    jobs_received: int

    persisted_jobs: tuple[DiscoveredJob, ...] = ()

    created_jobs: tuple[DiscoveredJob, ...] = ()

    updated_jobs: tuple[DiscoveredJob, ...] = ()

    failed_jobs: tuple[DiscoveredJob, ...] = ()

    reasons: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def persisted_count(self) -> int:
        """Return the number of successfully persisted jobs."""

        return len(self.persisted_jobs)

    @property
    def created_count(self) -> int:
        """Return the number of newly created jobs."""

        return len(self.created_jobs)

    @property
    def updated_count(self) -> int:
        """Return the number of updated jobs."""

        return len(self.updated_jobs)

    @property
    def failed_count(self) -> int:
        """Return the number of jobs that failed persistence."""

        return len(self.failed_jobs)


class JobDiscoveryService:
    """
    Application-level service for processing discovery results.

    The service keeps persistence behind the JobRepository contract.

    Portal adapters should return DiscoveryResult objects and should
    not directly interact with SQLAlchemy or database sessions.
    """

    def __init__(
        self,
        repository: JobRepository,
    ) -> None:
        if repository is None:
            raise ValueError(
                "repository cannot be None."
            )

        self._repository = repository

    @property
    def repository(self) -> JobRepository:
        """Return the configured job repository."""

        return self._repository

    @property
    def configured(self) -> bool:
        """Return whether a repository is configured."""

        return self._repository is not None

    def process(
        self,
        discovery_result: DiscoveryResult,
    ) -> JobDiscoveryProcessResult:
        """
        Persist all jobs contained in a DiscoveryResult.

        Existing jobs are updated through repository.upsert().
        New jobs are created through the same repository operation.

        Individual persistence failures are captured in the result
        so one malformed or failed job does not prevent other
        discovered jobs from being processed.
        """

        self._validate_discovery_result(
            discovery_result
        )

        persisted_jobs: list[DiscoveredJob] = []
        created_jobs: list[DiscoveredJob] = []
        updated_jobs: list[DiscoveredJob] = []
        failed_jobs: list[DiscoveredJob] = []

        reasons: list[str] = []

        for job in discovery_result.jobs:

            try:
                existing = (
                    self._repository.get_by_external_id(
                        source=job.source,
                        external_job_id=job.external_id,
                    )
                )

                persisted = self._repository.upsert(
                    job
                )

                persisted_jobs.append(
                    persisted
                )

                if existing is None:
                    created_jobs.append(
                        persisted
                    )
                else:
                    updated_jobs.append(
                        persisted
                    )

            except Exception as exc:
                failed_jobs.append(job)

                reasons.append(
                    (
                        f"Failed to persist job "
                        f"'{job.external_id}': "
                        f"{type(exc).__name__}: {exc}"
                    )
                )

        return JobDiscoveryProcessResult(
            source=discovery_result.source,
            total_found=discovery_result.total_found,
            jobs_received=len(
                discovery_result.jobs
            ),
            persisted_jobs=tuple(
                persisted_jobs
            ),
            created_jobs=tuple(
                created_jobs
            ),
            updated_jobs=tuple(
                updated_jobs
            ),
            failed_jobs=tuple(
                failed_jobs
            ),
            reasons=tuple(reasons),
            metadata={
                **dict(
                    discovery_result.metadata
                ),
                "source": (
                    discovery_result.source.value
                ),
                "total_found": (
                    discovery_result.total_found
                ),
                "jobs_received": len(
                    discovery_result.jobs
                ),
                "persisted_count": len(
                    persisted_jobs
                ),
                "created_count": len(
                    created_jobs
                ),
                "updated_count": len(
                    updated_jobs
                ),
                "failed_count": len(
                    failed_jobs
                ),
            },
        )

    def process_job(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """
        Persist one discovered job.

        This method is useful when a caller already has a normalized
        DiscoveredJob and does not need to construct a DiscoveryResult.
        """

        if job is None:
            raise ValueError(
                "job cannot be None."
            )

        return self._repository.upsert(
            job
        )

    def get_existing_job(
        self,
        *,
        source: JobSourceType,
        external_job_id: str,
    ) -> DiscoveredJob | None:
        """
        Retrieve an existing job by source and external ID.
        """

        if not external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        return (
            self._repository.get_by_external_id(
                source=source,
                external_job_id=external_job_id,
            )
        )

    @staticmethod
    def _validate_discovery_result(
        discovery_result: DiscoveryResult,
    ) -> None:
        """Validate a DiscoveryResult before processing."""

        if discovery_result is None:
            raise ValueError(
                "discovery_result cannot be None."
            )

        if discovery_result.total_found < 0:
            raise ValueError(
                "total_found cannot be negative."
            )

        if (
            discovery_result.total_found
            < len(discovery_result.jobs)
        ):
            raise ValueError(
                "total_found cannot be less than "
                "the number of discovered jobs."
            )

        for job in discovery_result.jobs:
            if job.source != discovery_result.source:
                raise ValueError(
                    "All discovered jobs must use the same "
                    "source as the DiscoveryResult."
                )


__all__ = [
    "JobDiscoveryProcessResult",
    "JobDiscoveryService",
]