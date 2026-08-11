"""
Integration test for the AutomationRepository.

This test uses the real PostgreSQL/Supabase database and verifies:

1. Create a test user.
2. Create an automation run.
3. Read the automation run.
4. Update the run status.
5. Create automation logs.
6. Create multiple audit logs.
7. List logs for the run.
8. List/filter automation runs.
9. Count logs for the run.
10. Delete the run and verify log cascade cleanup.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.modules.automation.domain.entities.automation import (
    AutomationLog,
    AutomationLogLevel,
    AutomationRun,
    AutomationRunStatus,
)
from src.modules.automation.infrastructure.repositories.automation_repository_impl import (
    SQLAlchemyAutomationRepository,
)
from src.modules.users.domain.entities.user import User
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.shared.database.session import session_scope


def main() -> None:
    print("=" * 70)
    print("AUTOMATION REPOSITORY INTEGRATION TEST")
    print("=" * 70)

    test_user_id = None
    test_run_id = None

    with session_scope() as session:
        user_repository = SQLAlchemyUserRepository(session)
        automation_repository = SQLAlchemyAutomationRepository(session)

        # --------------------------------------------------------------
        # 1. Create test user
        # --------------------------------------------------------------

        print("\n[1/10] Creating test user...")

        test_email = (
            f"automation-test-{uuid.uuid4().hex[:12]}"
            "@example.com"
        )

        user = User(
            full_name="Automation Repository Test User",
            email=test_email,
        )

        created_user = user_repository.create(user)
        test_user_id = created_user.id

        print("CREATE USER successful")
        print(f"User ID: {created_user.id}")
        print(f"Email: {created_user.email}")

        # --------------------------------------------------------------
        # 2. Create automation run
        # --------------------------------------------------------------

        print("\n[2/10] Creating automation run...")

        run = AutomationRun(
            user_id=created_user.id,
            run_type="job_discovery",
            status=AutomationRunStatus.QUEUED,
            metadata={
                "source": "integration_test",
                "platforms": [
                    "linkedin",
                    "indeed",
                    "naukri",
                ],
            },
        )

        created_run = automation_repository.create_run(run)
        test_run_id = created_run.id

        assert created_run.id == run.id
        assert created_run.status == AutomationRunStatus.QUEUED
        assert created_run.run_type == "job_discovery"
        assert created_run.metadata == {
            "source": "integration_test",
            "platforms": [
                "linkedin",
                "indeed",
                "naukri",
            ],
        }

        print("CREATE RUN successful")
        print(f"Run ID: {created_run.id}")
        print(f"Run type: {created_run.run_type}")
        print(f"Status: {created_run.status.value}")

        # --------------------------------------------------------------
        # 3. Read automation run
        # --------------------------------------------------------------

        print("\n[3/10] Reading automation run...")

        fetched_run = automation_repository.get_run_by_id(
            created_run.id
        )

        assert fetched_run is not None
        assert fetched_run.id == created_run.id
        assert fetched_run.user_id == created_user.id
        assert fetched_run.run_type == "job_discovery"
        assert fetched_run.metadata["source"] == "integration_test"

        print("READ RUN successful")
        print(f"Run ID: {fetched_run.id}")
        print(f"Status: {fetched_run.status.value}")

        # --------------------------------------------------------------
        # 4. Update run status
        # --------------------------------------------------------------

        print("\n[4/10] Updating automation run status...")

        started_run = automation_repository.update_run_status(
            created_run.id,
            AutomationRunStatus.IN_PROGRESS,
        )

        assert started_run.status == AutomationRunStatus.IN_PROGRESS
        assert started_run.started_at is not None

        print("RUN STATUS UPDATE successful")
        print(f"Status: {started_run.status.value}")
        print(f"Started at: {started_run.started_at}")

        # --------------------------------------------------------------
        # 5. Create first automation log
        # --------------------------------------------------------------

        print("\n[5/10] Creating first automation log...")

        first_log = AutomationLog(
            run_id=created_run.id,
            level=AutomationLogLevel.INFO,
            event_type="run_started",
            entity_type="automation_run",
            entity_id=created_run.id,
            status="in_progress",
            message="Job discovery automation started.",
            metadata={
                "source_count": 3,
            },
            occurred_at=datetime.now(timezone.utc),
        )

        created_first_log = automation_repository.create_log(
            first_log
        )

        assert created_first_log.id == first_log.id
        assert created_first_log.run_id == created_run.id
        assert created_first_log.metadata["source_count"] == 3

        print("CREATE LOG successful")
        print(f"Log ID: {created_first_log.id}")
        print(f"Event: {created_first_log.event_type}")

        # --------------------------------------------------------------
        # 6. Create multiple audit logs
        # --------------------------------------------------------------

        print("\n[6/10] Creating additional automation logs...")

        second_log = AutomationLog(
            run_id=created_run.id,
            level=AutomationLogLevel.INFO,
            event_type="job_discovered",
            entity_type="job",
            status="discovered",
            message="Job discovered from supported source.",
            metadata={
                "source": "linkedin",
                "job_title": "Data Analyst",
            },
            occurred_at=datetime.now(timezone.utc),
        )

        third_log = AutomationLog(
            run_id=created_run.id,
            level=AutomationLogLevel.INFO,
            event_type="job_matched",
            entity_type="job",
            status="matched",
            message="Job matched against active resume.",
            metadata={
                "match_score": 87,
            },
            occurred_at=datetime.now(timezone.utc),
        )

        fourth_log = AutomationLog(
            run_id=created_run.id,
            level=AutomationLogLevel.WARNING,
            event_type="warning",
            entity_type="automation_run",
            entity_id=created_run.id,
            status="warning",
            message="One job source returned a temporary error.",
            error_code="SOURCE_TEMPORARY_ERROR",
            metadata={
                "source": "test_source",
            },
            occurred_at=datetime.now(timezone.utc),
        )

        automation_repository.create_log(second_log)
        automation_repository.create_log(third_log)
        automation_repository.create_log(fourth_log)

        log_count = automation_repository.count_logs(
            created_run.id
        )

        assert log_count == 4

        print("MULTIPLE LOGS successful")
        print(f"Total logs created: {log_count}")

        # --------------------------------------------------------------
        # 7. List logs
        # --------------------------------------------------------------

        print("\n[7/10] Listing automation logs...")

        logs = automation_repository.list_logs(
            created_run.id,
            limit=100,
            offset=0,
        )

        assert len(logs) == 4

        print("LIST LOGS successful")
        print(f"Logs returned: {len(logs)}")

        for log in logs:
            print(
                f"- {log.event_type}: "
                f"level={log.level.value}, "
                f"message={log.message}"
            )

        # --------------------------------------------------------------
        # 8. List/filter automation runs
        # --------------------------------------------------------------

        print("\n[8/10] Listing and filtering automation runs...")

        all_runs = automation_repository.list_runs(
            user_id=created_user.id,
        )

        assert len(all_runs) >= 1
        assert any(
            run.id == created_run.id
            for run in all_runs
        )

        in_progress_runs = automation_repository.list_runs(
            user_id=created_user.id,
            status=AutomationRunStatus.IN_PROGRESS,
        )

        assert any(
            run.id == created_run.id
            for run in in_progress_runs
        )

        job_discovery_runs = automation_repository.list_runs(
            user_id=created_user.id,
            run_type="job_discovery",
        )

        assert any(
            run.id == created_run.id
            for run in job_discovery_runs
        )

        print("LIST/FILTER RUNS successful")
        print(f"Runs for test user: {len(all_runs)}")
        print(
            f"In-progress runs: "
            f"{len(in_progress_runs)}"
        )
        print(
            f"Job-discovery runs: "
            f"{len(job_discovery_runs)}"
        )

        # --------------------------------------------------------------
        # 9. Count logs + complete run
        # --------------------------------------------------------------

        print(
            "\n[9/10] Completing automation run "
            "and verifying counts..."
        )

        current_run = automation_repository.get_run_by_id(
            created_run.id
        )

        assert current_run is not None

        completed_run = current_run.model_copy(
            update={
                "status": AutomationRunStatus.COMPLETED,
                "completed_at": datetime.now(timezone.utc),
                "items_processed": 10,
                "items_succeeded": 8,
                "items_failed": 2,
                "metadata": {
                    **current_run.metadata,
                    "completed_by": "integration_test",
                },
            }
        )

        saved_run = automation_repository.update_run(
            completed_run
        )

        assert saved_run.status == AutomationRunStatus.COMPLETED
        assert saved_run.items_processed == 10
        assert saved_run.items_succeeded == 8
        assert saved_run.items_failed == 2
        assert saved_run.completed_at is not None
        assert saved_run.metadata["completed_by"] == "integration_test"

        final_log_count = automation_repository.count_logs(
            created_run.id
        )

        assert final_log_count == 4

        print("RUN COMPLETION successful")
        print(f"Final status: {saved_run.status.value}")
        print(f"Items processed: {saved_run.items_processed}")
        print(f"Items succeeded: {saved_run.items_succeeded}")
        print(f"Items failed: {saved_run.items_failed}")
        print(f"Total logs: {final_log_count}")

        # --------------------------------------------------------------
        # 10. Delete run + verify cascade
        # --------------------------------------------------------------

        print("\n[10/10] Testing run deletion and log cascade...")

        automation_repository.delete_run(
            created_run.id
        )

        deleted_run = automation_repository.get_run_by_id(
            created_run.id
        )

        assert deleted_run is None

        remaining_logs = automation_repository.list_logs(
            created_run.id,
        )

        assert remaining_logs == []

        remaining_log_count = automation_repository.count_logs(
            created_run.id
        )

        assert remaining_log_count == 0

        print("DELETE RUN successful")
        print("RUN successfully removed")
        print("CASCADE LOG CLEANUP successful")
        print("Remaining logs: 0")

        # --------------------------------------------------------------
        # Cleanup test user
        # --------------------------------------------------------------

        print("\nCleaning up test user...")

        user_for_cleanup = user_repository.get_by_id(
            test_user_id
        )

        if user_for_cleanup is not None:
            user_repository.delete(
                test_user_id
            )

        session.flush()

        print("USER CLEANUP successful")

    print("\n" + "=" * 70)
    print("AUTOMATION REPOSITORY INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()