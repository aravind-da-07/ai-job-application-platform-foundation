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

This layer does not perform browser automation or submit applications.
It only decides which discovered jobs are safe and eligible to enter
the application queue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    jobs_skipped: int
    jobs_manual_review: int

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class ApplicationPipelineService:
    """
    Coordinates matching, eligibility, and queueing.
    """

    def __init__(
        self,
        *,
        matching_service: JobMatchingService | None = None,
        eligibility_service: (
            ApplicationEligibilityService | None
        ) = None,
        queue_service: ApplicationQueueService | None = None,
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

    @property
    def matching_service(self) -> JobMatchingService:
        return self._matching_service

    @property
    def eligibility_service(
        self,
    ) -> ApplicationEligibilityService:
        return self._eligibility_service

    @property
    def queue_service(self) -> ApplicationQueueService:
        return self._queue_service

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
    ) -> ApplicationPipelineResult:
        """
        Process one discovered job through all application gates.
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
                reason=eligibility.reason,
                metadata=dict(metadata or {}),
            )

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
                reason=queue_decision.reason,
                metadata={
                    **dict(metadata or {}),
                    **queue_decision.metadata,
                },
            )

        return ApplicationPipelineResult(
            external_job_id=job.external_id,
            match_result=match_result,
            eligibility_decision=(
                eligibility.decision
            ),
            queued=True,
            queue_item=queue_decision.item,
            reason=queue_decision.reason,
            metadata={
                **dict(metadata or {}),
                **queue_decision.metadata,
            },
        )

    def process_jobs(
        self,
        jobs: list[DiscoveredJob]
        | tuple[DiscoveredJob, ...],
        profile: CandidateJobProfile,
        *,
        already_applied_ids: set[str] | None = None,
        inactive_job_ids: set[str] | None = None,
        authentication_required_ids: set[str] | None = None,
        captcha_detected_ids: set[str] | None = None,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationPipelineBatchResult:
        """
        Process multiple discovered jobs.
        """

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

        results: list[
            ApplicationPipelineResult
        ] = []

        for job in jobs:
            results.append(
                self.process_job(
                    job,
                    profile,
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
            jobs_skipped=jobs_skipped,
            jobs_manual_review=jobs_manual_review,
            metadata=dict(metadata or {}),
        )