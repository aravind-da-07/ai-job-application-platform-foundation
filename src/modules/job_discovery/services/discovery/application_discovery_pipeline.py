"""
Discovery-to-application pipeline service.

Connects:

    DiscoveryResult
        ↓
    JobDiscoveryService
        ↓
    persisted DiscoveredJob objects
        ↓
    ApplicationPipelineService
        ↓
    matching
        ↓
    eligibility
        ↓
    application queue

This service does not perform browser automation, authentication,
CAPTCHA handling, or application submission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
)
from src.modules.job_discovery.domain.matching import (
    CandidateJobProfile,
)
from src.modules.job_discovery.services.application_pipeline import (
    ApplicationPipelineBatchResult,
    ApplicationPipelineService,
)
from src.modules.job_discovery.services.discovery.job_discovery_service import (
    JobDiscoveryProcessResult,
    JobDiscoveryService,
)


@dataclass(frozen=True)
class DiscoveryApplicationPipelineResult:
    """
    Combined result of discovery persistence and application
    eligibility/queue processing.
    """

    discovery_result: JobDiscoveryProcessResult

    application_result: ApplicationPipelineBatchResult

    persisted_jobs: tuple[DiscoveredJob, ...] = ()

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def jobs_discovered(self) -> int:
        """Return the number of jobs returned by discovery."""

        return self.discovery_result.jobs_received

    @property
    def jobs_persisted(self) -> int:
        """Return the number of jobs successfully persisted."""

        return self.discovery_result.persisted_count

    @property
    def jobs_persistence_failed(self) -> int:
        """Return the number of jobs that failed persistence."""

        return self.discovery_result.failed_count

    @property
    def jobs_evaluated(self) -> int:
        """Return the number of persisted jobs evaluated."""

        return self.application_result.jobs_evaluated

    @property
    def jobs_matched(self) -> int:
        """Return the number of jobs matching the candidate profile."""

        return self.application_result.jobs_matched

    @property
    def jobs_queued(self) -> int:
        """Return the number of applications queued."""

        return self.application_result.jobs_queued

    @property
    def jobs_skipped(self) -> int:
        """Return the number of jobs skipped."""

        return self.application_result.jobs_skipped

    @property
    def jobs_manual_review(self) -> int:
        """Return the number of jobs requiring manual review."""

        return self.application_result.jobs_manual_review


class DiscoveryApplicationPipelineService:
    """
    Coordinates discovery persistence with application evaluation.

    Responsibilities:

        1. Process a DiscoveryResult.
        2. Persist discovered jobs.
        3. Send only successfully persisted jobs into the
           application pipeline.
        4. Return a normalized combined result.

    This service deliberately does not:
        - open browsers
        - authenticate
        - bypass CAPTCHA
        - fill application forms
        - submit applications
    """

    def __init__(
        self,
        *,
        discovery_service: JobDiscoveryService,
        application_pipeline: ApplicationPipelineService | None = None,
    ) -> None:
        if discovery_service is None:
            raise ValueError(
                "discovery_service is required."
            )

        self._discovery_service = discovery_service

        self._application_pipeline = (
            application_pipeline
            or ApplicationPipelineService()
        )

    @property
    def discovery_service(
        self,
    ) -> JobDiscoveryService:
        """Return the configured discovery service."""

        return self._discovery_service

    @property
    def application_pipeline(
        self,
    ) -> ApplicationPipelineService:
        """Return the configured application pipeline."""

        return self._application_pipeline

    def process(
        self,
        discovery_result: DiscoveryResult,
        profile: CandidateJobProfile,
        *,
        already_applied_ids: set[str] | None = None,
        inactive_job_ids: set[str] | None = None,
        authentication_required_ids: set[str] | None = None,
        captcha_detected_ids: set[str] | None = None,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> DiscoveryApplicationPipelineResult:
        """
        Process one discovery result through persistence and
        application evaluation.

        Only successfully persisted jobs are forwarded to the
        application pipeline.
        """

        if discovery_result is None:
            raise ValueError(
                "discovery_result is required."
            )

        if profile is None:
            raise ValueError(
                "candidate profile is required."
            )

        discovery_processing = (
            self._discovery_service.process(
                discovery_result
            )
        )

        persisted_jobs = (
            discovery_processing.persisted_jobs
        )

        application_result = (
            self._application_pipeline.process_jobs(
                list(persisted_jobs),
                profile,
                already_applied_ids=(
                    already_applied_ids
                ),
                inactive_job_ids=(
                    inactive_job_ids
                ),
                authentication_required_ids=(
                    authentication_required_ids
                ),
                captcha_detected_ids=(
                    captcha_detected_ids
                ),
                priority=priority,
                metadata=metadata,
            )
        )

        combined_metadata = {
            **dict(discovery_result.metadata),
            **dict(metadata or {}),
            "source": (
                discovery_result.source.value
            ),
            "jobs_discovered": (
                discovery_processing.jobs_received
            ),
            "jobs_persisted": (
                discovery_processing.persisted_count
            ),
            "jobs_persistence_failed": (
                discovery_processing.failed_count
            ),
            "jobs_evaluated": (
                application_result.jobs_evaluated
            ),
            "jobs_matched": (
                application_result.jobs_matched
            ),
            "jobs_queued": (
                application_result.jobs_queued
            ),
            "jobs_skipped": (
                application_result.jobs_skipped
            ),
            "jobs_manual_review": (
                application_result.jobs_manual_review
            ),
        }

        return DiscoveryApplicationPipelineResult(
            discovery_result=discovery_processing,
            application_result=application_result,
            persisted_jobs=tuple(
                persisted_jobs
            ),
            metadata=combined_metadata,
        )

    def process_job(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
        *,
        already_applied: bool = False,
        job_active: bool = True,
        authentication_required: bool = False,
        captcha_detected: bool = False,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Process one already-normalized job.

        This convenience method persists the job first and then sends
        the persisted job through the existing application pipeline.
        """

        if job is None:
            raise ValueError(
                "job is required."
            )

        if profile is None:
            raise ValueError(
                "candidate profile is required."
            )

        persisted_job = (
            self._discovery_service.process_job(
                job
            )
        )

        return self._application_pipeline.process_job(
            persisted_job,
            profile,
            already_applied=already_applied,
            job_active=job_active,
            authentication_required=(
                authentication_required
            ),
            captcha_detected=captcha_detected,
            priority=priority,
            metadata=metadata,
        )


__all__ = [
    "DiscoveryApplicationPipelineResult",
    "DiscoveryApplicationPipelineService",
]