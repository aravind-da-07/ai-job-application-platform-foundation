"""
Application Eligibility Service Integration Test.

Tests the application eligibility decision layer independently
from databases, browsers, and external job portals.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application import (
    ApplicationEligibilityDecision,
)
from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.services.application import (
    ApplicationEligibilityService,
)
from src.shared.config.constants import (
    ApplicationStatus,
    DecisionType,
    JobSourceType,
)


def create_job(
    external_id: str,
    *,
    title: str = "Data Analyst",
    company_name: str = "Test Company",
) -> DiscoveredJob:
    """
    Create a deterministic test job.
    """

    return DiscoveredJob(
        external_id=external_id,
        title=title,
        company_name=company_name,
        source=JobSourceType.LINKEDIN,
        url=(
            "https://www.linkedin.com/jobs/view/"
            f"{external_id}"
        ),
        location="Hyderabad, Telangana, India",
    )


def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION ELIGIBILITY SERVICE INTEGRATION TEST")
    print("=" * 70)

    # --------------------------------------------------------------
    # 1
    # --------------------------------------------------------------

    print()
    print("[1/10] Creating eligibility service...")

    service = ApplicationEligibilityService()

    assert isinstance(
        service,
        ApplicationEligibilityService,
    )

    print("ELIGIBILITY SERVICE creation successful")

    # --------------------------------------------------------------
    # 2
    # --------------------------------------------------------------

    print()
    print("[2/10] Testing eligible application queue...")

    job = create_job(
        "eligibility-test-001"
    )

    result = service.evaluate(
        job,
        match_decision=DecisionType.APPLY,
    )

    assert result.eligible is True
    assert (
        result.decision
        == ApplicationEligibilityDecision.QUEUE
    )
    assert (
        result.application_status
        == ApplicationStatus.QUEUED
    )

    print("QUEUE decision successful")
    print("Eligible:", result.eligible)
    print("Decision:", result.decision.value)
    print("Status:", result.application_status.value)
    print("Reason:", result.reason)

    # --------------------------------------------------------------
    # 3
    # --------------------------------------------------------------

    print()
    print("[3/10] Testing duplicate application...")

    result = service.evaluate(
        job,
        match_decision=DecisionType.APPLY,
        already_applied=True,
    )

    assert result.eligible is False
    assert (
        result.decision
        == ApplicationEligibilityDecision.SKIP
    )
    assert result.duplicate is True
    assert (
        result.application_status
        == ApplicationStatus.DUPLICATE
    )

    print("DUPLICATE handling successful")
    print("Decision:", result.decision.value)
    print("Status:", result.application_status.value)
    print("Reason:", result.reason)

    # --------------------------------------------------------------
    # 4
    # --------------------------------------------------------------

    print()
    print("[4/10] Testing inactive job...")

    result = service.evaluate(
        job,
        match_decision=DecisionType.APPLY,
        job_active=False,
    )

    assert result.eligible is False
    assert (
        result.decision
        == ApplicationEligibilityDecision.SKIP
    )
    assert result.job_active is False
    assert (
        result.application_status
        == ApplicationStatus.SKIPPED
    )

    print("INACTIVE JOB handling successful")
    print("Decision:", result.decision.value)
    print("Status:", result.application_status.value)
    print("Reason:", result.reason)

    # --------------------------------------------------------------
    # 5
    # --------------------------------------------------------------

    print()
    print("[5/10] Testing skipped match decision...")

    result = service.evaluate(
        job,
        match_decision=DecisionType.SKIP,
    )

    assert result.eligible is False
    assert (
        result.decision
        == ApplicationEligibilityDecision.SKIP
    )
    assert (
        result.application_status
        == ApplicationStatus.SKIPPED
    )

    print("MATCH SKIP handling successful")
    print("Decision:", result.decision.value)
    print("Status:", result.application_status.value)
    print("Reason:", result.reason)

    # --------------------------------------------------------------
    # 6
    # --------------------------------------------------------------

    print()
    print("[6/10] Testing manual-review match decision...")

    result = service.evaluate(
        job,
        match_decision=DecisionType.MANUAL_REVIEW,
    )

    assert result.eligible is False
    assert (
        result.decision
        == ApplicationEligibilityDecision.MANUAL_REVIEW
    )
    assert (
        result.application_status
        == ApplicationStatus.MANUAL_REVIEW_REQUIRED
    )

    print("MANUAL REVIEW handling successful")
    print("Decision:", result.decision.value)
    print("Status:", result.application_status.value)
    print("Reason:", result.reason)

    # --------------------------------------------------------------
    # 7
    # --------------------------------------------------------------

    print()
    print("[7/10] Testing authentication requirement...")

    result = service.evaluate(
        job,
        match_decision=DecisionType.APPLY,
        authentication_required=True,
    )

    assert result.eligible is False
    assert (
        result.decision
        == ApplicationEligibilityDecision.AUTHENTICATION_REQUIRED
    )
    assert result.authentication_required is True
    assert (
        result.application_status
        == ApplicationStatus.AUTHENTICATION_REQUIRED
    )

    print("AUTHENTICATION handling successful")
    print("Decision:", result.decision.value)
    print("Status:", result.application_status.value)
    print("Reason:", result.reason)

    # --------------------------------------------------------------
    # 8
    # --------------------------------------------------------------

    print()
    print("[8/10] Testing CAPTCHA detection...")

    result = service.evaluate(
        job,
        match_decision=DecisionType.APPLY,
        captcha_detected=True,
    )

    assert result.eligible is False
    assert (
        result.decision
        == ApplicationEligibilityDecision.CAPTCHA_DETECTED
    )
    assert result.captcha_detected is True
    assert (
        result.application_status
        == ApplicationStatus.CAPTCHA_DETECTED
    )

    print("CAPTCHA handling successful")
    print("Decision:", result.decision.value)
    print("Status:", result.application_status.value)
    print("Reason:", result.reason)

    # --------------------------------------------------------------
    # 9
    # --------------------------------------------------------------

    print()
    print("[9/10] Testing multiple-job eligibility...")

    jobs = (
        create_job("eligibility-test-001"),
        create_job("eligibility-test-002"),
        create_job("eligibility-test-003"),
        create_job("eligibility-test-004"),
    )

    results = service.evaluate_many(
        jobs,
        match_decision=DecisionType.APPLY,
        already_applied_ids={
            "eligibility-test-002",
        },
        inactive_job_ids={
            "eligibility-test-003",
        },
    )

    assert len(results) == 4

    assert (
        results[0].decision
        == ApplicationEligibilityDecision.QUEUE
    )

    assert (
        results[1].decision
        == ApplicationEligibilityDecision.SKIP
    )

    assert results[1].duplicate is True

    assert (
        results[2].decision
        == ApplicationEligibilityDecision.SKIP
    )

    assert results[2].job_active is False

    assert (
        results[3].decision
        == ApplicationEligibilityDecision.QUEUE
    )

    print("MULTIPLE-JOB eligibility successful")
    print("Jobs evaluated:", len(results))

    for index, item in enumerate(results, start=1):
        print(
            f"Job {index}: "
            f"{item.external_job_id} | "
            f"{item.decision.value} | "
            f"{item.application_status.value}"
        )

    # --------------------------------------------------------------
    # 10
    # --------------------------------------------------------------

    print()
    print("[10/10] Testing decision safety...")

    safe_job = create_job(
        "eligibility-test-safety"
    )

    captcha_result = service.evaluate(
        safe_job,
        match_decision=DecisionType.APPLY,
        captcha_detected=True,
    )

    auth_result = service.evaluate(
        safe_job,
        match_decision=DecisionType.APPLY,
        authentication_required=True,
    )

    manual_result = service.evaluate(
        safe_job,
        match_decision=DecisionType.MANUAL_REVIEW,
    )

    assert captcha_result.eligible is False
    assert auth_result.eligible is False
    assert manual_result.eligible is False

    assert (
        captcha_result.decision
        == ApplicationEligibilityDecision.CAPTCHA_DETECTED
    )

    assert (
        auth_result.decision
        == ApplicationEligibilityDecision.AUTHENTICATION_REQUIRED
    )

    assert (
        manual_result.decision
        == ApplicationEligibilityDecision.MANUAL_REVIEW
    )

    print("DECISION SAFETY checks successful")
    print("CAPTCHA → manual intervention")
    print("Authentication → authentication required")
    print("Manual review → manual review")

    print()
    print("=" * 70)
    print("APPLICATION ELIGIBILITY SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()