"""
Application execution planning service.

Converts answer-resolution results into a safe execution plan.

This service does not interact with Playwright and does not submit
applications.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor.answers import (
    AnswerResolutionResult,
)
from src.modules.job_discovery.domain.application_executor.planning import (
    ApplicationExecutionDecision,
    ApplicationExecutionPlan,
)


class ApplicationExecutionPlanningService:
    """
    Builds an execution plan from resolved application answers.

    Execution is allowed only when every detected field has a safe
    automatic answer.
    """

    def create_plan(
        self,
        *,
        application_id: str,
        external_job_id: str,
        resolution: AnswerResolutionResult,
    ) -> ApplicationExecutionPlan:
        """
        Create an execution plan from an answer-resolution result.
        """

        if not application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        if not external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        total_fields = len(resolution.answers)

        # ----------------------------------------------------------
        # Manual review takes priority over execution.
        # ----------------------------------------------------------

        if resolution.manual_review_count > 0:
            return ApplicationExecutionPlan(
                application_id=application_id,
                external_job_id=external_job_id,
                decision=ApplicationExecutionDecision.MANUAL_REVIEW,
                total_fields=total_fields,
                auto_answer_fields=resolution.auto_answer_count,
                manual_review_fields=resolution.manual_review_count,
                skipped_fields=resolution.skipped_count,
                reason=(
                    "One or more application fields require "
                    "manual review before execution."
                ),
            )

        # ----------------------------------------------------------
        # Nothing can be safely answered.
        # ----------------------------------------------------------

        if resolution.auto_answer_count == 0:
            return ApplicationExecutionPlan(
                application_id=application_id,
                external_job_id=external_job_id,
                decision=ApplicationExecutionDecision.SKIP,
                total_fields=total_fields,
                auto_answer_fields=0,
                manual_review_fields=0,
                skipped_fields=resolution.skipped_count,
                reason=(
                    "No application fields have a safe automatic "
                    "answer."
                ),
            )

        # ----------------------------------------------------------
        # Safe execution.
        # ----------------------------------------------------------

        return ApplicationExecutionPlan(
            application_id=application_id,
            external_job_id=external_job_id,
            decision=ApplicationExecutionDecision.EXECUTE,
            total_fields=total_fields,
            auto_answer_fields=resolution.auto_answer_count,
            manual_review_fields=0,
            skipped_fields=resolution.skipped_count,
            reason=(
                "All required application fields have safe "
                "automatic answers."
            ),
        )