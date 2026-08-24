"""
Application pipeline service.

Connects:

    DiscoveredJob
        ↓
    JobMatchingService
        ↓
    ApplicationEligibilityService
        ↓
    ApplicationQueueService
        ↓
    ApplicationRepository

This layer decides which discovered jobs are eligible for application
and persists accepted applications.

This service does not perform browser automation or submit applications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.modules.job_discovery.domain.application import (
    ApplicationEligibilityDecision,
)
from src.modules.job_discovery.domain.application_queue import (
    ApplicationQueueItem,
)
from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.domain.matching import (
    CandidateJobProfile,
    JobMatchResult,
)
from src.modules.job_discovery.domain.repositories.application_repository import (
    ApplicationRepository,
)
from src.modules.job_discovery.services.application import (
    ApplicationEligibilityService,
)
from src.modules.job_discovery.services.application_queue import (
    ApplicationQueueService,
)
from src.modules.job_discovery.services.matching import (
    JobMatchingService,
)
from src.shared.config.constants import (
    DecisionType,
)


@dataclass(frozen=True)
class ApplicationPipelineResult:
    """
    Result of processing one discovered job through the pipeline.
    """

    external_job_id: str

    match_result: JobMatchResult

    eligibility_decision: ApplicationEligibilityDecision

    queued: bool = False

    queue_item: ApplicationQueueItem | None = None

    persisted: bool = False

    reason: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class ApplicationPipelineBatchResult:
    """
    Result of processing multiple discovered jobs.
    """

    results: tuple[ApplicationPipelineResult, ...]

    jobs_evaluated: int

    jobs_matched: int

    jobs_queued: int

    jobs_persisted: int

    jobs_skipped: int

    jobs_manual_review: int

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class ApplicationPipelineService:
    """
    Coordinates matching, eligibility, queueing, and persistence.

    Flow:

        1. Match the discovered job.
        2. Evaluate application eligibility.
        3. Queue eligible jobs.
        4. Persist the accepted application.

    User/resume context is supplied by the caller because discovery
    itself is intentionally user-independent.
    """

    def __init__(
        self,
        *,
        matching_service: JobMatchingService | None = None,
        eligibility_service: (
            ApplicationEligibilityService | None
        ) = None,
        queue_service: ApplicationQueueService | None = None,
        application_repository: ApplicationRepository | None = None,
    ) -> None:

        self._matching_service = (
            matching_service
            or JobMatchingService()
        )

        self._eligibility_service = (
            eligibility_service
            or ApplicationEligibilityService()
        )

        self._queue_service = (
            queue_service
            or ApplicationQueueService()
        )

        self._application_repository = (
            application_repository
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def matching_service(
        self,
    ) -> JobMatchingService:
        """Return the configured matching service."""

        return self._matching_service

    @property
    def eligibility_service(
        self,
    ) -> ApplicationEligibilityService:
        """Return the configured eligibility service."""

        return self._eligibility_service

    @property
    def queue_service(
        self,
    ) -> ApplicationQueueService:
        """Return the configured queue service."""

        return self._queue_service

    @property
    def application_repository(
        self,
    ) -> ApplicationRepository | None:
        """Return the configured application repository."""

        return self._application_repository

    # ------------------------------------------------------------------
    # Single-job processing
    # ------------------------------------------------------------------

    def process_job(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
        *,
        user_id: UUID | None = None,
        job_id: UUID | None = None,
        resume_id: UUID | None = None,
        resume_version_id: UUID | None = None,
        already_applied: bool = False,
        job_active: bool = True,
        authentication_required: bool = False,
        captcha_detected: bool = False,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationPipelineResult:
        """
        Process one discovered job.

        An eligible job is first placed into the application queue.

        When an application repository and the required user/job
        identifiers are available, the accepted application is also
        persisted.
        """

        if job is None:
            raise ValueError(
                "job is required."
            )

        if profile is None:
            raise ValueError(
                "candidate profile is required."
            )

        # --------------------------------------------------------------
        # Stage 1: Matching
        # --------------------------------------------------------------

        match_result = self._matching_service.match(
            job,
            profile,
        )

        # --------------------------------------------------------------
        # Stage 2: Eligibility
        # --------------------------------------------------------------

        eligibility = (
            self._eligibility_service.evaluate(
                job,
                match_decision=match_result.decision,
                already_applied=already_applied,
                job_active=job_active,
                authentication_required=(
                    authentication_required
                ),
                captcha_detected=captcha_detected,
            )
        )

        # --------------------------------------------------------------
        # Stage 3: Queue only eligible jobs
        # --------------------------------------------------------------

        if (
            not eligibility.eligible
            or eligibility.decision
            != ApplicationEligibilityDecision.QUEUE
        ):
            return ApplicationPipelineResult(
                external_job_id=job.external_id,
                match_result=match_result,
                eligibility_decision=(
                    eligibility.decision
                ),
                queued=False,
                queue_item=None,
                persisted=False,
                reason=eligibility.reason,
                metadata=dict(metadata or {}),
            )

        # --------------------------------------------------------------
        # Stage 4: Queue
        # --------------------------------------------------------------

        queue_decision = self._queue_service.enqueue(
            job,
            match_score=match_result.overall_score,
            priority=priority,
            metadata=metadata,
        )

        if not queue_decision.accepted:
            return ApplicationPipelineResult(
                external_job_id=job.external_id,
                match_result=match_result,
                eligibility_decision=(
                    eligibility.decision
                ),
                queued=False,
                queue_item=None,
                persisted=False,
                reason=queue_decision.reason,
                metadata={
                    **dict(metadata or {}),
                    **queue_decision.metadata,
                },
            )

        queue_item = queue_decision.item

        if queue_item is None:
            return ApplicationPipelineResult(
                external_job_id=job.external_id,
                match_result=match_result,
                eligibility_decision=(
                    eligibility.decision
                ),
                queued=True,
                queue_item=None,
                persisted=False,
                reason=(
                    "Application was accepted into the queue "
                    "but no queue item was returned."
                ),
                metadata={
                    **dict(metadata or {}),
                    **queue_decision.metadata,
                },
            )

        # --------------------------------------------------------------
        # Stage 5: Persistent application record
        # --------------------------------------------------------------

        persisted = False

        persistence_metadata: dict[str, Any] = {}

        if self._application_repository is not None:

            if user_id is None:
                raise ValueError(
                    "user_id is required when an "
                    "application repository is configured."
                )

            if job_id is None:
                raise ValueError(
                    "job_id is required when an "
                    "application repository is configured."
                )

            persisted_item = (
                self._application_repository.create(
                    queue_item,
                    user_id=user_id,
                    job_id=job_id,
                    resume_id=resume_id,
                    resume_version_id=resume_version_id,
                )
            )

            persisted = True

            persistence_metadata = {
                "application_persisted": True,
                "application_id": (
                    persisted_item.application_id
                ),
            }

        # --------------------------------------------------------------
        # Final result
        # --------------------------------------------------------------

        return ApplicationPipelineResult(
            external_job_id=job.external_id,
            match_result=match_result,
            eligibility_decision=(
                eligibility.decision
            ),
            queued=True,
            queue_item=queue_item,
            persisted=persisted,
            reason=(
                "Application successfully queued."
                if not persisted
                else
                "Application successfully queued and persisted."
            ),
            metadata={
                **dict(metadata or {}),
                **queue_decision.metadata,
                **persistence_metadata,
            },
        )

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def process_jobs(
        self,
        jobs: list[DiscoveredJob]
        | tuple[DiscoveredJob, ...],
        profile: CandidateJobProfile,
        *,
        user_id: UUID | None = None,
        job_ids: dict[str, UUID] | None = None,
        resume_id: UUID | None = None,
        resume_version_id: UUID | None = None,
        already_applied_ids: set[str] | None = None,
        inactive_job_ids: set[str] | None = None,
        authentication_required_ids: set[str] | None = None,
        captcha_detected_ids: set[str] | None = None,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationPipelineBatchResult:
        """
        Process multiple discovered jobs.

        `job_ids` maps each external job ID to its persisted database
        UUID.

        Example:

            {
                "linkedin-123": UUID("..."),
                "linkedin-456": UUID("...")
            }
        """

        if jobs is None:
            raise ValueError(
                "jobs is required."
            )

        if profile is None:
            raise ValueError(
                "candidate profile is required."
            )

        already_applied_ids = (
            already_applied_ids or set()
        )

        inactive_job_ids = (
            inactive_job_ids or set()
        )

        authentication_required_ids = (
            authentication_required_ids or set()
        )

        captcha_detected_ids = (
            captcha_detected_ids or set()
        )

        job_ids = job_ids or {}

        results: list[
            ApplicationPipelineResult
        ] = []

        for job in jobs:

            results.append(
                self.process_job(
                    job,
                    profile,
                    user_id=user_id,
                    job_id=job_ids.get(
                        job.external_id
                    ),
                    resume_id=resume_id,
                    resume_version_id=(
                        resume_version_id
                    ),
                    already_applied=(
                        job.external_id
                        in already_applied_ids
                    ),
                    job_active=(
                        job.external_id
                        not in inactive_job_ids
                    ),
                    authentication_required=(
                        job.external_id
                        in authentication_required_ids
                    ),
                    captcha_detected=(
                        job.external_id
                        in captcha_detected_ids
                    ),
                    priority=priority,
                    metadata=metadata,
                )
            )

        # --------------------------------------------------------------
        # Batch statistics
        # --------------------------------------------------------------

        jobs_matched = sum(
            1
            for result in results
            if result.match_result.decision
            == DecisionType.APPLY
        )

        jobs_queued = sum(
            1
            for result in results
            if result.queued
        )

        jobs_persisted = sum(
            1
            for result in results
            if result.persisted
        )

        jobs_manual_review = sum(
            1
            for result in results
            if result.eligibility_decision
            == ApplicationEligibilityDecision.MANUAL_REVIEW
        )

        jobs_skipped = sum(
            1
            for result in results
            if (
                not result.queued
                and result.eligibility_decision
                not in {
                    ApplicationEligibilityDecision.MANUAL_REVIEW,
                }
            )
        )

        return ApplicationPipelineBatchResult(
            results=tuple(results),
            jobs_evaluated=len(results),
            jobs_matched=jobs_matched,
            jobs_queued=jobs_queued,
            jobs_persisted=jobs_persisted,
            jobs_skipped=jobs_skipped,
            jobs_manual_review=jobs_manual_review,
            metadata={
                **dict(metadata or {}),
                "jobs_evaluated": len(results),
                "jobs_matched": jobs_matched,
                "jobs_queued": jobs_queued,
                "jobs_persisted": jobs_persisted,
                "jobs_skipped": jobs_skipped,
                "jobs_manual_review": jobs_manual_review,
            },
        )


__all__ = [
    "ApplicationPipelineResult",
    "ApplicationPipelineBatchResult",
    "ApplicationPipelineService",
]