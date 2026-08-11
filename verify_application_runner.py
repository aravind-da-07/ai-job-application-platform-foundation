"""
Application Runner Service Integration Test.

Tests the complete application lifecycle:

    QUEUED
       ↓
    IN_PROGRESS
       ├── SUBMITTED
       ├── FAILED → RETRY → QUEUED
       ├── AUTHENTICATION_REQUIRED
       ├── CAPTCHA_DETECTED
       └── MANUAL_REVIEW_REQUIRED
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_runner import (
    ApplicationRunRequest,
)
from src.modules.job_discovery.services.application_runner import (
    ApplicationRunnerService,
)
from src.shared.config.constants import (
    ApplicationResult,
    ApplicationStatus,
    JobSourceType,
)


def create_request(
    application_id: str,
    external_job_id: str,
    *,
    maximum_attempts: int = 3,
) -> ApplicationRunRequest:
    """Create a deterministic runner test request."""

    return ApplicationRunRequest(
        application_id=application_id,
        external_job_id=external_job_id,
        job_url=(
            "https://www.linkedin.com/jobs/view/"
            f"{external_job_id}"
        ),
        source=JobSourceType.LINKEDIN,
        resume_id="resume-test-001",
        cover_letter_id="cover-letter-test-001",
        maximum_attempts=maximum_attempts,
        metadata={
            "test": "application_runner",
        },
    )


def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION RUNNER SERVICE INTEGRATION TEST")
    print("=" * 70)

    # ==============================================================
    # 1/10
    # ==============================================================

    print()
    print("[1/10] Creating application runner...")

    runner = ApplicationRunnerService()

    assert runner.size == 0

    print("APPLICATION RUNNER creation successful")
    print("Initial state count:", runner.size)

    # ==============================================================
    # 2/10
    # ==============================================================

    print()
    print("[2/10] Testing application registration...")

    request = create_request(
        "runner-test-001",
        "linkedin-job-001",
    )

    state = runner.register(request)

    assert state.application_id == "runner-test-001"
    assert state.external_job_id == "linkedin-job-001"
    assert state.status == ApplicationStatus.QUEUED
    assert state.last_result == ApplicationResult.PENDING
    assert state.attempt_number == 0
    assert state.maximum_attempts == 3

    print("REGISTRATION successful")
    print("Application ID:", state.application_id)
    print("Status:", state.status.value)
    print("Attempt:", state.attempt_number)

    # ==============================================================
    # 3/10
    # ==============================================================

    print()
    print("[3/10] Testing QUEUED → IN_PROGRESS...")

    state = runner.start(
        "runner-test-001"
    )

    assert state.status == ApplicationStatus.IN_PROGRESS
    assert state.attempt_number == 1
    assert state.started_at is not None

    print("START transition successful")
    print("Status:", state.status.value)
    print("Attempt:", state.attempt_number)

    # ==============================================================
    # 4/10
    # ==============================================================

    print()
    print("[4/10] Testing successful submission...")

    state = runner.mark_submitted(
        "runner-test-001",
        reason="Test application submitted successfully.",
        metadata={
            "portal": "linkedin",
            "submission_reference": "test-submit-001",
        },
    )

    assert state.status == ApplicationStatus.SUBMITTED
    assert state.last_result == ApplicationResult.YES
    assert state.completed_at is not None
    assert state.requires_manual_intervention is False
    assert (
        state.metadata["submission_reference"]
        == "test-submit-001"
    )

    print("SUBMISSION transition successful")
    print("Status:", state.status.value)
    print("Result:", state.last_result.value)
    print(
        "Manual intervention:",
        state.requires_manual_intervention,
    )

    # ==============================================================
    # 5/10
    # ==============================================================

    print()
    print("[5/10] Testing terminal-state protection...")

    try:
        runner.start(
            "runner-test-001"
        )
    except ValueError:
        terminal_protection = True
    else:
        terminal_protection = False

    assert terminal_protection is True

    print("TERMINAL STATE protection successful")
    print("Submitted application cannot be started again")

    # ==============================================================
    # 6/10
    # ==============================================================

    print()
    print("[6/10] Testing failure and retry...")

    failed_request = create_request(
        "runner-test-002",
        "linkedin-job-002",
    )

    state = runner.register(
        failed_request
    )

    state = runner.start(
        "runner-test-002"
    )

    assert state.status == ApplicationStatus.IN_PROGRESS
    assert state.attempt_number == 1

    state = runner.mark_failed(
        "runner-test-002",
        reason="Test browser execution failure.",
        error_code="browser_execution_failed",
    )

    assert state.status == ApplicationStatus.FAILED
    assert state.last_result == ApplicationResult.NO
    assert state.error_code == "browser_execution_failed"
    assert state.completed_at is not None

    print("FAILURE transition successful")
    print("Status:", state.status.value)
    print("Result:", state.last_result.value)
    print("Error:", state.error_code)

    state = runner.retry(
        "runner-test-002"
    )

    assert state.status == ApplicationStatus.QUEUED
    assert state.attempt_number == 1

    print("RETRY transition successful")
    print("Status:", state.status.value)
    print("Attempt:", state.attempt_number)

    # ==============================================================
    # 7/10
    # ==============================================================

    print()
    print("[7/10] Testing authentication-required state...")

    auth_request = create_request(
        "runner-test-003",
        "linkedin-job-003",
    )

    runner.register(
        auth_request
    )

    runner.start(
        "runner-test-003"
    )

    state = runner.mark_authentication_required(
        "runner-test-003"
    )

    assert (
        state.status
        == ApplicationStatus.AUTHENTICATION_REQUIRED
    )

    assert (
        state.last_result
        == ApplicationResult.PENDING
    )

    assert state.requires_manual_intervention is True
    assert state.error_code == "authentication_required"

    print("AUTHENTICATION REQUIRED transition successful")
    print("Status:", state.status.value)
    print(
        "Manual intervention:",
        state.requires_manual_intervention,
    )

    # ==============================================================
    # 8/10
    # ==============================================================

    print()
    print("[8/10] Testing CAPTCHA state...")

    captcha_request = create_request(
        "runner-test-004",
        "linkedin-job-004",
    )

    runner.register(
        captcha_request
    )

    runner.start(
        "runner-test-004"
    )

    state = runner.mark_captcha_detected(
        "runner-test-004"
    )

    assert (
        state.status
        == ApplicationStatus.CAPTCHA_DETECTED
    )

    assert (
        state.last_result
        == ApplicationResult.PENDING
    )

    assert state.requires_manual_intervention is True
    assert state.error_code == "captcha_detected"

    print("CAPTCHA transition successful")
    print("Status:", state.status.value)
    print(
        "Manual intervention:",
        state.requires_manual_intervention,
    )

    # ==============================================================
    # 9/10
    # ==============================================================

    print()
    print("[9/10] Testing manual-review state...")

    review_request = create_request(
        "runner-test-005",
        "linkedin-job-005",
    )

    runner.register(
        review_request
    )

    runner.start(
        "runner-test-005"
    )

    state = runner.mark_manual_review_required(
        "runner-test-005"
    )

    assert (
        state.status
        == ApplicationStatus.MANUAL_REVIEW_REQUIRED
    )

    assert (
        state.last_result
        == ApplicationResult.PENDING
    )

    assert state.requires_manual_intervention is True
    assert state.error_code == "manual_review_required"

    print("MANUAL REVIEW transition successful")
    print("Status:", state.status.value)
    print(
        "Manual intervention:",
        state.requires_manual_intervention,
    )

    # ==============================================================
    # 10/10
    # ==============================================================

    print()
    print("[10/10] Testing runner state lookup and isolation...")

    assert runner.has(
        "runner-test-001"
    )

    assert runner.has(
        "runner-test-002"
    )

    assert runner.has(
        "runner-test-003"
    )

    assert runner.has(
        "runner-test-004"
    )

    assert runner.has(
        "runner-test-005"
    )

    submitted = runner.get(
        "runner-test-001"
    )

    failed = runner.get(
        "runner-test-002"
    )

    authentication = runner.get(
        "runner-test-003"
    )

    captcha = runner.get(
        "runner-test-004"
    )

    manual_review = runner.get(
        "runner-test-005"
    )

    assert (
        submitted.status
        == ApplicationStatus.SUBMITTED
    )

    assert (
        failed.status
        == ApplicationStatus.QUEUED
    )

    assert (
        authentication.status
        == ApplicationStatus.AUTHENTICATION_REQUIRED
    )

    assert (
        captcha.status
        == ApplicationStatus.CAPTCHA_DETECTED
    )

    assert (
        manual_review.status
        == ApplicationStatus.MANUAL_REVIEW_REQUIRED
    )

    states = runner.list_states()

    assert len(states) == 5

    print("STATE LOOKUP successful")
    print("Tracked applications:", len(states))

    print()
    print("Application states:")

    for item in states:
        print(
            f"- {item.application_id} | "
            f"{item.status.value} | "
            f"attempt={item.attempt_number}"
        )

    print()
    print("=" * 70)
    print("APPLICATION RUNNER SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()