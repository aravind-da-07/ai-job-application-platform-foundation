"""
Integration tests for the in-memory application execution history repository.
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
from src.shared.config.constants import JobSourceType


def build_history(
    *,
    application_id: str,
    external_job_id: str,
    status: ApplicationExecutionHistoryStatus,
    started_at: datetime,
    completed_at: datetime,
    confirmation_id: str | None = None,
    manual_intervention_required: bool = False,
    reason: str | None = None,
    error_code: str | None = None,
    fields_detected: int = 2,
    fields_filled: int = 2,
) -> ApplicationExecutionHistory:
    return ApplicationExecutionHistory(
        application_id=application_id,
        external_job_id=external_job_id,
        source=JobSourceType.LINKEDIN,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        form_type="easy_apply",
        fields_detected=fields_detected,
        fields_filled=fields_filled,
        confirmation_id=confirmation_id,
        manual_intervention_required=(
            manual_intervention_required
        ),
        reason=reason,
        error_code=error_code,
    )


def test_save_and_retrieve() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    started = datetime.now()
    completed = started + timedelta(seconds=2)

    history = build_history(
        application_id="app-001",
        external_job_id="job-001",
        status=ApplicationExecutionHistoryStatus.SUBMITTED,
        started_at=started,
        completed_at=completed,
        confirmation_id="confirmation-001",
    )

    saved = repository.save(history)

    assert saved == history

    records = repository.get_by_application_id(
        "app-001"
    )

    assert len(records) == 1
    assert records[0] == history

    print(
        "SAVE + RETRIEVE successful"
    )


def test_latest_record() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    started = datetime.now()

    first = build_history(
        application_id="app-002",
        external_job_id="job-002",
        status=ApplicationExecutionHistoryStatus.FAILED,
        started_at=started,
        completed_at=started + timedelta(seconds=1),
        error_code="submission_failed",
    )

    second = build_history(
        application_id="app-002",
        external_job_id="job-002",
        status=ApplicationExecutionHistoryStatus.SUBMITTED,
        started_at=started + timedelta(seconds=2),
        completed_at=started + timedelta(seconds=4),
        confirmation_id="confirmation-002",
    )

    repository.save(first)
    repository.save(second)

    latest = repository.get_latest(
        "app-002"
    )

    assert latest == second
    assert latest is not None
    assert latest.status == (
        ApplicationExecutionHistoryStatus.SUBMITTED
    )

    print(
        "LATEST record retrieval successful"
    )


def test_multiple_records_same_application() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    started = datetime.now()

    for index in range(3):
        history = build_history(
            application_id="app-003",
            external_job_id="job-003",
            status=(
                ApplicationExecutionHistoryStatus.FAILED
            ),
            started_at=(
                started + timedelta(seconds=index)
            ),
            completed_at=(
                started
                + timedelta(seconds=index + 1)
            ),
            error_code=f"error-{index}",
        )

        repository.save(history)

    records = repository.get_by_application_id(
        "app-003"
    )

    assert len(records) == 3

    assert records[0].error_code == "error-0"
    assert records[1].error_code == "error-1"
    assert records[2].error_code == "error-2"

    print(
        "MULTIPLE records preservation successful"
    )


def test_application_isolation() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    started = datetime.now()

    first = build_history(
        application_id="app-004",
        external_job_id="job-004",
        status=ApplicationExecutionHistoryStatus.SUBMITTED,
        started_at=started,
        completed_at=started + timedelta(seconds=1),
        confirmation_id="confirmation-004",
    )

    second = build_history(
        application_id="app-005",
        external_job_id="job-005",
        status=ApplicationExecutionHistoryStatus.SUBMITTED,
        started_at=started,
        completed_at=started + timedelta(seconds=1),
        confirmation_id="confirmation-005",
    )

    repository.save(first)
    repository.save(second)

    app_004_records = (
        repository.get_by_application_id(
            "app-004"
        )
    )

    app_005_records = (
        repository.get_by_application_id(
            "app-005"
        )
    )

    assert len(app_004_records) == 1
    assert len(app_005_records) == 1

    assert (
        app_004_records[0].application_id
        == "app-004"
    )

    assert (
        app_005_records[0].application_id
        == "app-005"
    )

    print(
        "APPLICATION isolation successful"
    )


def test_empty_application_returns_none() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    latest = repository.get_latest(
        "does-not-exist"
    )

    assert latest is None

    records = repository.get_by_application_id(
        "does-not-exist"
    )

    assert records == ()

    print(
        "EMPTY application lookup successful"
    )


def test_empty_application_id_protection() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    try:
        repository.get_latest("")

    except ValueError as exc:
        assert (
            str(exc)
            == "application_id cannot be empty."
        )

        print(
            "EMPTY application ID protection successful"
        )

        return

    raise AssertionError(
        "Expected empty application_id validation error."
    )


def test_manual_review_history() -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    started = datetime.now()

    history = build_history(
        application_id="app-006",
        external_job_id="job-006",
        status=(
            ApplicationExecutionHistoryStatus
            .MANUAL_REVIEW_REQUIRED
        ),
        started_at=started,
        completed_at=started + timedelta(seconds=1),
        confirmation_id=None,
        manual_intervention_required=True,
        reason=(
            "Candidate answer requires manual review."
        ),
        fields_detected=3,
        fields_filled=0,
    )

    saved = repository.save(history)

    assert saved.status == (
        ApplicationExecutionHistoryStatus
        .MANUAL_REVIEW_REQUIRED
    )

    assert (
        saved.manual_intervention_required
        is True
    )

    assert saved.confirmation_id is None

    print(
        "MANUAL REVIEW history storage successful"
    )


def main() -> None:
    print("=" * 70)
    print(
        "APPLICATION EXECUTION HISTORY REPOSITORY "
        "INTEGRATION TEST"
    )
    print("=" * 70)

    print(
        "\n[1/7] Testing save and retrieve..."
    )
    test_save_and_retrieve()

    print(
        "\n[2/7] Testing latest record..."
    )
    test_latest_record()

    print(
        "\n[3/7] Testing multiple records..."
    )
    test_multiple_records_same_application()

    print(
        "\n[4/7] Testing application isolation..."
    )
    test_application_isolation()

    print(
        "\n[5/7] Testing empty application lookup..."
    )
    test_empty_application_returns_none()

    print(
        "\n[6/7] Testing empty application ID protection..."
    )
    test_empty_application_id_protection()

    print(
        "\n[7/7] Testing manual-review history..."
    )
    test_manual_review_history()

    print("\n" + "=" * 70)
    print(
        "APPLICATION EXECUTION HISTORY REPOSITORY "
        "TEST PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()