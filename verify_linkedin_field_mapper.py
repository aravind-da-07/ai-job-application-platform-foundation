"""
LinkedIn application field mapper integration test.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormField,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.mapping import (
    LinkedInApplicationFieldMapper,
)


def field(
    field_id: str,
    label: str,
) -> ApplicationFormField:
    return ApplicationFormField(
        field_id=field_id,
        label=label,
        field_type="text",
    )


def main() -> None:
    print()
    print("=" * 70)
    print("LINKEDIN APPLICATION FIELD MAPPER INTEGRATION TEST")
    print("=" * 70)

    mapper = LinkedInApplicationFieldMapper()

    # ==============================================================
    # 1/8
    # ==============================================================

    print()
    print("[1/8] Testing first-name variations...")

    first_name_labels = (
        "First Name",
        "Given Name",
        "Candidate First Name",
        "Forename",
    )

    for index, label in enumerate(first_name_labels):
        result = mapper.map_field(
            field(
                f"first-{index}",
                label,
            )
        )

        assert result.normalized_name == "first_name"
        assert result.confidence == 1.0

    print("FIRST NAME mapping successful")

    # ==============================================================
    # 2/8
    # ==============================================================

    print()
    print("[2/8] Testing email variations...")

    email_labels = (
        "Email",
        "Email Address",
        "Contact Email",
        "E-mail",
    )

    for index, label in enumerate(email_labels):
        result = mapper.map_field(
            field(
                f"email-{index}",
                label,
            )
        )

        assert result.normalized_name == "email"
        assert result.confidence == 1.0

    print("EMAIL mapping successful")

    # ==============================================================
    # 3/8
    # ==============================================================

    print()
    print("[3/8] Testing experience variations...")

    experience_labels = (
        "Years of Experience",
        "Total Experience",
        "Years Experience",
        "Professional Experience",
    )

    for index, label in enumerate(experience_labels):
        result = mapper.map_field(
            field(
                f"experience-{index}",
                label,
            )
        )

        assert result.normalized_name == "experience_years"
        assert result.confidence == 1.0

    print("EXPERIENCE mapping successful")

    # ==============================================================
    # 4/8
    # ==============================================================

    print()
    print("[4/8] Testing resume variations...")

    resume_labels = (
        "Resume",
        "CV",
        "Curriculum Vitae",
    )

    for index, label in enumerate(resume_labels):
        result = mapper.map_field(
            field(
                f"resume-{index}",
                label,
            )
        )

        assert result.normalized_name == "resume"
        assert result.confidence == 1.0

    print("RESUME mapping successful")

    # ==============================================================
    # 5/8
    # ==============================================================

    print()
    print("[5/8] Testing work authorization variations...")

    authorization_labels = (
        "Work Authorization",
        "Work Permit",
        "Authorized to Work",
        "Legally Authorized",
    )

    for index, label in enumerate(authorization_labels):
        result = mapper.map_field(
            field(
                f"authorization-{index}",
                label,
            )
        )

        assert result.normalized_name == "work_authorization"
        assert result.confidence == 1.0

    print("WORK AUTHORIZATION mapping successful")

    # ==============================================================
    # 6/8
    # ==============================================================

    print()
    print("[6/8] Testing partial wording recognition...")

    result = mapper.map_field(
        field(
            "partial-001",
            "What is your total years of professional experience?",
        )
    )

    assert result.normalized_name == "experience_years"
    assert result.confidence == 0.85

    print("PARTIAL wording mapping successful")
    print(
        "Normalized:",
        result.normalized_name,
    )
    print(
        "Confidence:",
        result.confidence,
    )

    # ==============================================================
    # 7/8
    # ==============================================================

    print()
    print("[7/8] Testing unknown-field handling...")

    result = mapper.map_field(
        field(
            "unknown-001",
            "What is your favorite programming language?",
        )
    )

    assert result.normalized_name == "unknown"
    assert result.confidence == 0.0

    print("UNKNOWN field handling successful")
    print(
        "Normalized:",
        result.normalized_name,
    )
    print(
        "Confidence:",
        result.confidence,
    )

    # ==============================================================
    # 8/8
    # ==============================================================

    print()
    print("[8/8] Testing batch field mapping...")

    fields = (
        field("batch-001", "First Name"),
        field("batch-002", "Contact Email"),
        field("batch-003", "Mobile Number"),
        field("batch-004", "Total Experience"),
        field("batch-005", "CV"),
        field("batch-006", "Expected Salary"),
        field("batch-007", "Notice Period"),
        field("batch-008", "Visa Sponsorship"),
    )

    results = mapper.map_fields(fields)

    assert len(results) == 8

    normalized_names = tuple(
        result.normalized_name
        for result in results
    )

    expected = (
        "first_name",
        "email",
        "phone",
        "experience_years",
        "resume",
        "salary",
        "notice_period",
        "sponsorship",
    )

    assert normalized_names == expected

    print("BATCH mapping successful")
    print(
        "Normalized fields:",
        normalized_names,
    )

    print()
    print("=" * 70)
    print("LINKEDIN APPLICATION FIELD MAPPER TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()