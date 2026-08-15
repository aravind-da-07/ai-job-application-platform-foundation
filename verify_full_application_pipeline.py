"""
Full Application Pipeline Integration Test.

Validates the local application pipeline from a discovered job
through queueing, runner coordination, execution, and history.

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

from src.modules.job_discovery.services.application_runner.application_runner_service import (
    ApplicationRunnerService,
)

from src.modules.job_discovery.services.application_runner.coordinator import (
    ApplicationRunnerCoordinator,
)

from src.shared.config.constants import (
    EmploymentType,
    JobSourceType,
    RemoteStatus,
)


# ============================================================================
# MOCK EXECUTOR
# ============================================================================


class EndToEndMockExecutor:
    """
    Local executor used to validate the complete application pipeline.

    No browser or external portal is contacted.
    """

    def __init__(
        self,
        *,
        status: ApplicationExecutionStatus = (
            ApplicationExecutionStatus.SUBMITTED
        ),
    ) -> None:
        self.status = status
        self.requests: list[
            ApplicationExecutionRequest
        ] = []

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:
        """
        Execute a deterministic local application simulation.
        """

        self.requests.append(request)

        if self.status == ApplicationExecutionStatus.SUBMITTED:
            return ApplicationExecutionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                source=request.source,
                status=ApplicationExecutionStatus.SUBMITTED,
                submitted=True,
                reason=(
                    "End-to-end mock application submitted successfully."
                ),
                fields_detected=8,
                fields_filled=8,
                metadata={
                    "confirmation_id": "E2E-MOCK-CONFIRM-001",
                    "form_type": "mock_easy_apply",
                    "pipeline": "full_application_pipeline",
                },
            )

        if self.status == ApplicationExecutionStatus.CAPTCHA_DETECTED:
            return ApplicationExecutionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                source=request.source,
                status=ApplicationExecutionStatus.CAPTCHA_DETECTED,
                submitted=False,
                requires_manual_intervention=True,
                reason="End-to-end mock CAPTCHA detected.",
                error_code="captcha_detected",
                fields_detected=6,
                fields_filled=4,
                metadata={
                    "form_type": "mock_easy_apply",
                    "pipeline": "full_application_pipeline",
                },
            )

        return ApplicationExecutionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=ApplicationExecutionStatus.FAILED,
            submitted=False,
            reason="End-to-end mock executor failure.",
            error_code="e2e_mock_failure",
            fields_detected=5,
            fields_filled=2,
            metadata={
                "form_type": "mock_easy_apply",
                "pipeline": "full_application_pipeline",
            },
        )


# ============================================================================
# TEST DATA
# ============================================================================


def build_job(
    external_id: str,
) -> DiscoveredJob:
    """
    Build a normalized discovered job.
    """

    return DiscoveredJob(
        external_id=external_id,
        title="Data Analyst",
        company_name="Full Pipeline Test Company",
        source=JobSourceType.LINKEDIN,
        url=(
            "https://www.linkedin.com/jobs/view/"
            + external_id
        ),
        location="Hyderabad, Telangana, India",
        remote_status=RemoteStatus.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "End-to-end integration test Data Analyst "
            "position."
        ),
    )


# ============================================================================
# PIPELINE SETUP
# ============================================================================


def build_pipeline(
    executor: EndToEndMockExecutor,
) -> tuple[
    ApplicationQueueService,
    ApplicationRunnerCoordinator,
    InMemoryApplicationExecutionHistoryRepository,
    EndToEndMockExecutor,
]:
    """
    Build the complete local application pipeline.
    """

    queue_service = ApplicationQueueService()

    runner_service = ApplicationRunnerService()

    executor_service = ApplicationExecutorService(
        executor=executor,
    )

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

    return (
        queue_service,
        coordinator,
        history_repository,
        executor,
    )


# ============================================================================
# TEST 1 - COMPLETE SUCCESS PIPELINE
# ============================================================================


def test_complete_success_pipeline() -> None:
    """
    Verify the complete successful application flow.
    """

    executor = EndToEndMockExecutor(
        status=ApplicationExecutionStatus.SUBMITTED,
    )

    (
        queue_service,
        coordinator,
        history_repository,
        executor,
    ) = build_pipeline(executor)

    job = build_job(
        "full-pipeline-success-001"
    )

    # --------------------------------------------------------------
    # Job → Queue
    # --------------------------------------------------------------

    decision = queue_service.enqueue(
        job,
        match_score=0.94,
        priority=10,
        metadata={
            "match_decision": "apply",
            "pipeline_test": True,
        },
    )

    assert decision.accepted is True
    assert decision.item is not None

    item = decision.item

    assert item.external_job_id == (
        "full-pipeline-success-001"
    )

    assert item.job_title == "Data Analyst"

    assert item.company_name == (
        "Full Pipeline Test Company"
    )

    assert item.source == JobSourceType.LINKEDIN

    assert item.match_score == 0.94

    assert item.status.value == "queued"

    # --------------------------------------------------------------
    # Queue → Coordinator
    # --------------------------------------------------------------

    result = coordinator.run(item)

    assert result.application_id == (
        item.application_id
    )

    assert result.external_job_id == (
        item.external_job_id
    )

    # --------------------------------------------------------------
    # Coordinator → Executor
    # --------------------------------------------------------------

    assert len(executor.requests) == 1

    request = executor.requests[0]

    assert request.application_id == (
        item.application_id
    )

    assert request.external_job_id == (
        item.external_job_id
    )

    assert request.job_url == item.job_url

    assert request.source == item.source

    # --------------------------------------------------------------
    # Executor result
    # --------------------------------------------------------------

    assert (
        result.execution_result.status
        == ApplicationExecutionStatus.SUBMITTED
    )

    assert result.execution_result.submitted is True

    assert result.execution_result.fields_detected == 8

    assert result.execution_result.fields_filled == 8

    # --------------------------------------------------------------
    # Runner state
    # --------------------------------------------------------------

    assert (
        result.runner_state.status.value
        == "submitted"
    )

    assert (
        result.runner_state.external_job_id
        == item.external_job_id
    )

    # --------------------------------------------------------------
    # History
    # --------------------------------------------------------------

    assert result.history_recorded is True

    assert result.history is not None

    assert (
        result.history.status
        == ApplicationExecutionHistoryStatus.SUBMITTED
    )

    assert (
        result.history.confirmation_id
        == "E2E-MOCK-CONFIRM-001"
    )

    records = (
        history_repository.get_by_application_id(
            item.application_id
        )
    )

    assert len(records) == 1

    print(
        "COMPLETE SUCCESS PIPELINE test passed"
    )

    print(
        f"Application ID : {item.application_id}"
    )

    print(
        f"Job ID         : {item.external_job_id}"
    )

    print(
        f"Match score    : {item.match_score:.0%}"
    )

    print(
        "Queue status   : "
        f"{item.status.value}"
    )

    print(
        "Execution      : "
        f"{result.execution_result.status.value}"
    )

    print(
        "Runner status  : "
        f"{result.runner_state.status.value}"
    )

    print(
        "History status : "
        f"{result.history.status.value}"
    )

    print(
        "Confirmation   : "
        f"{result.history.confirmation_id}"
    )


# ============================================================================
# TEST 2 - COMPLETE CAPTCHA PIPELINE
# ============================================================================


def test_complete_captcha_pipeline() -> None:
    """
    Verify that CAPTCHA flows safely through the complete pipeline.
    """

    executor = EndToEndMockExecutor(
        status=ApplicationExecutionStatus.CAPTCHA_DETECTED,
    )

    (
        queue_service,
        coordinator,
        history_repository,
        executor,
    ) = build_pipeline(executor)

    job = build_job(
        "full-pipeline-captcha-001"
    )

    decision = queue_service.enqueue(
        job,
        match_score=0.91,
        priority=8,
    )

    assert decision.accepted is True
    assert decision.item is not None

    item = decision.item

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

    records = (
        history_repository.get_by_application_id(
            item.application_id
        )
    )

    assert len(records) == 1

    print(
        "COMPLETE CAPTCHA PIPELINE test passed"
    )

    print(
        f"Application ID : {item.application_id}"
    )

    print(
        "Execution      : "
        f"{result.execution_result.status.value}"
    )

    print(
        "Runner status  : "
        f"{result.runner_state.status.value}"
    )

    print(
        "Manual review  : "
        f"{result.history.manual_intervention_required}"
    )


# ============================================================================
# TEST 3 - MULTI-JOB QUEUE PIPELINE
# ============================================================================


def test_multi_job_queue_pipeline() -> None:
    """
    Verify multiple queued jobs can be processed independently.
    """

    executor = EndToEndMockExecutor(
        status=ApplicationExecutionStatus.SUBMITTED,
    )

    (
        queue_service,
        coordinator,
        history_repository,
        executor,
    ) = build_pipeline(executor)

    jobs = [
        build_job("full-pipeline-batch-001"),
        build_job("full-pipeline-batch-002"),
        build_job("full-pipeline-batch-003"),
    ]

    scores = [
        0.95,
        0.88,
        0.81,
    ]

    items = []

    for job, score in zip(
        jobs,
        scores,
    ):
        decision = queue_service.enqueue(
            job,
            match_score=score,
            priority=5,
        )

        assert decision.accepted is True
        assert decision.item is not None

        items.append(decision.item)

    assert queue_service.size == 3

    queued_items = queue_service.queued_items()

    assert len(queued_items) == 3

    results = []

    for item in queued_items:
        result = coordinator.run(item)

        results.append(result)

    assert len(results) == 3

    assert len(executor.requests) == 3

    for result, item in zip(
        results,
        queued_items,
    ):
        assert (
            result.application_id
            == item.application_id
        )

        assert (
            result.external_job_id
            == item.external_job_id
        )

        assert (
            result.execution_result.status
            == ApplicationExecutionStatus.SUBMITTED
        )

        assert result.execution_result.submitted is True

        assert (
            result.runner_state.status.value
            == "submitted"
        )

        assert result.history is not None

        assert (
            result.history.status
            == ApplicationExecutionHistoryStatus.SUBMITTED
        )

        records = (
            history_repository.get_by_application_id(
                item.application_id
            )
        )

        assert len(records) == 1

    print(
        "MULTI-JOB QUEUE PIPELINE test passed"
    )

    print(
        "Jobs queued     : "
        f"{len(items)}"
    )

    print(
        "Jobs executed   : "
        f"{len(results)}"
    )

    print(
        "History records : "
        f"{sum(len(history_repository.get_by_application_id(item.application_id)) for item in items)}"
    )


# ============================================================================
# TEST 4 - DUPLICATE PROTECTION THROUGH QUEUE
# ============================================================================


def test_duplicate_job_never_reaches_executor() -> None:
    """
    Verify duplicate jobs are rejected before execution.
    """

    executor = EndToEndMockExecutor()

    (
        queue_service,
        coordinator,
        history_repository,
        executor,
    ) = build_pipeline(executor)

    job = build_job(
        "full-pipeline-duplicate-001"
    )

    first = queue_service.enqueue(
        job,
        match_score=0.90,
    )

    assert first.accepted is True
    assert first.item is not None

    duplicate = queue_service.enqueue(
        job,
        match_score=0.99,
    )

    assert duplicate.accepted is False

    assert duplicate.duplicate is True

    assert duplicate.item is None

    assert queue_service.size == 1

    result = coordinator.run(
        first.item
    )

    assert (
        result.execution_result.status
        == ApplicationExecutionStatus.SUBMITTED
    )

    assert len(executor.requests) == 1

    assert len(
        history_repository.get_by_application_id(
            first.item.application_id
        )
    ) == 1

    print(
        "DUPLICATE protection pipeline test passed"
    )

    print(
        "Original application : "
        f"{first.item.application_id}"
    )

    print(
        "Duplicate rejected    : "
        f"{duplicate.duplicate}"
    )

    print(
        "Executor calls        : "
        f"{len(executor.requests)}"
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    """
    Run all full-pipeline integration tests.
    """

    print()
    print("=" * 70)
    print(
        "FULL APPLICATION PIPELINE INTEGRATION TEST"
    )
    print("=" * 70)

    print()

    test_complete_success_pipeline()

    print()

    test_complete_captcha_pipeline()

    print()

    test_multi_job_queue_pipeline()

    print()

    test_duplicate_job_never_reaches_executor()

    print()

    print("=" * 70)
    print(
        "ALL FULL APPLICATION PIPELINE TESTS PASSED"
    )
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()