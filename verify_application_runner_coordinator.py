"""
Integration test for ApplicationRunnerCoordinator.

Tests the complete application lifecycle using only free/local
in-memory components.

No browser, LinkedIn, database, or external service is required.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionRequest,
    ApplicationExecutionResult,
    ApplicationExecutionStatus,
)

from src.modules.job_discovery.domain.application_executor.history import (
    ApplicationExecutionHistoryStatus,
)

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)

from src.modules.job_discovery.infrastructure.application_executor.history.in_memory_history_repository import (
    InMemoryApplicationExecutionHistoryRepository,
)

from src.modules.job_discovery.services.application_executor.application_executor_service import (
    ApplicationExecutorService,
)

from src.modules.job_discovery.services.application_executor.history.history_service import (
    ApplicationExecutionHistoryService,
)

from src.modules.job_discovery.services.application_queue.application_queue_service import (
    ApplicationQueueService,
)

from src.modules.job_discovery.services.application_runner.coordinator import (
    ApplicationRunnerCoordinator,
)

from src.modules.job_discovery.services.application_runner.application_runner_service import (
    ApplicationRunnerService,
)

from src.shared.config.constants import (
    EmploymentType,
    JobSourceType,
    RemoteStatus,
)


# ============================================================================
# MOCK EXECUTORS
# ============================================================================


class SuccessfulMockExecutor:
    """
    Mock executor that simulates a successful submission.

    This deliberately contains no browser logic.
    """

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
            reason="Mock application submitted successfully.",
            fields_detected=8,
            fields_filled=8,
            started_at=None,
            completed_at=None,
            metadata={
                "confirmation_id": "MOCK-CONFIRM-001",
                "form_type": "mock_easy_apply",
            },
        )


class FailedMockExecutor:
    """
    Mock executor that simulates a failed execution.
    """

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:

        return ApplicationExecutionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=ApplicationExecutionStatus.FAILED,
            submitted=False,
            reason="Mock executor failure.",
            error_code="mock_failure",
            fields_detected=5,
            fields_filled=2,
            metadata={
                "form_type": "mock_easy_apply",
            },
        )


class CaptchaMockExecutor:
    """
    Mock executor that simulates CAPTCHA detection.
    """

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
            reason="Mock CAPTCHA detected.",
            error_code="captcha_detected",
            fields_detected=6,
            fields_filled=4,
            metadata={
                "form_type": "mock_easy_apply",
            },
        )


# ============================================================================
# TEST DATA
# ============================================================================


def build_job(
    external_id: str,
) -> DiscoveredJob:
    """
    Create a normalized test job.
    """

    return DiscoveredJob(
        external_id=external_id,
        title="Data Analyst",
        company_name="Coordinator Test Company",
        source=JobSourceType.LINKEDIN,
        url="https://example.com/jobs/" + external_id,
        location="Hyderabad",
        remote_status=RemoteStatus.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        description="Test Data Analyst position.",
    )


# ============================================================================
# COORDINATOR SETUP
# ============================================================================


def build_coordinator(
    executor,
) -> tuple[
    ApplicationQueueService,
    ApplicationRunnerCoordinator,
    InMemoryApplicationExecutionHistoryRepository,
]:
    """
    Build a complete in-memory coordinator stack.
    """

    # Queue service belongs to the SERVICE layer.
    queue_service = ApplicationQueueService()

    # Application runner state machine.
    runner_service = ApplicationRunnerService()

    # Application executor service.
    executor_service = ApplicationExecutorService(
        executor=executor,
    )

    # In-memory execution history repository.
    history_repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    # History application service.
    history_service = ApplicationExecutionHistoryService(
        repository=history_repository,
    )

    # Coordinator combines runner + executor + history.
    coordinator = ApplicationRunnerCoordinator(
        runner_service=runner_service,
        executor_service=executor_service,
        history_service=history_service,
    )

    return (
        queue_service,
        coordinator,
        history_repository,
    )


# ============================================================================
# QUEUE HELPER
# ============================================================================


def enqueue_test_job(
    queue_service: ApplicationQueueService,
    external_id: str,
):
    """
    Add one test job to the application queue.
    """

    decision = queue_service.enqueue(
        build_job(external_id),
        match_score=0.92,
        priority=10,
    )

    if not decision.accepted:
        raise AssertionError(
            "Test job was not accepted into the queue."
        )

    if decision.item is None:
        raise AssertionError(
            "Accepted queue decision must contain an item."
        )

    return decision.item


# ============================================================================
# TEST 1 - SUCCESSFUL SUBMISSION
# ============================================================================


def test_successful_submission() -> None:
    """
    Test successful application submission.
    """

    (
        queue_service,
        coordinator,
        history_repository,
    ) = build_coordinator(
        SuccessfulMockExecutor()
    )

    item = enqueue_test_job(
        queue_service,
        "coordinator-success-test",
    )

    result = coordinator.run(item)

    assert result.application_id == item.application_id

    assert result.external_job_id == item.external_job_id

    assert (
        result.execution_result.status
        == ApplicationExecutionStatus.SUBMITTED
    )

    assert result.execution_result.submitted is True

    assert result.runner_state.status.value == "submitted"

    assert result.history_recorded is True

    assert result.history is not None

    assert (
        result.history.status
        == ApplicationExecutionHistoryStatus.SUBMITTED
    )

    assert result.history.confirmation_id == (
        "MOCK-CONFIRM-001"
    )

    records = history_repository.get_by_application_id(
        item.application_id
    )

    assert len(records) == 1

    print(
        "SUCCESSFUL SUBMISSION test passed"
    )

    print(
        f"Application ID : {result.application_id}"
    )

    print(
        f"Status         : {result.runner_state.status.value}"
    )

    print(
        f"Confirmation   : {result.history.confirmation_id}"
    )


# ============================================================================
# TEST 2 - FAILED EXECUTION
# ============================================================================


def test_failed_execution() -> None:
    """
    Test failed execution lifecycle.
    """

    (
        queue_service,
        coordinator,
        history_repository,
    ) = build_coordinator(
        FailedMockExecutor()
    )

    item = enqueue_test_job(
        queue_service,
        "coordinator-failure-test",
    )

    result = coordinator.run(item)

    assert (
        result.execution_result.status
        == ApplicationExecutionStatus.FAILED
    )

    assert result.execution_result.submitted is False

    assert result.runner_state.status.value == "failed"

    assert result.runner_state.error_code == (
        "mock_failure"
    )

    assert result.history is not None

    assert (
        result.history.status
        == ApplicationExecutionHistoryStatus.FAILED
    )

    assert result.history.error_code == (
        "mock_failure"
    )

    records = history_repository.get_by_application_id(
        item.application_id
    )

    assert len(records) == 1

    print(
        "FAILED EXECUTION test passed"
    )

    print(
        f"Application ID : {result.application_id}"
    )

    print(
        f"Status         : {result.runner_state.status.value}"
    )

    print(
        f"Error code     : {result.history.error_code}"
    )


# ============================================================================
# TEST 3 - CAPTCHA / MANUAL INTERVENTION
# ============================================================================


def test_captcha_manual_intervention() -> None:
    """
    Test CAPTCHA handling without bypassing it.
    """

    (
        queue_service,
        coordinator,
        history_repository,
    ) = build_coordinator(
        CaptchaMockExecutor()
    )

    item = enqueue_test_job(
        queue_service,
        "coordinator-captcha-test",
    )

    result = coordinator.run(item)

    assert (
        result.execution_result.status
        == ApplicationExecutionStatus.CAPTCHA_DETECTED
    )

    assert result.execution_result.submitted is False

    assert (
        result.execution_result.requires_manual_intervention
        is True
    )

    assert (
        result.runner_state.status.value
        == "captcha_detected"
    )

    assert (
        result.runner_state.requires_manual_intervention
        is True
    )

    assert result.history is not None

    assert (
        result.history.status
        == ApplicationExecutionHistoryStatus.MANUAL_REVIEW_REQUIRED
    )

    assert (
        result.history.manual_intervention_required
        is True
    )

    records = history_repository.get_by_application_id(
        item.application_id
    )

    assert len(records) == 1

    print(
        "CAPTCHA manual-intervention test passed"
    )

    print(
        f"Application ID : {result.application_id}"
    )

    print(
        f"Status         : {result.runner_state.status.value}"
    )

    print(
        "Manual review  : "
        f"{result.history.manual_intervention_required}"
    )


# ============================================================================
# TEST 4 - EXECUTOR NOT CONFIGURED
# ============================================================================


def test_executor_not_configured() -> None:
    """
    Verify safe behavior when no executor is configured.
    """

    queue_service = ApplicationQueueService()

    runner_service = ApplicationRunnerService()

    executor_service = ApplicationExecutorService()

    history_repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    history_service = ApplicationExecutionHistoryService(
        repository=history_repository,
    )

    coordinator = ApplicationRunnerCoordinator(
        runner_service=runner_service,
        executor_service=executor_service,
        history_service=history_service,
    )

    item = enqueue_test_job(
        queue_service,
        "coordinator-no-executor-test",
    )

    result = coordinator.run(item)

    assert (
        result.execution_result.status
        == ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert (
        result.execution_result.error_code
        == "executor_not_configured"
    )

    assert result.runner_state.status.value == (
        "manual_review_required"
    )

    assert (
        result.runner_state.requires_manual_intervention
        is True
    )

    assert result.history is not None

    assert (
        result.history.status
        == ApplicationExecutionHistoryStatus.MANUAL_REVIEW_REQUIRED
    )

    print(
        "EXECUTOR NOT CONFIGURED test passed"
    )

    print(
        "Status         : "
        f"{result.runner_state.status.value}"
    )

    print(
        "Error code     : "
        f"{result.execution_result.error_code}"
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    """
    Run all coordinator integration tests.
    """

    print("=" * 70)
    print(
        "APPLICATION RUNNER COORDINATOR INTEGRATION TEST"
    )
    print("=" * 70)
    print()

    test_successful_submission()
    print()

    test_failed_execution()
    print()

    test_captcha_manual_intervention()
    print()

    test_executor_not_configured()
    print()

    print("=" * 70)
    print(
        "ALL APPLICATION RUNNER COORDINATOR TESTS PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()