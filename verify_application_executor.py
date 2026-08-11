"""
Application Executor Service Integration Test.

Tests the application executor service without connecting to a real
portal or browser.

The fake executors simulate:
    - successful submission
    - execution failure
    - authentication requirement
    - CAPTCHA detection
    - manual review
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionRequest,
    ApplicationExecutionResult,
    ApplicationExecutionStatus,
)
from src.modules.job_discovery.services.application_executor import (
    ApplicationExecutorService,
)
from src.shared.config.constants import JobSourceType


def create_request(
    application_id: str,
    external_job_id: str,
) -> ApplicationExecutionRequest:
    """Create a standard test request."""

    return ApplicationExecutionRequest(
        application_id=application_id,
        external_job_id=external_job_id,
        job_url=(
            "https://www.linkedin.com/jobs/view/"
            f"{external_job_id}"
        ),
        source=JobSourceType.LINKEDIN,
        resume_id="resume-test-001",
        cover_letter_id="cover-letter-test-001",
        candidate_data={
            "first_name": "Test",
            "last_name": "Candidate",
            "email": "test@example.com",
        },
        metadata={
            "test": "application_executor",
        },
    )


class SuccessfulFakeExecutor:
    """Fake executor that simulates successful submission."""

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:

        return ApplicationExecutionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=ApplicationExecutionStatus.SUBMITTED,
            submitted=True,
            requires_manual_intervention=False,
            reason="Application submitted successfully.",
            fields_detected=12,
            fields_filled=12,
            metadata={
                "executor": "fake_success",
                "submission_reference": "fake-submit-001",
            },
        )


class FailingFakeExecutor:
    """Fake executor that simulates an execution failure."""

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:

        raise RuntimeError(
            "Simulated browser execution failure."
        )


class AuthenticationFakeExecutor:
    """Fake executor that simulates an authentication requirement."""

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:

        return ApplicationExecutionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=(
                ApplicationExecutionStatus.AUTHENTICATION_REQUIRED
            ),
            submitted=False,
            requires_manual_intervention=True,
            reason=(
                "Authentication is required before the "
                "application can continue."
            ),
            error_code="authentication_required",
            metadata={
                "executor": "fake_authentication",
            },
        )


class CaptchaFakeExecutor:
    """Fake executor that simulates CAPTCHA detection."""

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:

        return ApplicationExecutionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=ApplicationExecutionStatus.CAPTCHA_DETECTED,
            submitted=False,
            requires_manual_intervention=True,
            reason=(
                "CAPTCHA was detected. Manual intervention "
                "is required."
            ),
            error_code="captcha_detected",
            metadata={
                "executor": "fake_captcha",
            },
        )


class ManualReviewFakeExecutor:
    """Fake executor that simulates a manual-review requirement."""

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:

        return ApplicationExecutionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=(
                ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
            ),
            submitted=False,
            requires_manual_intervention=True,
            reason=(
                "Application requires manual review."
            ),
            error_code="manual_review_required",
            metadata={
                "executor": "fake_manual_review",
            },
        )


class WrongIdentityFakeExecutor:
    """Fake executor returning an incorrect application identity."""

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:

        return ApplicationExecutionResult(
            application_id="wrong-application-id",
            external_job_id=request.external_job_id,
            source=request.source,
            status=ApplicationExecutionStatus.SUBMITTED,
            submitted=True,
            requires_manual_intervention=False,
            fields_detected=5,
            fields_filled=5,
        )


def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION EXECUTOR SERVICE INTEGRATION TEST")
    print("=" * 70)

    # ==============================================================
    # 1/10
    # ==============================================================

    print()
    print("[1/10] Creating executor service...")

    service = ApplicationExecutorService()

    assert service.executor_configured is False

    print("EXECUTOR SERVICE creation successful")
    print(
        "Executor configured:",
        service.executor_configured,
    )

    # ==============================================================
    # 2/10
    # ==============================================================

    print()
    print("[2/10] Testing execution request validation...")

    request = create_request(
        "executor-test-001",
        "linkedin-job-001",
    )

    ApplicationExecutorService.validate_request(
        request
    )

    print("REQUEST validation successful")
    print("Application ID:", request.application_id)
    print("External Job ID:", request.external_job_id)

    # ==============================================================
    # 3/10
    # ==============================================================

    print()
    print("[3/10] Testing execution context lifecycle...")

    context = service.create_context(
        request
    )

    assert (
        context.status
        == ApplicationExecutionStatus.READY
    )

    context = service.start_context(
        context
    )

    assert (
        context.status
        == ApplicationExecutionStatus.STARTED
    )

    context = service.record_form(
        context,
        fields_detected=10,
    )

    assert (
        context.status
        == ApplicationExecutionStatus.FORM_DETECTED
    )

    assert context.fields_detected == 10

    context = service.record_fields(
        context,
        fields_filled=8,
    )

    assert (
        context.status
        == ApplicationExecutionStatus.FIELDS_MAPPED
    )

    assert context.fields_filled == 8

    print("EXECUTION CONTEXT lifecycle successful")
    print(
        "Status:",
        context.status.value,
    )
    print(
        "Fields detected:",
        context.fields_detected,
    )
    print(
        "Fields filled:",
        context.fields_filled,
    )

    # ==============================================================
    # 4/10
    # ==============================================================

    print()
    print("[4/10] Testing successful executor...")

    service = ApplicationExecutorService(
        SuccessfulFakeExecutor()
    )

    request = create_request(
        "executor-test-002",
        "linkedin-job-002",
    )

    result = service.execute(
        request
    )

    assert (
        result.status
        == ApplicationExecutionStatus.SUBMITTED
    )

    assert result.submitted is True

    assert (
        result.requires_manual_intervention
        is False
    )

    assert result.fields_detected == 12
    assert result.fields_filled == 12

    print("SUCCESSFUL execution successful")
    print("Status:", result.status.value)
    print("Submitted:", result.submitted)
    print(
        "Fields:",
        f"{result.fields_filled}/{result.fields_detected}",
    )

    # ==============================================================
    # 5/10
    # ==============================================================

    print()
    print("[5/10] Testing executor failure handling...")

    service = ApplicationExecutorService(
        FailingFakeExecutor()
    )

    request = create_request(
        "executor-test-003",
        "linkedin-job-003",
    )

    result = service.execute(
        request
    )

    assert (
        result.status
        == ApplicationExecutionStatus.FAILED
    )

    assert result.submitted is False

    assert (
        result.error_code
        == "executor_execution_failed"
    )

    print("FAILURE handling successful")
    print("Status:", result.status.value)
    print("Error:", result.error_code)

    # ==============================================================
    # 6/10
    # ==============================================================

    print()
    print("[6/10] Testing executor-not-configured handling...")

    service = ApplicationExecutorService()

    request = create_request(
        "executor-test-004",
        "linkedin-job-004",
    )

    result = service.execute(
        request
    )

    assert (
        result.status
        == ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert result.submitted is False

    assert (
        result.requires_manual_intervention
        is True
    )

    assert (
        result.error_code
        == "executor_not_configured"
    )

    print("NO EXECUTOR handling successful")
    print("Status:", result.status.value)
    print(
        "Manual intervention:",
        result.requires_manual_intervention,
    )

    # ==============================================================
    # 7/10
    # ==============================================================

    print()
    print("[7/10] Testing authentication handling...")

    service = ApplicationExecutorService(
        AuthenticationFakeExecutor()
    )

    request = create_request(
        "executor-test-005",
        "linkedin-job-005",
    )

    result = service.execute(
        request
    )

    assert (
        result.status
        == ApplicationExecutionStatus.AUTHENTICATION_REQUIRED
    )

    assert result.submitted is False

    assert (
        result.requires_manual_intervention
        is True
    )

    assert (
        result.error_code
        == "authentication_required"
    )

    print("AUTHENTICATION handling successful")
    print("Status:", result.status.value)
    print(
        "Manual intervention:",
        result.requires_manual_intervention,
    )

    # ==============================================================
    # 8/10
    # ==============================================================

    print()
    print("[8/10] Testing CAPTCHA handling...")

    service = ApplicationExecutorService(
        CaptchaFakeExecutor()
    )

    request = create_request(
        "executor-test-006",
        "linkedin-job-006",
    )

    result = service.execute(
        request
    )

    assert (
        result.status
        == ApplicationExecutionStatus.CAPTCHA_DETECTED
    )

    assert result.submitted is False

    assert (
        result.requires_manual_intervention
        is True
    )

    assert (
        result.error_code
        == "captcha_detected"
    )

    print("CAPTCHA handling successful")
    print("Status:", result.status.value)
    print(
        "Manual intervention:",
        result.requires_manual_intervention,
    )

    # ==============================================================
    # 9/10
    # ==============================================================

    print()
    print("[9/10] Testing manual-review handling...")

    service = ApplicationExecutorService(
        ManualReviewFakeExecutor()
    )

    request = create_request(
        "executor-test-007",
        "linkedin-job-007",
    )

    result = service.execute(
        request
    )

    assert (
        result.status
        == ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert result.submitted is False

    assert (
        result.requires_manual_intervention
        is True
    )

    assert (
        result.error_code
        == "manual_review_required"
    )

    print("MANUAL REVIEW handling successful")
    print("Status:", result.status.value)
    print(
        "Manual intervention:",
        result.requires_manual_intervention,
    )

    # ==============================================================
    # 10/10
    # ==============================================================

    print()
    print("[10/10] Testing executor identity protection...")

    service = ApplicationExecutorService(
        WrongIdentityFakeExecutor()
    )

    request = create_request(
        "executor-test-008",
        "linkedin-job-008",
    )

    try:
        service.execute(
            request
        )
    except ValueError as exc:
        identity_protection = True
        print("Expected validation error:", str(exc))
    else:
        identity_protection = False

    assert identity_protection is True

    print("IDENTITY protection successful")
    print(
        "Executor cannot return a different application ID."
    )

    # ==============================================================
    # Final
    # ==============================================================

    print()
    print("=" * 70)
    print("APPLICATION EXECUTOR SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()