"""
Application execution orchestrator integration test.

Verifies:
- EXECUTE plans send only AUTO_ANSWER fields to the filler.
- MANUAL_REVIEW blocks all field filling.
- SKIP blocks all field filling.
- Successful field filling completes execution.
- Failed field filling is reported correctly.
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

from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling import (
    MockLinkedInApplicationFieldFiller,
)

from src.modules.job_discovery.services.application_executor.orchestration import (
    ApplicationExecutionOrchestrator,
)


class FailingMockFieldFiller:
    """Test filler that deliberately fails every approved field."""

    def __init__(self) -> None:
        self.attempted_answers: list[ApplicationAnswer] = []

    async def fill_field(
        self,
        answer: ApplicationAnswer,
    ):
        self.attempted_answers.append(answer)

        from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling import (
            FieldFillResult,
        )

        return FieldFillResult(
            field_id=answer.field_id,
            success=False,
            error_code="test_fill_failure",
            error_message="Intentional integration-test failure.",
        )


def create_auto_answer(
    field_id: str,
    normalized_name: str,
    value: str,
) -> ApplicationAnswer:
    """Create a valid automatic answer."""

    return ApplicationAnswer(
        field_id=field_id,
        normalized_field_name=normalized_name,
        value=value,
        decision=ApplicationAnswerDecision.AUTO_ANSWER,
        confidence=1.0,
        source=ApplicationAnswerSource.CANDIDATE_PROFILE,
        reason="Explicit candidate profile value.",
    )


def create_manual_answer(
    field_id: str,
    normalized_name: str,
) -> ApplicationAnswer:
    """Create a manual-review answer."""

    return ApplicationAnswer(
        field_id=field_id,
        normalized_field_name=normalized_name,
        value="Needs review",
        decision=ApplicationAnswerDecision.MANUAL_REVIEW,
        confidence=0.5,
        source=ApplicationAnswerSource.UNKNOWN,
        reason="Manual review required.",
    )


def create_skip_answer(
    field_id: str,
    normalized_name: str,
) -> ApplicationAnswer:
    """Create a skipped answer."""

    return ApplicationAnswer(
        field_id=field_id,
        normalized_field_name=normalized_name,
        value=None,
        decision=ApplicationAnswerDecision.SKIP,
        confidence=0.0,
        source=ApplicationAnswerSource.UNKNOWN,
        reason="No safe answer available.",
    )


async def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION EXECUTION ORCHESTRATOR INTEGRATION TEST")
    print("=" * 70)

    orchestrator = ApplicationExecutionOrchestrator()

    print()
    print("[1/7] Creating execution orchestrator...")
    print("ORCHESTRATOR creation successful")

    # ==============================================================
    # 2/7
    # ==============================================================

    print()
    print("[2/7] Testing fully executable application...")

    resolution = AnswerResolutionResult(
        answers=(
            create_auto_answer(
                "field-001",
                "first_name",
                "Aravind",
            ),
            create_auto_answer(
                "field-002",
                "email",
                "aravind@example.com",
            ),
            create_auto_answer(
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

    result = await orchestrator.execute(
        application_id="orch-test-001",
        external_job_id="job-001",
        resolution=resolution,
        field_filler=filler,
    )

    assert (
        result.plan.decision
        == ApplicationExecutionDecision.EXECUTE
    )

    assert result.completed is True
    assert result.attempted_fields == 3
    assert result.successful_fields == 3
    assert result.failed_fields == 0
    assert filler.fill_count == 3

    print("EXECUTE orchestration successful")
    print("Decision:", result.plan.decision.value)
    print("Attempted:", result.attempted_fields)
    print("Successful:", result.successful_fields)
    print("Completed:", result.completed)

    # ==============================================================
    # 3/7
    # ==============================================================

    print()
    print("[3/7] Testing manual-review safety gate...")

    resolution = AnswerResolutionResult(
        answers=(
            create_auto_answer(
                "field-004",
                "first_name",
                "Aravind",
            ),
            create_manual_answer(
                "field-005",
                "work_authorization",
            ),
        ),
        auto_answer_count=1,
        manual_review_count=1,
        skipped_count=0,
    )

    filler = MockLinkedInApplicationFieldFiller()

    result = await orchestrator.execute(
        application_id="orch-test-002",
        external_job_id="job-002",
        resolution=resolution,
        field_filler=filler,
    )

    assert (
        result.plan.decision
        == ApplicationExecutionDecision.MANUAL_REVIEW
    )

    assert result.completed is False
    assert result.attempted_fields == 0
    assert result.successful_fields == 0
    assert filler.fill_count == 0
    assert result.manual_intervention_required is True

    print("MANUAL REVIEW safety gate successful")
    print("Decision:", result.plan.decision.value)
    print("Fields attempted:", result.attempted_fields)
    print("Manual intervention:", result.manual_intervention_required)

    # ==============================================================
    # 4/7
    # ==============================================================

    print()
    print("[4/7] Testing skip safety gate...")

    resolution = AnswerResolutionResult(
        answers=(
            create_skip_answer(
                "field-006",
                "unknown",
            ),
        ),
        auto_answer_count=0,
        manual_review_count=0,
        skipped_count=1,
    )

    filler = MockLinkedInApplicationFieldFiller()

    result = await orchestrator.execute(
        application_id="orch-test-003",
        external_job_id="job-003",
        resolution=resolution,
        field_filler=filler,
    )

    assert (
        result.plan.decision
        == ApplicationExecutionDecision.SKIP
    )

    assert result.completed is False
    assert result.attempted_fields == 0
    assert filler.fill_count == 0

    print("SKIP safety gate successful")
    print("Decision:", result.plan.decision.value)
    print("Fields attempted:", result.attempted_fields)

    # ==============================================================
    # 5/7
    # ==============================================================

    print()
    print("[5/7] Testing mixed AUTO_ANSWER + SKIP fields...")

    resolution = AnswerResolutionResult(
        answers=(
            create_auto_answer(
                "field-007",
                "email",
                "aravind@example.com",
            ),
            create_skip_answer(
                "field-008",
                "unknown",
            ),
        ),
        auto_answer_count=1,
        manual_review_count=0,
        skipped_count=1,
    )

    filler = MockLinkedInApplicationFieldFiller()

    result = await orchestrator.execute(
        application_id="orch-test-004",
        external_job_id="job-004",
        resolution=resolution,
        field_filler=filler,
    )

    assert (
        result.plan.decision
        == ApplicationExecutionDecision.EXECUTE
    )

    assert result.completed is True
    assert result.attempted_fields == 1
    assert result.successful_fields == 1
    assert result.failed_fields == 0
    assert filler.fill_count == 1

    print("AUTO + SKIP orchestration successful")
    print("Decision:", result.plan.decision.value)
    print("Auto fields filled:", filler.fill_count)
    print("Skipped fields:", result.plan.skipped_fields)

    # ==============================================================
    # 6/7
    # ==============================================================

    print()
    print("[6/7] Testing browser field failure handling...")

    resolution = AnswerResolutionResult(
        answers=(
            create_auto_answer(
                "field-009",
                "email",
                "aravind@example.com",
            ),
            create_auto_answer(
                "field-010",
                "phone",
                "+91 9000000000",
            ),
        ),
        auto_answer_count=2,
        manual_review_count=0,
        skipped_count=0,
    )

    failing_filler = FailingMockFieldFiller()

    result = await orchestrator.execute(
        application_id="orch-test-005",
        external_job_id="job-005",
        resolution=resolution,
        field_filler=failing_filler,
    )

    assert (
        result.plan.decision
        == ApplicationExecutionDecision.EXECUTE
    )

    assert result.completed is False
    assert result.attempted_fields == 2
    assert result.successful_fields == 0
    assert result.failed_fields == 2
    assert len(failing_filler.attempted_answers) == 2

    print("FIELD FAILURE handling successful")
    print("Attempted:", result.attempted_fields)
    print("Successful:", result.successful_fields)
    print("Failed:", result.failed_fields)

    # ==============================================================
    # 7/7
    # ==============================================================

    print()
    print("[7/7] Testing AUTO_ANSWER boundary protection...")

    resolution = AnswerResolutionResult(
        answers=(
            create_auto_answer(
                "field-011",
                "first_name",
                "Aravind",
            ),
            create_manual_answer(
                "field-012",
                "sponsorship",
            ),
            create_skip_answer(
                "field-013",
                "unknown",
            ),
        ),
        auto_answer_count=1,
        manual_review_count=1,
        skipped_count=1,
    )

    filler = MockLinkedInApplicationFieldFiller()

    result = await orchestrator.execute(
        application_id="orch-test-006",
        external_job_id="job-006",
        resolution=resolution,
        field_filler=filler,
    )

    # Because manual review exists, execution must be blocked
    # completely. The AUTO_ANSWER must not be filled either.
    assert (
        result.plan.decision
        == ApplicationExecutionDecision.MANUAL_REVIEW
    )

    assert result.attempted_fields == 0
    assert filler.fill_count == 0

    print("EXECUTION boundary protection successful")
    print("Manual review prevented all browser interaction")

    print()
    print("=" * 70)
    print("APPLICATION EXECUTION ORCHESTRATOR TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())