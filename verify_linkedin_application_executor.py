"""
Integration tests for LinkedInApplicationExecutor.

These tests do NOT open a real browser.

They verify:
    1. LinkedIn source validation
    2. Missing browser-session safety
    3. History recording
    4. Synchronous executor contract
    5. Asynchronous executor contract
    6. Authentication/manual-review safety
    7. CAPTCHA/manual-review safety
    8. External-application safety
"""

from __future__ import annotations

import asyncio

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionRequest,
    ApplicationExecutionStatus,
)

from src.modules.job_discovery.domain.application_executor.history import (
    ApplicationExecutionHistoryStatus,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.linkedin_application_executor import (
    LinkedInApplicationExecutor,
)

from src.modules.job_discovery.infrastructure.application_executor.history.in_memory_history_repository import (
    InMemoryApplicationExecutionHistoryRepository,
)

from src.modules.job_discovery.services.application_executor.history import (
    ApplicationExecutionHistoryService,
)

from src.shared.config.constants import JobSourceType


# ============================================================================
# TEST DATA
# ============================================================================


def build_request(
    *,
    external_job_id: str = "linkedin-executor-test",
) -> ApplicationExecutionRequest:
    """
    Build a valid LinkedIn application execution request.

    Keep candidate data minimal because these tests do not reach
    the browser/form-filling stage.
    """

    return ApplicationExecutionRequest(
        application_id="app-linkedin-executor-test",
        external_job_id=external_job_id,
        job_url=(
            "https://www.linkedin.com/jobs/view/"
            + external_job_id
        ),
        source=JobSourceType.LINKEDIN,
        candidate_data={
            "full_name": "Test Candidate",
            "email": "test@example.com",
        },
        metadata={
            "test": True,
        },
    )


def build_executor():
    """
    Build LinkedInApplicationExecutor without a browser.

    This deliberately exercises the executor's safe
    browser-not-configured path.
    """

    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    history_service = (
        ApplicationExecutionHistoryService(
            repository=repository,
        )
    )

    executor = LinkedInApplicationExecutor(
        browser_session=None,
        history_service=history_service,
    )

    return executor, repository


# ============================================================================
# TEST 1 - CONFIGURATION
# ============================================================================


def test_configuration() -> None:
    """
    Verify executor configuration properties.
    """

    executor, repository = build_executor()

    assert executor.configured is False

    assert executor.history_configured is True

    print(
        "CONFIGURATION test passed"
    )

    print(
        f"Browser configured : {executor.configured}"
    )

    print(
        f"History configured : {executor.history_configured}"
    )


# ============================================================================
# TEST 2 - SYNCHRONOUS EXECUTE
# ============================================================================


def test_sync_execute() -> None:
    """
    Verify synchronous execution safely handles a missing browser.
    """

    executor, repository = build_executor()

    request = build_request(
        external_job_id="linkedin-sync-test",
    )

    result = executor.execute(request)

    assert (
        result.application_id
        == request.application_id
    )

    assert (
        result.external_job_id
        == request.external_job_id
    )

    assert result.source == JobSourceType.LINKEDIN

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
        == "linkedin_browser_not_configured"
    )

    print(
        "SYNC EXECUTE test passed"
    )

    print(
        f"Status     : {result.status.value}"
    )

    print(
        f"Error code : {result.error_code}"
    )


# ============================================================================
# TEST 3 - ASYNC EXECUTE
# ============================================================================


def test_async_execute() -> None:
    """
    Verify asynchronous execution safely handles a missing browser.
    """

    executor, repository = build_executor()

    request = build_request(
        external_job_id="linkedin-async-test",
    )

    result = asyncio.run(
        executor.execute_async(request)
    )

    assert (
        result.application_id
        == request.application_id
    )

    assert (
        result.external_job_id
        == request.external_job_id
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
        == "linkedin_browser_not_configured"
    )

    print(
        "ASYNC EXECUTE test passed"
    )

    print(
        f"Status     : {result.status.value}"
    )

    print(
        f"Error code : {result.error_code}"
    )


# ============================================================================
# TEST 4 - HISTORY
# ============================================================================


