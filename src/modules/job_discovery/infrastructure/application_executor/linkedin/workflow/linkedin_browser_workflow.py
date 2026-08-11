"""
LinkedIn browser execution workflow.

Coordinates:

    Form Detection
        ↓
    Answer Resolution
        ↓
    Execution Planning
        ↓
    Approved Field Filling
        ↓
    Application Submission

This component is asynchronous because it owns the Playwright
browser boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.modules.job_discovery.domain.application_executor.answers import (
    AnswerResolutionResult,
)

from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormType,
)

from src.modules.job_discovery.domain.application_executor.submission import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionResult,
    ApplicationSubmissionStatus,
)

from src.modules.job_discovery.services.application_executor.orchestration import (
    ApplicationExecutionOrchestrator,
)

from src.modules.job_discovery.services.application_executor.submission import (
    ApplicationSubmissionService,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.form import (
    LinkedInApplicationFormDetector,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling import (
    PlaywrightLinkedInApplicationFieldFiller,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.submission import (
    PlaywrightLinkedInApplicationSubmitter,
)


@dataclass(frozen=True)
class LinkedInBrowserExecutionResult:
    """Normalized result from the LinkedIn browser workflow."""

    application_id: str
    external_job_id: str

    form_type: ApplicationFormType

    fields_detected: int = 0
    fields_filled: int = 0
    fields_failed: int = 0

    submission: ApplicationSubmissionResult | None = None

    completed: bool = False
    requires_manual_intervention: bool = False

    reason: str = ""
    error_code: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class LinkedInBrowserExecutionWorkflow:
    """
    Coordinates the already-tested LinkedIn browser components.

    This class does not bypass authentication, CAPTCHA, or manual
    review states.
    """

    def __init__(
        self,
        *,
        execution_orchestrator: (
            ApplicationExecutionOrchestrator | None
        ) = None,
        submission_service: (
            ApplicationSubmissionService | None
        ) = None,
    ) -> None:

        self._execution_orchestrator = (
            execution_orchestrator
            or ApplicationExecutionOrchestrator()
        )

        self._submission_service = (
            submission_service
            or ApplicationSubmissionService()
        )

    async def execute(
        self,
        *,
        application_id: str,
        external_job_id: str,
        page: Any,
        resolution: AnswerResolutionResult,
    ) -> LinkedInBrowserExecutionResult:
        """
        Execute the LinkedIn browser workflow.

        The page must already be loaded at the intended application
        URL. Authentication and CAPTCHA are never bypassed.
        """

        # ----------------------------------------------------------
        # 1. Detect application form
        # ----------------------------------------------------------

        detector = LinkedInApplicationFormDetector(
            page
        )

        snapshot = await detector.detect_async()

        form_type = snapshot.form_type

        # ----------------------------------------------------------
        # Authentication
        # ----------------------------------------------------------

        if (
            form_type
            == ApplicationFormType.AUTHENTICATION_REQUIRED
        ):
            return LinkedInBrowserExecutionResult(
                application_id=application_id,
                external_job_id=external_job_id,
                form_type=form_type,
                requires_manual_intervention=True,
                reason=(
                    "LinkedIn authentication is required "
                    "before the application can continue."
                ),
                error_code="authentication_required",
                metadata={
                    "form_detected": False,
                },
            )

        # ----------------------------------------------------------
        # CAPTCHA
        # ----------------------------------------------------------

        if (
            form_type
            == ApplicationFormType.CAPTCHA_DETECTED
        ):
            return LinkedInBrowserExecutionResult(
                application_id=application_id,
                external_job_id=external_job_id,
                form_type=form_type,
                requires_manual_intervention=True,
                reason=(
                    "CAPTCHA detected. Manual intervention "
                    "is required."
                ),
                error_code="captcha_detected",
                metadata={
                    "form_detected": False,
                },
            )

        # ----------------------------------------------------------
        # External application
        # ----------------------------------------------------------

        if (
            form_type
            == ApplicationFormType.EXTERNAL_APPLICATION
        ):
            return LinkedInBrowserExecutionResult(
                application_id=application_id,
                external_job_id=external_job_id,
                form_type=form_type,
                fields_detected=0,
                requires_manual_intervention=True,
                reason=(
                    "Application redirects to an external "
                    "application flow."
                ),
                error_code="external_application",
                metadata={
                    "external_application": True,
                },
            )

        # ----------------------------------------------------------
        # Unknown flow
        # ----------------------------------------------------------

        if (
            form_type
            != ApplicationFormType.EASY_APPLY
        ):
            return LinkedInBrowserExecutionResult(
                application_id=application_id,
                external_job_id=external_job_id,
                form_type=form_type,
                fields_detected=0,
                requires_manual_intervention=True,
                reason=(
                    "LinkedIn application flow could not "
                    "be safely recognized."
                ),
                error_code="unknown_application_flow",
            )

        # ----------------------------------------------------------
        # Easy Apply detected
        # ----------------------------------------------------------

        fields_detected = len(
            snapshot.fields
        )

        # ----------------------------------------------------------
        # Execution planning / field filling
        # ----------------------------------------------------------

        field_filler = (
            PlaywrightLinkedInApplicationFieldFiller(
                page
            )
        )

        execution_result = (
            await self._execution_orchestrator.execute(
                application_id=application_id,
                external_job_id=external_job_id,
                resolution=resolution,
                field_filler=field_filler,
            )
        )

        # ----------------------------------------------------------
        # Execution safety gate
        # ----------------------------------------------------------

        if not execution_result.completed:
            return LinkedInBrowserExecutionResult(
                application_id=application_id,
                external_job_id=external_job_id,
                form_type=form_type,
                fields_detected=fields_detected,
                fields_filled=(
                    execution_result.successful_fields
                ),
                fields_failed=(
                    execution_result.failed_fields
                ),
                completed=False,
                requires_manual_intervention=(
                    execution_result.manual_intervention_required
                    or execution_result.plan.decision.value
                    == "manual_review"
                ),
                reason=execution_result.reason,
                error_code=(
                    "execution_blocked"
                    if execution_result.plan.decision.value
                    != "execute"
                    else "field_execution_failed"
                ),
                metadata={
                    "execution_decision": (
                        execution_result.plan.decision.value
                    ),
                    "submission_attempted": False,
                },
            )

        # ----------------------------------------------------------
        # Submission
        # ----------------------------------------------------------

        submitter = (
            PlaywrightLinkedInApplicationSubmitter(
                page
            )
        )

        submission_service = (
            self._submission_service
        )

        # The default submission service may not have a
        # submitter configured. Build a browser-backed service
        # for this workflow when necessary.
        if not submission_service.submitter_configured:
            submission_service = (
                ApplicationSubmissionService(
                    submitter=submitter
                )
            )

        request = ApplicationSubmissionRequest(
            application_id=application_id,
            external_job_id=external_job_id,
            verified_field_count=(
                execution_result.successful_fields
            ),
        )

        submission_result = (
            await submission_service.submit(
                request
            )
        )

        # ----------------------------------------------------------
        # Final success boundary
        # ----------------------------------------------------------

        if (
            submission_result.status
            == ApplicationSubmissionStatus.SUBMITTED
            and submission_result.submitted
            and submission_result.confirmation_id
        ):
            return LinkedInBrowserExecutionResult(
                application_id=application_id,
                external_job_id=external_job_id,
                form_type=form_type,
                fields_detected=fields_detected,
                fields_filled=(
                    execution_result.successful_fields
                ),
                fields_failed=(
                    execution_result.failed_fields
                ),
                submission=submission_result,
                completed=True,
                requires_manual_intervention=False,
                reason=(
                    "LinkedIn application was successfully "
                    "submitted and confirmed."
                ),
                metadata={
                    "execution_decision": "execute",
                    "submission_attempted": True,
                    "submission_successful": True,
                    "confirmation_id": (
                        submission_result.confirmation_id
                    ),
                },
            )

        # ----------------------------------------------------------
        # Submission failed
        # ----------------------------------------------------------

        return LinkedInBrowserExecutionResult(
            application_id=application_id,
            external_job_id=external_job_id,
            form_type=form_type,
            fields_detected=fields_detected,
            fields_filled=(
                execution_result.successful_fields
            ),
            fields_failed=(
                execution_result.failed_fields
            ),
            submission=submission_result,
            completed=False,
            requires_manual_intervention=True,
            reason=(
                submission_result.error_message
                or "LinkedIn submission did not complete."
            ),
            error_code=(
                submission_result.error_code
                or "submission_failed"
            ),
            metadata={
                "execution_decision": "execute",
                "submission_attempted": True,
                "submission_successful": False,
            },
        )