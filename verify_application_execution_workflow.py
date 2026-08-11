"""
Application execution workflow integration test.

Tests the complete execution-to-submission workflow without using
a real job portal.
"""

from __future__ import annotations

import asyncio

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
    ApplicationAnswerDecision,
    ApplicationAnswerSource,
    AnswerResolutionResult,
)

from src.modules.job_discovery.domain.application_executor.planning import (
    ApplicationExecutionDecision,
)

from src.modules.job_discovery.domain.application_executor.submission import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionResult,
    ApplicationSubmissionStatus,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling import (
    MockLinkedInApplicationFieldFiller,
)

from src.modules.job_discovery.services.application_executor.submission import (
    ApplicationSubmissionService,
)

from src.modules.job_discovery.services.application_executor.workflow import (
    ApplicationExecutionWorkflow,
)


class MockApplicationSubmitter:
    """Controlled submission implementation for integration tests."""

    def __init__(self, should_succeed: bool = True) -> None:
        self.should_succeed = should_succeed
        self.requests: list[
            ApplicationSubmissionRequest
        ] = []

    async def submit(
        self,
        request: ApplicationSubmissionRequest,
    ) -> ApplicationSubmissionResult:
        self.requests.append(request)

        if not self.should_succeed:
            return ApplicationSubmissionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                status=ApplicationSubmissionStatus.FAILED,
                submitted=False,
                verified_field_count=(
                    request.verified_field_count
                ),
                error_code="mock_submission_failed",
                error_message=(
                    "Intentional workflow test submission failure."
                ),
            )

        return ApplicationSubmissionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            status=ApplicationSubmissionStatus.SUBMITTED,
            submitted=True,
            verified_field_count=(
                request.verified_field_count
            ),
            confirmation_id="workflow-confirmation-001",
        )


def auto_answer(
    field_id: str,
    name: str,
    value: str,
) -> ApplicationAnswer:
    return ApplicationAnswer(
        field_id=field_id,
        normalized_field_name=name,
        value=value,
        decision=ApplicationAnswerDecision.AUTO_ANSWER,
        confidence=1.0,
        source=ApplicationAnswerSource.CANDIDATE_PROFILE,
        reason="Explicit candidate profile value.",
    )


def manual_answer(
    field_id: str,
    name: str,
) -> ApplicationAnswer:
    return ApplicationAnswer(
        field_id=field_id,
        normalized_field_name=name,
        value=None,
        decision=ApplicationAnswerDecision.MANUAL_REVIEW,
        confidence=0.5,
        source=ApplicationAnswerSource.UNKNOWN,
        reason="Manual review required.",
    )


