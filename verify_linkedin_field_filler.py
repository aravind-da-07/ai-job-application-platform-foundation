"""
LinkedIn application field filler integration test.

Verifies that:
- AUTO_ANSWER values are accepted.
- MANUAL_REVIEW values are rejected.
- SKIP values are rejected.
- Invalid empty AUTO_ANSWER values are rejected by the domain model.
- Multiple approved fields are recorded correctly.
"""

from __future__ import annotations

import asyncio

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
    ApplicationAnswerDecision,
    ApplicationAnswerSource,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling import (
    MockLinkedInApplicationFieldFiller,
)


async def main() -> None:
    print()
    print("=" * 70)
    print("LINKEDIN APPLICATION FIELD FILLER INTEGRATION TEST")
    print("=" * 70)

    filler = MockLinkedInApplicationFieldFiller()

    # ==============================================================
    # 1/6
    # ==============================================================

    print()
    print("[1/6] Testing approved AUTO_ANSWER field...")

    answer = ApplicationAnswer(
        field_id="field-001",
        normalized_field_name="first_name",
        value="Aravind",
        decision=ApplicationAnswerDecision.AUTO_ANSWER,
        confidence=1.0,
        source=ApplicationAnswerSource.CANDIDATE_PROFILE,
        reason="Explicit candidate profile value.",
    )

    result = await filler.fill_field(answer)

    assert result.success is True
    assert result.field_id == "field-001"
    assert result.filled_value == "Aravind"
    assert result.error_code is None
    assert filler.fill_count == 1

    print("AUTO_ANSWER filling successful")
    print("Field:", result.field_id)
    print("Value:", result.filled_value)

    # ==============================================================
    # 2/6
    # ==============================================================

    print()
    print("[2/6] Testing MANUAL_REVIEW protection...")

    answer = ApplicationAnswer(
        field_id="field-002",
        normalized_field_name="work_authorization",
        value="India work authorization",
        decision=ApplicationAnswerDecision.MANUAL_REVIEW,
        confidence=1.0,
        source=ApplicationAnswerSource.CANDIDATE_PROFILE,
        reason="Sensitive field requires review.",
    )

    result = await filler.fill_field(answer)

    assert result.success is False
    assert result.error_code == "answer_not_approved"
    assert filler.fill_count == 1

    print("MANUAL_REVIEW protection successful")
    print("Rejected:", result.error_code)

    # ==============================================================
    # 3/6
    # ==============================================================

    print()
    print("[3/6] Testing SKIP protection...")

    answer = ApplicationAnswer(
        field_id="field-003",
        normalized_field_name="unknown",
        value=None,
        decision=ApplicationAnswerDecision.SKIP,
        confidence=0.0,
        source=ApplicationAnswerSource.UNKNOWN,
        reason="Unsupported field.",
    )

    result = await filler.fill_field(answer)

    assert result.success is False
    assert result.error_code == "answer_not_approved"
    assert filler.fill_count == 1

    print("SKIP protection successful")
    print("Rejected:", result.error_code)

    # ==============================================================
    # 4/6
    # ==============================================================

    print()
    print("[4/6] Testing invalid empty AUTO_ANSWER protection...")

    try:
        ApplicationAnswer(
            field_id="field-004",
            normalized_field_name="email",
            value="",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Invalid empty test value.",
        )

    except ValueError as exc:
        assert (
            str(exc)
            == "AUTO_ANSWER requires a non-empty value."
        )

        print("EMPTY AUTO_ANSWER protection successful")
        print("Rejected:", str(exc))

    else:
        raise AssertionError(
            "Empty AUTO_ANSWER was incorrectly accepted."
        )

    # The invalid answer must never reach the filler.
    assert filler.fill_count == 1

    # ==============================================================
    # 5/6
    # ==============================================================

    print()
    print("[5/6] Testing multiple approved fields...")

    approved_answers = (
        ApplicationAnswer(
            field_id="field-005",
            normalized_field_name="email",
            value="aravind@example.com",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Explicit candidate profile value.",
        ),
        ApplicationAnswer(
            field_id="field-006",
            normalized_field_name="phone",
            value="+91 9000000000",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Explicit candidate profile value.",
        ),
        ApplicationAnswer(
            field_id="field-007",
            normalized_field_name="location",
            value="Hyderabad",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Explicit candidate profile value.",
        ),
    )

    for approved_answer in approved_answers:
        result = await filler.fill_field(approved_answer)

        assert result.success is True

    assert filler.fill_count == 4

    print("MULTIPLE FIELD filling successful")
    print("Total successful fills:", filler.fill_count)

    # ==============================================================
    # 6/6
    # ==============================================================

    print()
    print("[6/6] Testing filler isolation...")

    assert all(
        answer.decision
        == ApplicationAnswerDecision.AUTO_ANSWER
        for answer in filler.filled_answers
    )

    assert all(
        answer.value is not None
        and answer.value.strip()
        for answer in filler.filled_answers
    )

    print("FILLER isolation checks successful")
    print("Only approved answers were recorded.")

    print()
    print("=" * 70)
    print("LINKEDIN APPLICATION FIELD FILLER TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())