"""
Application execution workflow.

Coordinates:

    Answer Resolution
        ↓
    Execution Planning
        ↓
    Field Filling
        ↓
    Submission
        ↓
    Final Result

This workflow does not contain portal-specific browser logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.modules.job_discovery.domain.application_executor.answers import (
    AnswerResolutionResult,
)

from src.modules.job_discovery.domain.application_executor.planning import (
    ApplicationExecutionDecision,
)

from src.modules.job_discovery.domain.application_executor.submission import (
    ApplicationSubmissionResult,
    ApplicationSubmissionStatus,
)

from src.modules.job_discovery.services.application_executor.orchestration import (
    ApplicationExecutionOrchestrator,
)

from src.modules.job_discovery.services.application_executor.submission import (
    ApplicationSubmissionService,
)


@dataclass(frozen=True)
class ApplicationExecutionWorkflowResult:
    """Final result of the complete application workflow."""

    application_id: str
    external_job_id: str

    execution_decision: ApplicationExecutionDecision

    fields_attempted: int = 0
    fields_successful: int = 0
    fields_failed: int = 0

    submission: ApplicationSubmissionResult | None = None

    completed: bool = False
    manual_intervention_required: bool = False

    reason: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class ApplicationExecutionWorkflow:
    """
    Coordinates application execution and final submission.

    Submission is attempted only when:

    1. Execution planning returns EXECUTE.
    2. Approved fields are successfully filled.
    3. At least one field was successfully verified.
    """

    def __init__(
        self,
        execution_orchestrator: ApplicationExecutionOrchestrator | None = None,
        submission_service: ApplicationSubmissionService | None = None,
    ) -> None:
        self._execution_orchestrator = (
            execution_orchestrator
            or ApplicationExecutionOrchestrator()
        )

        self._submission_service = (
            submission_service
            or ApplicationSubmissionService()
        )

    async def run(
        self,
        *,
        application_id: str,
        external_job_id: str,
        resolution: AnswerResolutionResult,
        field_filler: Any,
    ) -> ApplicationExecutionWorkflowResult:
        """
        Execute the complete application workflow.

        The workflow stops before submission when execution is blocked
        or any approved field fails to fill.
        """

        execution_result = (
            await self._execution_orchestrator.execute(
                application_id=application_id,
                external_job_id=external_job_id,
                resolution=resolution,
                field_filler=field_filler,
            )
        )

        # ----------------------------------------------------------
        # Execution blocked
        # ----------------------------------------------------------

        if (
            execution_result.plan.decision
            != ApplicationExecutionDecision.EXECUTE
        ):
            return ApplicationExecutionWorkflowResult(
                application_id=application_id,
                external_job_id=external_job_id,
                execution_decision=(
                    execution_result.plan.decision
                ),
                fields_attempted=(
                    execution_result.attempted_fields
                ),
                fields_successful=(
                    execution_result.successful_fields
                ),
                fields_failed=(
                    execution_result.failed_fields
                ),
                completed=False,
                manual_intervention_required=(
                    execution_result.manual_intervention_required
                ),
                reason=execution_result.reason,
                metadata={
                    "submission_attempted": False,
                    "execution_blocked": True,
                },
            )

        # ----------------------------------------------------------
        # Field filling failed
        # ----------------------------------------------------------

        if execution_result.failed_fields > 0:
            return ApplicationExecutionWorkflowResult(
                application_id=application_id,
                external_job_id=external_job_id,
                execution_decision=(
                    execution_result.plan.decision
                ),
                fields_attempted=(
                    execution_result.attempted_fields
                ),
                fields_successful=(
                    execution_result.successful_fields
                ),
                fields_failed=(
                    execution_result.failed_fields
                ),
                completed=False,
                manual_intervention_required=True,
                reason=(
                    "Application submission was blocked because "
                    "one or more approved fields failed."
                ),
                metadata={
                    "submission_attempted": False,
                    "execution_failed": True,
                },
            )

        # ----------------------------------------------------------
        # No successfully verified fields
        # ----------------------------------------------------------

        if execution_result.successful_fields <= 0:
            return ApplicationExecutionWorkflowResult(
                application_id=application_id,
                external_job_id=external_job_id,
                execution_decision=(
                    execution_result.plan.decision
                ),
                fields_attempted=(
                    execution_result.attempted_fields
                ),
                fields_successful=(
                    execution_result.successful_fields
                ),
                fields_failed=(
                    execution_result.failed_fields
                ),
                completed=False,
                manual_intervention_required=True,
                reason=(
                    "Application submission was blocked because "
                    "no fields were successfully verified."
                ),
                metadata={
                    "submission_attempted": False,
                    "no_verified_fields": True,
                },
            )

        # ----------------------------------------------------------
        # Submission
        # ----------------------------------------------------------

        from src.modules.job_discovery.domain.application_executor.submission import (
            ApplicationSubmissionRequest,
        )

        submission_request = ApplicationSubmissionRequest(
            application_id=application_id,
            external_job_id=external_job_id,
            verified_field_count=(
                execution_result.successful_fields
            ),
        )

        submission_result = (
            await self._submission_service.submit(
                submission_request
            )
        )

        # ----------------------------------------------------------
        # Successful completion
        # ----------------------------------------------------------

        if (
            submission_result.status
            == ApplicationSubmissionStatus.SUBMITTED
            and submission_result.submitted
        ):
            return ApplicationExecutionWorkflowResult(
                application_id=application_id,
                external_job_id=external_job_id,
                execution_decision=(
                    execution_result.plan.decision
                ),
                fields_attempted=(
                    execution_result.attempted_fields
                ),
                fields_successful=(
                    execution_result.successful_fields
                ),
                fields_failed=(
                    execution_result.failed_fields
                ),
                submission=submission_result,
                completed=True,
                manual_intervention_required=False,
                reason=(
                    "Application fields were successfully "
                    "verified and the application was submitted."
                ),
                metadata={
                    "submission_attempted": True,
                    "submission_successful": True,
                    "confirmation_id": (
                        submission_result.confirmation_id
                    ),
                },
            )

        # ----------------------------------------------------------
        # Submission failed or requires intervention
        # ----------------------------------------------------------

        return ApplicationExecutionWorkflowResult(
            application_id=application_id,
            external_job_id=external_job_id,
            execution_decision=(
                execution_result.plan.decision
            ),
            fields_attempted=(
                execution_result.attempted_fields
            ),
            fields_successful=(
                execution_result.successful_fields
            ),
            fields_failed=(
                execution_result.failed_fields
            ),
            submission=submission_result,
            completed=False,
            manual_intervention_required=(
                submission_result.manual_intervention_required
                or submission_result.status
                != ApplicationSubmissionStatus.SUBMITTED
            ),
            reason=(
                submission_result.error_message
                or "Application submission did not complete."
            ),
            metadata={
                "submission_attempted": True,
                "submission_successful": False,
            },
        )