async def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION EXECUTION WORKFLOW INTEGRATION TEST")
    print("=" * 70)

    # --------------------------------------------------------------
    # 1/6
    # --------------------------------------------------------------

    print()
    print("[1/6] Creating complete workflow...")

    submitter = MockApplicationSubmitter(
        should_succeed=True
    )

    submission_service = ApplicationSubmissionService(
        submitter=submitter
    )

    workflow = ApplicationExecutionWorkflow(
        submission_service=submission_service
    )

    print("WORKFLOW creation successful")

    # --------------------------------------------------------------
    # 2/6
    # --------------------------------------------------------------

    print()
    print("[2/6] Testing complete successful workflow...")

    resolution = AnswerResolutionResult(
        answers=(
            auto_answer(
                "field-001",
                "first_name",
                "Aravind",
            ),
            auto_answer(
                "field-002",
                "email",
                "aravind@example.com",
            ),
            auto_answer(
                "field-003",
                "location",
                "Hyderabad",
            ),
        ),
        auto_answer_count=3,
        manual_review_count=0,
        skipped_count=0,
    )

    filler = MockLinkedInApplicationFieldFiller()

    result = await workflow.run(
        application_id="workflow-test-001",
        external_job_id="job-001",
        resolution=resolution,
        field_filler=filler,
    )

    assert (
        result.execution_decision
        == ApplicationExecutionDecision.EXECUTE
    )

    assert result.fields_attempted == 3
    assert result.fields_successful == 3
    assert result.fields_failed == 0

    assert result.submission is not None

    assert (
        result.submission.status
        == ApplicationSubmissionStatus.SUBMITTED
    )

    assert result.submission.submitted is True

    assert (
        result.submission.confirmation_id
        == "workflow-confirmation-001"
    )

    assert result.completed is True
    assert result.manual_intervention_required is False

    assert filler.fill_count == 3
    assert len(submitter.requests) == 1

    assert (
        submitter.requests[0].verified_field_count
        == 3
    )

    print("COMPLETE workflow successful")
    print(
        "Execution:",
        result.execution_decision.value,
    )
    print(
        "Fields:",
        result.fields_successful,
    )
    print(
        "Submission:",
        result.submission.status.value,
    )
    print(
        "Confirmation:",
        result.submission.confirmation_id,
    )

    # --------------------------------------------------------------
    # 3/6
    # --------------------------------------------------------------

    print()
    print("[3/6] Testing manual-review workflow protection...")

    submitter = MockApplicationSubmitter(
        should_succeed=True
    )

    submission_service = ApplicationSubmissionService(
        submitter=submitter
    )

    workflow = ApplicationExecutionWorkflow(
        submission_service=submission_service
    )

    resolution = AnswerResolutionResult(
        answers=(
            auto_answer(
                "field-004",
                "first_name",
                "Aravind",
            ),
            manual_answer(
                "field-005",
                "work_authorization",
            ),
        ),
        auto_answer_count=1,
        manual_review_count=1,
        skipped_count=0,
    )

    filler = MockLinkedInApplicationFieldFiller()

    result = await workflow.run(
        application_id="workflow-test-002",
        external_job_id="job-002",
        resolution=resolution,
        field_filler=filler,
    )

    assert (
        result.execution_decision
        == ApplicationExecutionDecision.MANUAL_REVIEW
    )

    assert result.completed is False
    assert result.submission is None

    assert result.manual_intervention_required is True

    assert filler.fill_count == 0
    assert len(submitter.requests) == 0

    print("MANUAL REVIEW protection successful")
    print(
        "Decision:",
        result.execution_decision.value,
    )
    print("Browser fills:", filler.fill_count)
    print("Submission attempts:", len(submitter.requests))

    # --------------------------------------------------------------
    # 4/6
    # --------------------------------------------------------------

    print()
    print("[4/6] Testing field-failure submission protection...")

    submitter = MockApplicationSubmitter(
        should_succeed=True
    )

    submission_service = ApplicationSubmissionService(
        submitter=submitter
    )

    workflow = ApplicationExecutionWorkflow(
        submission_service=submission_service
    )

    class FailingFiller:
        def __init__(self) -> None:
            self.fill_attempts = 0

        async def fill_field(self, answer):
            self.fill_attempts += 1

            from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling import (
                FieldFillResult,
            )

            return FieldFillResult(
                field_id=answer.field_id,
                success=False,
                error_code="workflow_test_fill_failed",
                error_message="Intentional failure.",
            )

    resolution = AnswerResolutionResult(
        answers=(
            auto_answer(
                "field-006",
                "email",
                "aravind@example.com",
            ),
        ),
        auto_answer_count=1,
        manual_review_count=0,
        skipped_count=0,
    )

    filler = FailingFiller()

    result = await workflow.run(
        application_id="workflow-test-003",
        external_job_id="job-003",
        resolution=resolution,
        field_filler=filler,
    )

    assert result.completed is False
    assert result.fields_failed == 1
    assert result.submission is None
    assert result.manual_intervention_required is True

    assert filler.fill_attempts == 1
    assert len(submitter.requests) == 0

    print("FIELD FAILURE protection successful")
    print("Failed fields:", result.fields_failed)
    print("Submission attempts:", len(submitter.requests))

    # --------------------------------------------------------------
    # 5/6
    # --------------------------------------------------------------

    print()
    print("[5/6] Testing submission failure propagation...")

    submitter = MockApplicationSubmitter(
        should_succeed=False
    )

    submission_service = ApplicationSubmissionService(
        submitter=submitter
    )

    workflow = ApplicationExecutionWorkflow(
        submission_service=submission_service
    )

    resolution = AnswerResolutionResult(
        answers=(
            auto_answer(
                "field-007",
                "first_name",
                "Aravind",
            ),
            auto_answer(
                "field-008",
                "email",
                "aravind@example.com",
            ),
        ),
        auto_answer_count=2,
        manual_review_count=0,
        skipped_count=0,
    )

    filler = MockLinkedInApplicationFieldFiller()

    result = await workflow.run(
        application_id="workflow-test-004",
        external_job_id="job-004",
        resolution=resolution,
        field_filler=filler,
    )

    assert result.completed is False

    assert result.submission is not None

    assert (
        result.submission.status
        == ApplicationSubmissionStatus.FAILED
    )

    assert result.submission.submitted is False

    assert result.manual_intervention_required is True

    assert filler.fill_count == 2
    assert len(submitter.requests) == 1

    print("SUBMISSION FAILURE propagation successful")
    print(
        "Submission:",
        result.submission.status.value,
    )
    print(
        "Error:",
        result.submission.error_code,
    )

    # --------------------------------------------------------------
    # 6/6
    # --------------------------------------------------------------

    print()
    print("[6/6] Testing final success boundary...")

    submitter = MockApplicationSubmitter(
        should_succeed=True
    )

    submission_service = ApplicationSubmissionService(
        submitter=submitter
    )

    workflow = ApplicationExecutionWorkflow(
        submission_service=submission_service
    )

    resolution = AnswerResolutionResult(
        answers=(
            auto_answer(
                "field-009",
                "first_name",
                "Aravind",
            ),
        ),
        auto_answer_count=1,
        manual_review_count=0,
        skipped_count=0,
    )

    filler = MockLinkedInApplicationFieldFiller()

    result = await workflow.run(
        application_id="workflow-test-005",
        external_job_id="job-005",
        resolution=resolution,
        field_filler=filler,
    )

    assert result.completed is True

    assert (
        result.submission is not None
    )

    assert (
        result.submission.status
        == ApplicationSubmissionStatus.SUBMITTED
    )

    assert result.submission.submitted is True

    assert (
        result.submission.confirmation_id
        is not None
    )

    assert (
        result.metadata["submission_successful"]
        is True
    )

    print("FINAL SUCCESS boundary successful")
    print("Workflow completed:", result.completed)
    print(
        "Confirmation:",
        result.submission.confirmation_id,
    )

    print()
    print("=" * 70)
    print("APPLICATION EXECUTION WORKFLOW TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())