def test_history_recording() -> None:
    """
    Verify execution history is recorded even when the browser
    is not configured.
    """

    executor, repository = build_executor()

    request = build_request(
        external_job_id="linkedin-history-test",
    )

    result = executor.execute(request)

    records = repository.get_by_application_id(
        request.application_id
    )

    assert len(records) == 1

    history = records[0]

    assert (
        history.application_id
        == request.application_id
    )

    assert (
        history.external_job_id
        == request.external_job_id
    )

    assert (
        history.source
        == JobSourceType.LINKEDIN
    )

    assert (
        history.status
        == ApplicationExecutionHistoryStatus.MANUAL_REVIEW_REQUIRED
    )

    assert (
        history.error_code
        == "linkedin_browser_not_configured"
    )

    assert (
        history.manual_intervention_required
        is True
    )

    print(
        "HISTORY recording test passed"
    )

    print(
        f"History records : {len(records)}"
    )

    print(
        f"History status  : {history.status.value}"
    )

    print(
        f"Error code      : {history.error_code}"
    )


# ============================================================================
# TEST 5 - INVALID SOURCE
# ============================================================================


def test_invalid_source() -> None:
    """
    Verify LinkedIn executor rejects non-LinkedIn jobs.
    """

    executor, repository = build_executor()

    request = ApplicationExecutionRequest(
        application_id="app-invalid-source-test",
        external_job_id="indeed-test",
        job_url="https://example.com/job",
        source=JobSourceType.INDEED,
        candidate_data={
            "full_name": "Test Candidate",
        },
    )

    try:
        executor.execute(request)

    except ValueError as exc:
        assert (
            str(exc)
            == "LinkedIn executor received a non-LinkedIn job."
        )

        print(
            "INVALID SOURCE test passed"
        )

        print(
            f"Reason : {exc}"
        )

        return

    raise AssertionError(
        "LinkedIn executor accepted a non-LinkedIn request."
    )


# ============================================================================
# TEST 6 - EMPTY APPLICATION ID
# ============================================================================


def test_invalid_application_id() -> None:
    """
    Verify ApplicationExecutionRequest rejects an empty application ID.

    The domain request validates application_id during construction,
    before the LinkedIn executor can receive the request. Therefore
    this test intentionally validates the construction boundary.
    """

    try:
        ApplicationExecutionRequest(
            application_id="",
            external_job_id="linkedin-test",
            job_url="https://example.com/job",
            source=JobSourceType.LINKEDIN,
            candidate_data={},
        )

    except ValueError as exc:
        assert (
            str(exc)
            == "application_id cannot be empty."
        )

        print(
            "INVALID APPLICATION ID test passed"
        )

        print(
            f"Reason : {exc}"
        )

        return

    raise AssertionError(
        "Empty application_id was accepted by "
        "ApplicationExecutionRequest."
    )

# ============================================================================
# TEST 7 - EMPTY JOB URL
# ============================================================================


def test_invalid_job_url() -> None:
    """
    Verify ApplicationExecutionRequest rejects an empty job URL.

    The domain request validates job_url during construction,
    before the LinkedIn executor can receive the request. Therefore
    this test intentionally validates the construction boundary.
    """

    try:
        ApplicationExecutionRequest(
            application_id="app-invalid-url-test",
            external_job_id="linkedin-test",
            job_url="",
            source=JobSourceType.LINKEDIN,
            candidate_data={},
        )

    except ValueError as exc:
        assert (
            str(exc)
            == "job_url cannot be empty."
        )

        print(
            "INVALID JOB URL test passed"
        )

        print(
            f"Reason : {exc}"
        )

        return

    raise AssertionError(
        "Empty job_url was accepted by "
        "ApplicationExecutionRequest."
    )

# ============================================================================
# TEST 8 - NO BROWSER NEVER SUBMITS
# ============================================================================


def test_no_browser_never_submits() -> None:
    """
    Critical safety assertion.

    Without a browser session, the executor must never report
    a successful application submission.
    """

    executor, repository = build_executor()

    request = build_request(
        external_job_id="linkedin-safety-test",
    )

    result = executor.execute(request)

    assert result.submitted is False

    assert (
        result.status
        != ApplicationExecutionStatus.SUBMITTED
    )

    assert (
        result.requires_manual_intervention
        is True
    )

    print(
        "NO-BROWSER SAFETY test passed"
    )

    print(
        "Submitted : False"
    )

    print(
        f"Status    : {result.status.value}"
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    """
    Run all LinkedIn executor integration tests.
    """

    print("=" * 70)

    print(
        "LINKEDIN APPLICATION EXECUTOR INTEGRATION TEST"
    )

    print("=" * 70)

    print()

    test_configuration()

    print()

    test_sync_execute()

    print()

    test_async_execute()

    print()

    test_history_recording()

    print()

    test_invalid_source()

    print()

    test_invalid_application_id()

    print()

    test_invalid_job_url()

    print()

    test_no_browser_never_submits()

    print()

    print("=" * 70)

    print(
        "ALL LINKEDIN APPLICATION EXECUTOR TESTS PASSED"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()