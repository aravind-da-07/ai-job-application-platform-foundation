"""
Application eligibility service.

Determines whether a matched job can safely enter the application
queue.

This service does not submit applications and does not bypass
authentication, MFA, CAPTCHA, or other security controls.
"""

from __future__ import annotations

from collections.abc import Iterable

from src.modules.job_discovery.domain.application.eligibility import (
    ApplicationEligibility,
    ApplicationEligibilityDecision,
)
from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.shared.config.constants import (
    ApplicationStatus,
    DecisionType,
)
from src.shared.core.exceptions import ValidationError


class ApplicationEligibilityService:
    """
    Evaluates application eligibility for matched jobs.
    """

    def evaluate(
        self,
        job: DiscoveredJob,
        *,
        match_decision: DecisionType,
        already_applied: bool = False,
        job_active: bool = True,
        authentication_required: bool = False,
        captcha_detected: bool = False,
    ) -> ApplicationEligibility:
        """
        Evaluate one job for application eligibility.
        """

        if job is None:
            raise ValidationError(
                "A discovered job is required."
            )

        if already_applied:
            return ApplicationEligibility(
                eligible=False,
                decision=ApplicationEligibilityDecision.SKIP,
                reason=(
                    "Application already exists for this job."
                ),
                external_job_id=job.external_id,
                source=job.source,
                application_status=ApplicationStatus.DUPLICATE,
                duplicate=True,
                job_active=job_active,
                authentication_required=authentication_required,
                captcha_detected=captcha_detected,
            )

        if not job_active:
            return ApplicationEligibility(
                eligible=False,
                decision=ApplicationEligibilityDecision.SKIP,
                reason="Job is no longer active.",
                external_job_id=job.external_id,
                source=job.source,
                application_status=ApplicationStatus.SKIPPED,
                job_active=False,
                authentication_required=authentication_required,
                captcha_detected=captcha_detected,
            )

        if captcha_detected:
            return ApplicationEligibility(
                eligible=False,
                decision=ApplicationEligibilityDecision.CAPTCHA_DETECTED,
                reason=(
                    "CAPTCHA was detected. Application requires "
                    "manual intervention."
                ),
                external_job_id=job.external_id,
                source=job.source,
                application_status=ApplicationStatus.CAPTCHA_DETECTED,
                job_active=job_active,
                authentication_required=authentication_required,
                captcha_detected=True,
            )

        if authentication_required:
            return ApplicationEligibility(
                eligible=False,
                decision=(
                    ApplicationEligibilityDecision.AUTHENTICATION_REQUIRED
                ),
                reason=(
                    "Authentication is required before the "
                    "application can continue."
                ),
                external_job_id=job.external_id,
                source=job.source,
                application_status=ApplicationStatus.AUTHENTICATION_REQUIRED,
                job_active=job_active,
                authentication_required=True,
                captcha_detected=captcha_detected,
            )

        if match_decision == DecisionType.SKIP:
            return ApplicationEligibility(
                eligible=False,
                decision=ApplicationEligibilityDecision.SKIP,
                reason=(
                    "Job matching service marked this job as "
                    "not suitable for application."
                ),
                external_job_id=job.external_id,
                source=job.source,
                application_status=ApplicationStatus.SKIPPED,
                job_active=job_active,
            )

        if match_decision == DecisionType.MANUAL_REVIEW:
            return ApplicationEligibility(
                eligible=False,
                decision=ApplicationEligibilityDecision.MANUAL_REVIEW,
                reason=(
                    "Job requires manual review before application."
                ),
                external_job_id=job.external_id,
                source=job.source,
                application_status=ApplicationStatus.MANUAL_REVIEW_REQUIRED,
                job_active=job_active,
            )

        if match_decision != DecisionType.APPLY:
            raise ValidationError(
                f"Unsupported match decision: {match_decision!r}"
            )

        return ApplicationEligibility(
            eligible=True,
            decision=ApplicationEligibilityDecision.QUEUE,
            reason=(
                "Job passed eligibility checks and can enter "
                "the application queue."
            ),
            external_job_id=job.external_id,
            source=job.source,
            application_status=ApplicationStatus.QUEUED,
            job_active=True,
        )

    def evaluate_many(
        self,
        jobs: Iterable[DiscoveredJob],
        *,
        match_decision: DecisionType,
        already_applied_ids: set[str] | None = None,
        inactive_job_ids: set[str] | None = None,
    ) -> tuple[ApplicationEligibility, ...]:
        """
        Evaluate multiple jobs.

        This helper is intentionally deterministic and does not perform
        database or browser operations.
        """

        duplicate_ids = already_applied_ids or set()
        inactive_ids = inactive_job_ids or set()

        results: list[ApplicationEligibility] = []

        for job in jobs:
            results.append(
                self.evaluate(
                    job,
                    match_decision=match_decision,
                    already_applied=job.external_id in duplicate_ids,
                    job_active=job.external_id not in inactive_ids,
                )
            )

        return tuple(results)