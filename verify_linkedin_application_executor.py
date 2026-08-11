"""
Integration test for LinkedInApplicationExecutor.

This test validates the synchronous executor boundary and ensures
that it correctly delegates to the existing browser workflow.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionRequest,
    ApplicationExecutionStatus,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin import (
    LinkedInApplicationExecutor,
)
from src.shared.config.constants import JobSourceType


def create_request(
    *,
    application_id: str = "executor-linkedin-001",
    external_job_id: str = "linkedin-job-001",
) -> ApplicationExecutionRequest:
    return ApplicationExecutionRequest(
        application_id=application_id,
        external_job_id=external_job_id,
        job_url="https://www.linkedin.com/jobs/view/test-job",
        source=JobSourceType.LINKEDIN,
        candidate_data={
            "first_name": "Aravind",
            "last_name": "Reddy",
            "full_name": "Aravind Reddy",
            "email": "aravind@example.com",
            "phone": "9999999999",
            "location": "Hyderabad",
            "experience_years": "2.10",
            "linkedin_url": "https://www.linkedin.com/in/test",
            "resume": "resume-test.pdf",
            "cover_letter": "cover-letter-test.pdf",
            "salary": "600000",
            "notice_period": "30 days",
        },
    )


def main() -> None:
    print("=" * 70)
    print("LINKEDIN APPLICATION EXECUTOR INTEGRATION TEST")
    print("=" * 70)

    # --------------------------------------------------------------
    # 1. Executor creation
    # --------------------------------------------------------------

    print("\n[1/6] Creating LinkedIn executor...")

    executor = LinkedInApplicationExecutor()

    assert executor.configured is False

    print("EXECUTOR creation successful")
    print("Configured:", executor.configured)

    # --------------------------------------------------------------
    # 2. Missing browser protection
    # --------------------------------------------------------------

    print("\n[2/6] Testing browser-not-configured protection...")

    result = executor.execute(
        create_request()
    )

    assert (
        result.status
        == ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )
    assert result.submitted is False
    assert result.requires_manual_intervention is True
    assert result.error_code == "linkedin_browser_not_configured"

    print("BROWSER protection successful")
    print("Status:", result.status.value)
    print("Error:", result.error_code)

    # --------------------------------------------------------------
    # 3. Request validation
    # --------------------------------------------------------------

    print("\n[3/6] Testing request validation...")

    try:
        executor.execute(
            create_request(
                application_id=""
            )
        )
    except ValueError as exc:
        assert str(exc) == "application_id cannot be empty."
        print("REQUEST validation successful")
        print("Expected validation error:", exc)
    else:
        raise AssertionError(
            "Expected application_id validation error."
        )

    # --------------------------------------------------------------
    # 4. Wrong source protection
    # --------------------------------------------------------------

    print("\n[4/6] Testing LinkedIn source protection...")

    class FakeSource:
        value = "not_linkedin"

    request = create_request()

    # Do not mutate the frozen domain object. Build another request
    # with an invalid source through the existing constructor.
    invalid_request = ApplicationExecutionRequest(
        application_id=request.application_id,
        external_job_id=request.external_job_id,
        job_url=request.job_url,
        source=FakeSource(),
        candidate_data=request.candidate_data,
    )

    try:
        executor.execute(invalid_request)
    except ValueError as exc:
        assert (
            str(exc)
            == "LinkedIn executor received a non-LinkedIn job."
        )
        print("SOURCE protection successful")
        print("Expected validation error:", exc)
    else:
        raise AssertionError(
            "Expected LinkedIn source validation error."
        )

    # --------------------------------------------------------------
    # 5. Empty job URL protection
    # --------------------------------------------------------------

    print("\n[5/6] Testing job URL validation...")

    try:
        executor.execute(
            ApplicationExecutionRequest(
                application_id="executor-linkedin-002",
                external_job_id="linkedin-job-002",
                job_url="",
                source=JobSourceType.LINKEDIN,
                candidate_data={
                    "first_name": "Aravind",
                },
            )
        )
    except ValueError as exc:
        assert str(exc) == "job_url cannot be empty."
        print("JOB URL validation successful")
        print("Expected validation error:", exc)
    else:
        raise AssertionError(
            "Expected job URL validation error."
        )

    # --------------------------------------------------------------
    # 6. Final safety boundary
    # --------------------------------------------------------------

    print("\n[6/6] Testing final safety boundary...")

    result = executor.execute(
        create_request(
            application_id="executor-safety-001"
        )
    )

    assert result.submitted is False
    assert result.requires_manual_intervention is True
    assert result.status == (
        ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    print("FINAL safety boundary successful")
    print("No browser session = no submission")
    print("No automatic bypass occurred")

    print("\n" + "=" * 70)
    print("LINKEDIN APPLICATION EXECUTOR TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()