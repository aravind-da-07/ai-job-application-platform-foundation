"""
Application Execution Planning Service integration test.

Verifies:
- safe answers -> EXECUTE
- manual-review answers -> MANUAL_REVIEW
- only skipped answers -> SKIP
- mixed answers -> MANUAL_REVIEW
- plan counters and safety properties
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
    ApplicationAnswerDecision,
    ApplicationAnswerSource,
    AnswerResolutionResult,
)
from src.modules.job_discovery.domain.application_executor.planning import (
    ApplicationExecutionDecision,
)
from src.modules.job_discovery.services.application_executor.planning import (
    ApplicationExecutionPlanningService,
)


def create_answer(
    *,
    field_id: str,
    field_name: str,
    decision: ApplicationAnswerDecision,
    value: str | None = None,
) -> ApplicationAnswer:
    """Create a test answer."""

    return ApplicationAnswer(
        field_id=field_id,
        normalized_field_name=field_name,
        value=value,
        decision=decision,
        confidence=1.0 if decision != ApplicationAnswerDecision.SKIP else 0.0,
        source=(
            ApplicationAnswerSource.CANDIDATE_PROFILE
            if decision != ApplicationAnswerDecision.SKIP
            else ApplicationAnswerSource.UNKNOWN
        ),
        reason="Test answer.",
    )


def create_resolution(
    answers: tuple[ApplicationAnswer, ...],
) -> AnswerResolutionResult:
    """Create a consistent resolution result."""

    auto_count = sum(
        answer.decision
        == ApplicationAnswerDecision.AUTO_ANSWER
        for answer in answers
    )

    manual_count = sum(
        answer.decision
        == ApplicationAnswerDecision.MANUAL_REVIEW
        for answer in answers
    )

    skipped_count = sum(
        answer.decision
        == ApplicationAnswerDecision.SKIP
        for answer in answers
    )

    return AnswerResolutionResult(
        answers=answers,
        auto_answer_count=auto_count,
        manual_review_count=manual_count,
        skipped_count=skipped_count,
    )


def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION EXECUTION PLANNING SERVICE INTEGRATION TEST")
    print("=" * 70)

    service = ApplicationExecutionPlanningService()

    # ==============================================================
    # 1/8
    # ==============================================================

    print()
    print("[1/8] Creating planning service...")

    print("PLANNING SERVICE creation successful")

    # ==============================================================
    # 2/8
    # ==============================================================

    print()
    print("[2/8] Testing fully executable application...")

    answers = (
        create_answer(
            field_id="field-001",
            field_name="first_name",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            value="Aravind",
        ),
        create_answer(
            field_id="field-002",
            field_name="email",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            value="aravind@example.com",
        ),
        create_answer(
            field_id="field-003",
            field_name="phone",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            value="+91 9000000000",
        ),
    )

    resolution = create_resolution(answers)

    plan = service.create_plan(
        application_id="plan-test-001",
        external_job_id="linkedin-job-001",
        resolution=resolution,
    )

    assert (
        plan.decision
        == ApplicationExecutionDecision.EXECUTE
    )

    assert plan.can_execute is True
    assert plan.requires_manual_review is False
    assert plan.is_skipped is False

    assert plan.total_fields == 3
    assert plan.auto_answer_fields == 3
    assert plan.manual_review_fields == 0
    assert plan.skipped_fields == 0

    print("EXECUTE decision successful")
    print("Decision:", plan.decision.value)
    print("Can execute:", plan.can_execute)
    print("Fields:", plan.total_fields)

    # ==============================================================
    # 3/8
    # ==============================================================

    print()
    print("[3/8] Testing manual-review application...")

    answers = (
        create_answer(
            field_id="field-004",
            field_name="first_name",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            value="Aravind",
        ),
        create_answer(
            field_id="field-005",
            field_name="work_authorization",
            decision=ApplicationAnswerDecision.MANUAL_REVIEW,
            value="India work authorization",
        ),
    )

    resolution = create_resolution(answers)

    plan = service.create_plan(
        application_id="plan-test-002",
        external_job_id="linkedin-job-002",
        resolution=resolution,
    )

    assert (
        plan.decision
        == ApplicationExecutionDecision.MANUAL_REVIEW
    )

    assert plan.can_execute is False
    assert plan.requires_manual_review is True

    assert plan.total_fields == 2
    assert plan.auto_answer_fields == 1
    assert plan.manual_review_fields == 1
    assert plan.skipped_fields == 0

    print("MANUAL REVIEW decision successful")
    print("Decision:", plan.decision.value)
    print("Can execute:", plan.can_execute)
    print("Reason:", plan.reason)

    # ==============================================================
    # 4/8
    # ==============================================================

    print()
    print("[4/8] Testing skip-only application...")

    answers = (
        create_answer(
            field_id="field-006",
            field_name="unsupported_field",
            decision=ApplicationAnswerDecision.SKIP,
        ),
        create_answer(
            field_id="field-007",
            field_name="another_unsupported_field",
            decision=ApplicationAnswerDecision.SKIP,
        ),
    )

    resolution = create_resolution(answers)

    plan = service.create_plan(
        application_id="plan-test-003",
        external_job_id="linkedin-job-003",
        resolution=resolution,
    )

    assert (
        plan.decision
        == ApplicationExecutionDecision.SKIP
    )

    assert plan.can_execute is False
    assert plan.requires_manual_review is False
    assert plan.is_skipped is True

    assert plan.total_fields == 2
    assert plan.auto_answer_fields == 0
    assert plan.manual_review_fields == 0
    assert plan.skipped_fields == 2

    print("SKIP decision successful")
    print("Decision:", plan.decision.value)
    print("Reason:", plan.reason)

    # ==============================================================
    # 5/8
    # ==============================================================

    print()
    print("[5/8] Testing mixed auto-answer and skip fields...")

    answers = (
        create_answer(
            field_id="field-008",
            field_name="first_name",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            value="Aravind",
        ),
        create_answer(
            field_id="field-009",
            field_name="unsupported_field",
            decision=ApplicationAnswerDecision.SKIP,
        ),
    )

    resolution = create_resolution(answers)

    plan = service.create_plan(
        application_id="plan-test-004",
        external_job_id="linkedin-job-004",
        resolution=resolution,
    )

    assert (
        plan.decision
        == ApplicationExecutionDecision.EXECUTE
    )

    assert plan.can_execute is True

    assert plan.total_fields == 2
    assert plan.auto_answer_fields == 1
    assert plan.manual_review_fields == 0
    assert plan.skipped_fields == 1

    print("AUTO + SKIP handling successful")
    print("Decision:", plan.decision.value)
    print("Auto answers:", plan.auto_answer_fields)
    print("Skipped:", plan.skipped_fields)

    # ==============================================================
    # 6/8
    # ==============================================================

    print()
    print("[6/8] Testing mixed auto-answer and manual-review fields...")

    answers = (
        create_answer(
            field_id="field-010",
            field_name="email",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            value="aravind@example.com",
        ),
        create_answer(
            field_id="field-011",
            field_name="sponsorship",
            decision=ApplicationAnswerDecision.MANUAL_REVIEW,
            value="No",
        ),
        create_answer(
            field_id="field-012",
            field_name="unsupported_field",
            decision=ApplicationAnswerDecision.SKIP,
        ),
    )

    resolution = create_resolution(answers)

    plan = service.create_plan(
        application_id="plan-test-005",
        external_job_id="linkedin-job-005",
        resolution=resolution,
    )

    assert (
        plan.decision
        == ApplicationExecutionDecision.MANUAL_REVIEW
    )

    assert plan.can_execute is False
    assert plan.requires_manual_review is True

    assert plan.total_fields == 3
    assert plan.auto_answer_fields == 1
    assert plan.manual_review_fields == 1
    assert plan.skipped_fields == 1

    print("MIXED decision handling successful")
    print("Decision:", plan.decision.value)
    print("Reason:", plan.reason)

    # ==============================================================
    # 7/8
    # ==============================================================

    print()
    print("[7/8] Testing empty resolution...")

    resolution = create_resolution(())

    plan = service.create_plan(
        application_id="plan-test-006",
        external_job_id="linkedin-job-006",
        resolution=resolution,
    )

    assert (
        plan.decision
        == ApplicationExecutionDecision.SKIP
    )

    assert plan.total_fields == 0
    assert plan.auto_answer_fields == 0
    assert plan.manual_review_fields == 0
    assert plan.skipped_fields == 0

    print("EMPTY resolution handling successful")
    print("Decision:", plan.decision.value)

    # ==============================================================
    # 8/8
    # ==============================================================

    print()
    print("[8/8] Testing execution safety...")

    manual_answers = (
        create_answer(
            field_id="field-013",
            field_name="work_authorization",
            decision=ApplicationAnswerDecision.MANUAL_REVIEW,
            value="Requires review",
        ),
    )

    resolution = create_resolution(manual_answers)

    plan = service.create_plan(
        application_id="plan-test-007",
        external_job_id="linkedin-job-007",
        resolution=resolution,
    )

    assert plan.can_execute is False
    assert plan.requires_manual_review is True
    assert (
        plan.decision
        == ApplicationExecutionDecision.MANUAL_REVIEW
    )

    print("EXECUTION SAFETY checks successful")
    print("Manual review blocks execution:", not plan.can_execute)

    print()
    print("=" * 70)
    print("APPLICATION EXECUTION PLANNING SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()