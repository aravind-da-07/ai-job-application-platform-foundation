"""
Application execution history service integration test.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.modules.job_discovery.domain.application_executor.history import (
    ApplicationExecutionHistory,
    ApplicationExecutionHistoryStatus,
)
from src.modules.job_discovery.infrastructure.application_executor.history import (
    InMemoryApplicationExecutionHistoryRepository,
)
from src.modules.job_discovery.services.application_executor.history import (
    ApplicationExecutionHistoryService,
)
from src.shared.config.constants import JobSourceType


def build_history(
    *,
    application_id: str,
    external_job_id: str,
    status: ApplicationExecutionHistoryStatus,
    confirmation_id: str | None = None,
    manual_intervention_required: bool = False,
    reason: str | None = None,
    error_code: str | None = None,
) -> ApplicationExecutionHistory:

    started = datetime.now().astimezone()
    completed = started + timedelta(seconds=1)

    return ApplicationExecutionHistory(
        application_id=application_id,
        external_job_id=external_job_id,
        source=JobSourceType.LINKEDIN,
        status=status,
        started_at=started,
        completed_at=completed,
        form_type="easy_apply",
        fields_detected=2,
        fields_filled=(
            2
            if status
            == ApplicationExecutionHistoryStatus.SUBMITTED
            else 0
        ),
        confirmation_id=confirmation_id,
        manual_intervention_required=(
            manual_intervention_required
        ),
        reason=reason,
        error_code=error_code,
    )


def test_service_creation() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    service = ApplicationExecutionHistoryService(
        repository
    )

    assert service.configured is True

    print(
        "SERVICE creation successful"
    )


def test_record_submitted_history() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    service = ApplicationExecutionHistoryService(
        repository
    )

    history = build_history(
        application_id="service-app-001",
        external_job_id="service-job-001",
        status=(
            ApplicationExecutionHistoryStatus.SUBMITTED
        ),
        confirmation_id="service-confirmation-001",
    )

    recorded = service.record(history)

    assert recorded == history

    latest = service.get_latest(
        "service-app-001"
    )

    assert latest == history

    assert latest is not None

    assert latest.status == (
        ApplicationExecutionHistoryStatus.SUBMITTED
    )

    print(
        "SUBMITTED history recording successful"
    )


def test_record_manual_review_history() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    service = ApplicationExecutionHistoryService(
        repository
    )

    history = build_history(
        application_id="service-app-002",
        external_job_id="service-job-002",
        status=(
            ApplicationExecutionHistoryStatus
            .MANUAL_REVIEW_REQUIRED
        ),
        manual_intervention_required=True,
        reason="Authentication required.",
        error_code="authentication_required",
    )

    service.record(history)

    latest = service.get_latest(
        "service-app-002"
    )

    assert latest is not None

    assert latest.status == (
        ApplicationExecutionHistoryStatus
        .MANUAL_REVIEW_REQUIRED
    )

    assert latest.manual_intervention_required is True

    assert latest.error_code == (
        "authentication_required"
    )

    print(
        "MANUAL REVIEW history recording successful"
    )


def test_record_failed_history() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    service = ApplicationExecutionHistoryService(
        repository
    )

    history = build_history(
        application_id="service-app-003",
        external_job_id="service-job-003",
        status=(
            ApplicationExecutionHistoryStatus.FAILED
        ),
        reason="Submission failed.",
        error_code="submit_failed",
        manual_intervention_required=True,
    )

    service.record(history)

    latest = service.get_latest(
        "service-app-003"
    )

    assert latest is not None

    assert latest.status == (
        ApplicationExecutionHistoryStatus.FAILED
    )

    assert latest.error_code == (
        "submit_failed"
    )

    print(
        "FAILED history recording successful"
    )


def test_get_history_returns_all_records() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    service = ApplicationExecutionHistoryService(
        repository
    )

    first = build_history(
        application_id="service-app-004",
        external_job_id="service-job-004",
        status=(
            ApplicationExecutionHistoryStatus.FAILED
        ),
        error_code="first_failure",
        manual_intervention_required=True,
    )

    second = build_history(
        application_id="service-app-004",
        external_job_id="service-job-004",
        status=(
            ApplicationExecutionHistoryStatus.SUBMITTED
        ),
        confirmation_id="final-confirmation-004",
    )

    service.record(first)
    service.record(second)

    records = service.get_history(
        "service-app-004"
    )

    assert len(records) == 2

    assert records[0] == first
    assert records[1] == second

    print(
        "FULL history retrieval successful"
    )


def test_application_isolation() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    service = ApplicationExecutionHistoryService(
        repository
    )

    first = build_history(
        application_id="service-app-005",
        external_job_id="service-job-005",
        status=(
            ApplicationExecutionHistoryStatus.SUBMITTED
        ),
        confirmation_id="confirmation-005",
    )

    second = build_history(
        application_id="service-app-006",
        external_job_id="service-job-006",
        status=(
            ApplicationExecutionHistoryStatus.SUBMITTED
        ),
        confirmation_id="confirmation-006",
    )

    service.record(first)
    service.record(second)

    app_005 = service.get_history(
        "service-app-005"
    )

    app_006 = service.get_history(
        "service-app-006"
    )

    assert len(app_005) == 1
    assert len(app_006) == 1

    assert (
        app_005[0].application_id
        == "service-app-005"
    )

    assert (
        app_006[0].application_id
        == "service-app-006"
    )

    print(
        "APPLICATION isolation successful"
    )


def test_empty_application_id_protection() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    service = ApplicationExecutionHistoryService(
        repository
    )

    try:
        service.get_history("")

    except ValueError as exc:
        assert (
            str(exc)
            == "application_id cannot be empty."
        )

    else:
        raise AssertionError(
            "Expected application_id validation error."
        )

    try:
        service.get_latest("")

    except ValueError as exc:
        assert (
            str(exc)
            == "application_id cannot be empty."
        )

    else:
        raise AssertionError(
            "Expected application_id validation error."
        )

    print(
        "EMPTY application ID protection successful"
    )


def test_none_history_protection() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    service = ApplicationExecutionHistoryService(
        repository
    )

    try:
        service.record(None)  # type: ignore[arg-type]

    except ValueError as exc:
        assert (
            str(exc)
            == "history cannot be None."
        )

    else:
        raise AssertionError(
            "Expected None history validation error."
        )

    print(
        "NONE history protection successful"
    )


def main() -> None:
    print("=" * 70)
    print(
        "APPLICATION EXECUTION HISTORY SERVICE "
        "INTEGRATION TEST"
    )
    print("=" * 70)

    print(
        "\n[1/7] Testing service creation..."
    )
    test_service_creation()

    print(
        "\n[2/7] Testing SUBMITTED history..."
    )
    test_record_submitted_history()

    print(
        "\n[3/7] Testing MANUAL REVIEW history..."
    )
    test_record_manual_review_history()

    print(
        "\n[4/7] Testing FAILED history..."
    )
    test_record_failed_history()

    print(
        "\n[5/7] Testing history retrieval..."
    )
    test_get_history_returns_all_records()

    print(
        "\n[6/7] Testing application isolation..."
    )
    test_application_isolation()

    print(
        "\n[7/7] Testing validation protections..."
    )
    test_empty_application_id_protection()
    test_none_history_protection()

    print("\n" + "=" * 70)
    print(
        "APPLICATION EXECUTION HISTORY SERVICE "
        "TEST PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()