"""
Application execution orchestration.

Coordinates answer resolution, execution planning, and browser-backed
field filling.

This layer does not contain browser-specific logic and does not submit
applications. It only coordinates already-approved execution steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.modules.job_discovery.domain.application_executor.answers import (
    AnswerResolutionResult,
)
from src.modules.job_discovery.domain.application_executor.planning import (
    ApplicationExecutionDecision,
    ApplicationExecutionPlan,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling.field_filler import (
    FieldFillResult,
)
from src.modules.job_discovery.services.application_executor.planning import (
    ApplicationExecutionPlanningService,
)


@dataclass(frozen=True)
class ApplicationExecutionOrchestrationResult:
    """Result returned by the execution orchestrator."""

    application_id: str
    external_job_id: str
    plan: ApplicationExecutionPlan

    attempted_fields: int = 0
    successful_fields: int = 0
    failed_fields: int = 0

    field_results: tuple[FieldFillResult, ...] = ()

    completed: bool = False
    manual_intervention_required: bool = False

    reason: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class ApplicationExecutionOrchestrator:
    """
    Coordinates application execution planning and field filling.

    The orchestrator enforces the following safety boundary:

    EXECUTE
        -> only AUTO_ANSWER fields are sent to the filler.

    MANUAL_REVIEW
        -> no fields are filled.

    SKIP
        -> no fields are filled.
    """

    def __init__(
        self,
        planning_service: ApplicationExecutionPlanningService | None = None,
    ) -> None:
        self._planning_service = (
            planning_service
            or ApplicationExecutionPlanningService()
        )

    def build_plan(
        self,
        *,
        application_id: str,
        external_job_id: str,
        resolution: AnswerResolutionResult,
    ) -> ApplicationExecutionPlan:
        """
        Build an execution plan from the answer-resolution result.
        """

        return self._planning_service.create_plan(
            application_id=application_id,
            external_job_id=external_job_id,
            resolution=resolution,
        )

    async def execute(
        self,
        *,
        application_id: str,
        external_job_id: str,
        resolution: AnswerResolutionResult,
        field_filler: Any,
    ) -> ApplicationExecutionOrchestrationResult:
        """
        Execute approved application answers.

        No browser interaction occurs unless the execution plan is
        EXECUTE.
        """

        plan = self.build_plan(
            application_id=application_id,
            external_job_id=external_job_id,
            resolution=resolution,
        )

        # ----------------------------------------------------------
        # Safety gate
        # ----------------------------------------------------------

        if plan.decision != ApplicationExecutionDecision.EXECUTE:
            manual_intervention_required = (
                plan.decision
                == ApplicationExecutionDecision.MANUAL_REVIEW
            )

            return ApplicationExecutionOrchestrationResult(
                application_id=application_id,
                external_job_id=external_job_id,
                plan=plan,
                attempted_fields=0,
                successful_fields=0,
                failed_fields=0,
                field_results=(),
                completed=False,
                manual_intervention_required=(
                    manual_intervention_required
                ),
                reason=plan.reason,
                metadata={
                    "execution_blocked": True,
                    "decision": plan.decision.value,
                },
            )

        # ----------------------------------------------------------
        # Execute approved fields only
        # ----------------------------------------------------------

        approved_answers = tuple(
            answer
            for answer in resolution.answers
            if answer.decision.value == "auto_answer"
        )

        field_results: list[FieldFillResult] = []

        for answer in approved_answers:
            result = await field_filler.fill_field(answer)
            field_results.append(result)

        successful_fields = sum(
            1
            for result in field_results
            if result.success
        )

        failed_fields = len(field_results) - successful_fields

        completed = (
            len(field_results) > 0
            and failed_fields == 0
        )

        if failed_fields > 0:
            reason = (
                "One or more approved application fields "
                "failed during browser execution."
            )
        elif completed:
            reason = (
                "All approved application fields were "
                "filled successfully."
            )
        else:
            reason = (
                "Execution plan allowed execution, but "
                "there were no approved fields to fill."
            )

        return ApplicationExecutionOrchestrationResult(
            application_id=application_id,
            external_job_id=external_job_id,
            plan=plan,
            attempted_fields=len(field_results),
            successful_fields=successful_fields,
            failed_fields=failed_fields,
            field_results=tuple(field_results),
            completed=completed,
            manual_intervention_required=False,
            reason=reason,
            metadata={
                "execution_blocked": False,
                "decision": plan.decision.value,
            },
        )