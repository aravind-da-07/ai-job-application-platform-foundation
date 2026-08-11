"""
Answer Resolver Service integration test.

Verifies:
- known candidate fields -> AUTO_ANSWER
- missing candidate data -> MANUAL_REVIEW
- unknown fields -> MANUAL_REVIEW
- sensitive fields -> MANUAL_REVIEW
- unsupported fields -> SKIP
- batch resolution
"""

from __future__ import annotations

from dataclasses import dataclass

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswerDecision,
    ApplicationAnswerSource,
)
from src.modules.job_discovery.services.application_executor.answers import (
    AnswerResolverService,
)


@dataclass(frozen=True)
class NormalizedField:
    """Minimal normalized field used by the resolver test."""

    field_id: str
    normalized_name: str


def main() -> None:
    print()
    print("=" * 70)
    print("ANSWER RESOLVER SERVICE INTEGRATION TEST")
    print("=" * 70)

    resolver = AnswerResolverService()

    candidate_data = {
        "first_name": "Aravind",
        "last_name": "Reddy",
        "full_name": "Aravind Reddy",
        "email": "aravind@example.com",
        "phone": "+91 9000000000",
        "location": "Hyderabad",
        "experience_years": "2.10",
        "linkedin_url": "https://www.linkedin.com/in/example",
        "resume": "resume-001",
        "cover_letter": "cover-letter-001",
        "salary": "600000",
        "notice_period": "30 days",
        "work_authorization": "India work authorization",
        "sponsorship": "No",
    }

    # ==============================================================
    # 1/8
    # ==============================================================

    print()
    print("[1/8] Testing known candidate field...")

    result = resolver.resolve_field(
        field_id="field-001",
        normalized_field_name="first_name",
        candidate_data=candidate_data,
    )

    assert (
        result.decision
        == ApplicationAnswerDecision.AUTO_ANSWER
    )

    assert result.value == "Aravind"
    assert result.confidence == 1.0
    assert (
        result.source
        == ApplicationAnswerSource.CANDIDATE_PROFILE
    )

    print("KNOWN FIELD resolution successful")
    print("Decision:", result.decision.value)
    print("Value:", result.value)
    print("Confidence:", result.confidence)

    # ==============================================================
    # 2/8
    # ==============================================================

    print()
    print("[2/8] Testing email resolution...")

    result = resolver.resolve_field(
        field_id="field-002",
        normalized_field_name="email",
        candidate_data=candidate_data,
    )

    assert (
        result.decision
        == ApplicationAnswerDecision.AUTO_ANSWER
    )

    assert result.value == "aravind@example.com"

    print("EMAIL resolution successful")
    print("Value:", result.value)

    # ==============================================================
    # 3/8
    # ==============================================================

    print()
    print("[3/8] Testing missing candidate information...")

    incomplete_data = {
        "first_name": "Aravind",
    }

    result = resolver.resolve_field(
        field_id="field-003",
        normalized_field_name="phone",
        candidate_data=incomplete_data,
    )

    assert (
        result.decision
        == ApplicationAnswerDecision.MANUAL_REVIEW
    )

    assert result.value is None

    print("MISSING DATA handling successful")
    print("Decision:", result.decision.value)
    print("Reason:", result.reason)

    # ==============================================================
    # 4/8
    # ==============================================================

    print()
    print("[4/8] Testing unknown question...")

    result = resolver.resolve_field(
        field_id="field-004",
        normalized_field_name="unknown",
        candidate_data=candidate_data,
    )

    assert (
        result.decision
        == ApplicationAnswerDecision.MANUAL_REVIEW
    )

    assert result.value is None
    assert result.confidence == 0.0

    print("UNKNOWN QUESTION handling successful")
    print("Decision:", result.decision.value)
    print("Reason:", result.reason)

    # ==============================================================
    # 5/8
    # ==============================================================

    print()
    print("[5/8] Testing sensitive authorization question...")

    result = resolver.resolve_field(
        field_id="field-005",
        normalized_field_name="work_authorization",
        candidate_data=candidate_data,
    )

    assert (
        result.decision
        == ApplicationAnswerDecision.MANUAL_REVIEW
    )

    assert result.value == "India work authorization"
    assert result.confidence == 1.0

    print("AUTHORIZATION safety handling successful")
    print("Decision:", result.decision.value)
    print("Reason:", result.reason)

    # ==============================================================
    # 6/8
    # ==============================================================

    print()
    print("[6/8] Testing sponsorship question...")

    result = resolver.resolve_field(
        field_id="field-006",
        normalized_field_name="sponsorship",
        candidate_data=candidate_data,
    )

    assert (
        result.decision
        == ApplicationAnswerDecision.MANUAL_REVIEW
    )

    assert result.value == "No"

    print("SPONSORSHIP safety handling successful")
    print("Decision:", result.decision.value)
    print("Reason:", result.reason)

    # ==============================================================
    # 7/8
    # ==============================================================

    print()
    print("[7/8] Testing unsupported field...")

    result = resolver.resolve_field(
        field_id="field-007",
        normalized_field_name="unknown_internal_field",
        candidate_data=candidate_data,
    )

    assert (
        result.decision
        == ApplicationAnswerDecision.SKIP
    )

    assert result.value is None

    print("UNSUPPORTED FIELD handling successful")
    print("Decision:", result.decision.value)
    print("Reason:", result.reason)

    # ==============================================================
    # 8/8
    # ==============================================================

    print()
    print("[8/8] Testing batch resolution...")

    fields = (
        NormalizedField(
            field_id="batch-001",
            normalized_name="first_name",
        ),
        NormalizedField(
            field_id="batch-002",
            normalized_name="email",
        ),
        NormalizedField(
            field_id="batch-003",
            normalized_name="experience_years",
        ),
        NormalizedField(
            field_id="batch-004",
            normalized_name="work_authorization",
        ),
        NormalizedField(
            field_id="batch-005",
            normalized_name="unknown",
        ),
        NormalizedField(
            field_id="batch-006",
            normalized_name="unknown_internal_field",
        ),
    )

    batch_result = resolver.resolve_fields(
        fields=fields,
        candidate_data=candidate_data,
    )

    assert len(batch_result.answers) == 6

    assert batch_result.auto_answer_count == 3
    assert batch_result.manual_review_count == 2
    assert batch_result.skipped_count == 1

    assert batch_result.requires_manual_review is True

    decisions = tuple(
        answer.decision.value
        for answer in batch_result.answers
    )

    expected_decisions = (
        "auto_answer",
        "auto_answer",
        "auto_answer",
        "manual_review",
        "manual_review",
        "skip",
    )

    assert decisions == expected_decisions

    print("BATCH resolution successful")
    print("Answers:", len(batch_result.answers))
    print(
        "Auto answers:",
        batch_result.auto_answer_count,
    )
    print(
        "Manual review:",
        batch_result.manual_review_count,
    )
    print(
        "Skipped:",
        batch_result.skipped_count,
    )

    print()
    print("=" * 70)
    print("ANSWER RESOLVER SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()