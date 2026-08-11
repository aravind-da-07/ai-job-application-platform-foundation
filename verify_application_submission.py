"""
Application submission service integration test.

Verifies the final submission safety boundary without interacting
with a real job portal.
"""

from __future__ import annotations

import asyncio

from src.modules.job_discovery.domain.application_executor.submission import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionResult,
    ApplicationSubmissionStatus,
)

from src.modules.job_discovery.services.application_executor.submission import (
    ApplicationSubmissionService,
)


class MockApplicationSubmitter:
    """Controlled test submitter."""

    def __init__(
        self,
        *,
        should_succeed: bool = True,
    ) -> None:
        self.should_succeed = should_succeed
        self.submitted_requests: list[
            ApplicationSubmissionRequest
        ] = []

    async def submit(
        self,
        request: ApplicationSubmissionRequest,
    ) -> ApplicationSubmissionResult:
        self.submitted_requests.append(request)

        if not self.should_succeed:
            return ApplicationSubmissionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                status=ApplicationSubmissionStatus.FAILED,
                submitted=False,
                verified_field_count=(
                    request.verified_field_count
                ),
                error_code="submit_failed",
                error_message=(
                    "Intentional integration-test "
                    "submission failure."
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
            confirmation_id="confirmation-test-001",
        )


async def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION SUBMISSION SERVICE INTEGRATION TEST")
    print("=" * 70)

    # ==============================================================
    # 1/7
    # ==============================================================

    print()
    print("[1/7] Creating submission service...")

    service = ApplicationSubmissionService()

    assert service.submitter_configured is False

    print("SUBMISSION SERVICE creation successful")
    print(
        "Submitter configured:",
        service.submitter_configured,
    )

    # ==============================================================
    # 2/7
    # ==============================================================

    print()
    print("[2/7] Testing no-verified-fields protection...")

    request = ApplicationSubmissionRequest(
        application_id="submission-test-001",
        external_job_id="job-001",
        verified_field_count=0,
    )

    result = await service.submit(request)

    assert (
        result.status
        == ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED
    )
    assert result.submitted is False
    assert result.error_code == "no_verified_fields"
    assert result.manual_intervention_required is True

    print("NO VERIFIED FIELDS protection successful")
    print("Status:", result.status.value)
    print("Submitted:", result.submitted)
    print("Reason:", result.error_code)

    # ==============================================================
    # 3/7
    # ==============================================================

    print()
    print("[3/7] Testing submitter-not-configured protection...")

    request = ApplicationSubmissionRequest(
        application_id="submission-test-002",
        external_job_id="job-002",
        verified_field_count=5,
    )

    result = await service.submit(request)

    assert (
        result.status
        == ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED
    )
    assert result.submitted is False
    assert result.error_code == "submitter_not_configured"
    assert result.manual_intervention_required is True

    print("NO SUBMITTER protection successful")
    print("Status:", result.status.value)
    print("Submitted:", result.submitted)
    print("Reason:", result.error_code)

    # ==============================================================
    # 4/7
    # ==============================================================

    print()
    print("[4/7] Testing successful submission...")

    submitter = MockApplicationSubmitter(
        should_succeed=True
    )

    service = ApplicationSubmissionService(
        submitter=submitter
    )

    request = ApplicationSubmissionRequest(
        application_id="submission-test-003",
        external_job_id="job-003",
        verified_field_count=8,
    )

    result = await service.submit(request)

    assert (
        result.status
        == ApplicationSubmissionStatus.SUBMITTED
    )
    assert result.submitted is True
    assert result.confirmation_id == (
        "confirmation-test-001"
    )
    assert result.verified_field_count == 8
    assert len(submitter.submitted_requests) == 1

    print("SUCCESSFUL submission successful")
    print("Status:", result.status.value)
    print("Submitted:", result.submitted)
    print("Confirmation:", result.confirmation_id)
    print(
        "Verified fields:",
        result.verified_field_count,
    )

    # ==============================================================
    # 5/7
    # ==============================================================

    print()
    print("[5/7] Testing submission failure...")

    failing_submitter = MockApplicationSubmitter(
        should_succeed=False
    )

    service = ApplicationSubmissionService(
        submitter=failing_submitter
    )

    request = ApplicationSubmissionRequest(
        application_id="submission-test-004",
        external_job_id="job-004",
        verified_field_count=6,
    )

    result = await service.submit(request)

    assert (
        result.status
        == ApplicationSubmissionStatus.FAILED
    )
    assert result.submitted is False
    assert result.confirmation_id is None
    assert result.error_code == "submit_failed"
    assert len(failing_submitter.submitted_requests) == 1

    print("SUBMISSION FAILURE handling successful")
    print("Status:", result.status.value)
    print("Submitted:", result.submitted)
    print("Error:", result.error_code)

    # ==============================================================
    # 6/7
    # ==============================================================

    print()
    print("[6/7] Testing submission result safety...")

    try:
        ApplicationSubmissionResult(
            application_id="submission-test-005",
            external_job_id="job-005",
            status=ApplicationSubmissionStatus.SUBMITTED,
            submitted=True,
            verified_field_count=5,
            confirmation_id=None,
        )

    except ValueError as exc:
        print("RESULT safety validation successful")
        print("Expected validation error:", str(exc))

    else:
        raise AssertionError(
            "Submission result incorrectly allowed "
            "submitted=True without confirmation ID."
        )

    try:
        ApplicationSubmissionResult(
            application_id="submission-test-006",
            external_job_id="job-006",
            status=ApplicationSubmissionStatus.SUBMITTED,
            submitted=False,
            verified_field_count=5,
            confirmation_id="confirmation-006",
        )

    except ValueError as exc:
        print("SUBMITTED state consistency validation successful")
        print("Expected validation error:", str(exc))

    else:
        raise AssertionError(
            "SUBMITTED status incorrectly allowed "
            "submitted=False."
        )

    # ==============================================================
    # 7/7
    # ==============================================================

    print()
    print("[7/7] Testing request validation...")

    try:
        ApplicationSubmissionRequest(
            application_id="",
            external_job_id="job-007",
            verified_field_count=1,
        )

    except ValueError as exc:
        print("APPLICATION ID validation successful")
        print("Expected validation error:", str(exc))

    else:
        raise AssertionError(
            "Empty application_id was incorrectly accepted."
        )

    try:
        ApplicationSubmissionRequest(
            application_id="submission-test-008",
            external_job_id="job-008",
            verified_field_count=-1,
        )

    except ValueError as exc:
        print("VERIFIED FIELD validation successful")
        print("Expected validation error:", str(exc))

    else:
        raise AssertionError(
            "Negative verified_field_count was incorrectly accepted."
        )

    print()
    print("=" * 70)
    print("APPLICATION SUBMISSION SERVICE TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())