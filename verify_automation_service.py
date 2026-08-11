"""
Integration test for AutomationService.

This test verifies the complete automation lifecycle against the
real PostgreSQL/Supabase database:

1. Create test user.
2. Start automation run.
3. Verify IN_PROGRESS state.
4. Create persistent audit log.
5. Record successful items.
6. Record failed items.
7. Verify counters.
8. Complete the run.
9. Verify final logs and lifecycle.
10. Clean up test data.
"""

from __future__ import annotations

import uuid

from src.modules.automation.domain.entities.automation import (
    AutomationLogLevel,
    AutomationRunStatus,
)
from src.modules.automation.infrastructure.repositories.automation_repository_impl import (
    SQLAlchemyAutomationRepository,
)
from src.modules.automation.services.automation_service import (
    AutomationService,
)
from src.modules.users.domain.entities.user import User
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.shared.database.session import session_scope


def main() -> None:
    print("=" * 70)
    print("AUTOMATION SERVICE INTEGRATION TEST")
    print("=" * 70)

    with session_scope() as session:
        user_repository = SQLAlchemyUserRepository(session)
        automation_repository = SQLAlchemyAutomationRepository(session)
        automation_service = AutomationService(
            automation_repository
        )

        # --------------------------------------------------------------
        # 1. Create test user
        # --------------------------------------------------------------

        print("\n[1/10] Creating test user...")

        test_email = (
            f"automation-service-test-{uuid.uuid4().hex[:12]}"
            "@example.com"
        )

        user = User(
            full_name="Automation Service Test User",
            email=test_email,
        )

        created_user = user_repository.create(user)

        print("CREATE USER successful")
        print(f"User ID: {created_user.id}")

        # --------------------------------------------------------------
        # 2. Start automation run
        # --------------------------------------------------------------

        print("\n[2/10] Starting automation run...")

        started_run = automation_service.start_run(
            run_type="job_discovery",
            user_id=created_user.id,
            metadata={
                "test": True,
                "sources": [
                    "linkedin",
                    "indeed",
                    "naukri",
                ],
            },
        )

        assert started_run.id is not None
        assert started_run.user_id == created_user.id
        assert started_run.run_type == "job_discovery"
        assert started_run.status == AutomationRunStatus.IN_PROGRESS
        assert started_run.started_at is not None

        print("START RUN successful")
        print(f"Run ID: {started_run.id}")
        print(f"Status: {started_run.status.value}")
        print(f"Started at: {started_run.started_at}")

        # --------------------------------------------------------------
        # 3. Verify run retrieval
        # --------------------------------------------------------------

        print("\n[3/10] Verifying active automation run...")

        fetched_run = automation_service.get_run(
            started_run.id
        )

        assert fetched_run is not None
        assert fetched_run.id == started_run.id
        assert fetched_run.status == AutomationRunStatus.IN_PROGRESS

        print("GET RUN successful")
        print(f"Current status: {fetched_run.status.value}")

        # --------------------------------------------------------------
        # 4. Verify automatic RUN_STARTED log
        # --------------------------------------------------------------

        print("\n[4/10] Verifying automatic start log...")

        logs = automation_service.list_logs(
            started_run.id
        )

        assert len(logs) == 1
        assert logs[0].event_type == "run_started"
        assert logs[0].level == AutomationLogLevel.INFO

        print("START LOG successful")
        print(f"Event: {logs[0].event_type}")
        print(f"Message: {logs[0].message}")

        # --------------------------------------------------------------
        # 5. Record successful items
        # --------------------------------------------------------------

        print("\n[5/10] Recording successful items...")

        after_success = automation_service.record_success(
            started_run.id,
            count=5,
        )

        assert after_success.items_processed == 5
        assert after_success.items_succeeded == 5
        assert after_success.items_failed == 0

        print("SUCCESS COUNTER successful")
        print(f"Items processed: {after_success.items_processed}")
        print(f"Items succeeded: {after_success.items_succeeded}")
        print(f"Items failed: {after_success.items_failed}")

        # --------------------------------------------------------------
        # 6. Record failed items
        # --------------------------------------------------------------

        print("\n[6/10] Recording failed items...")

        after_failure = automation_service.record_failure(
            started_run.id,
            count=2,
            error_message="Two test jobs failed processing.",
            error_code="TEST_PROCESSING_ERROR",
        )

        assert after_failure.items_processed == 7
        assert after_failure.items_succeeded == 5
        assert after_failure.items_failed == 2

        print("FAILURE COUNTER successful")
        print(f"Items processed: {after_failure.items_processed}")
        print(f"Items succeeded: {after_failure.items_succeeded}")
        print(f"Items failed: {after_failure.items_failed}")

        # --------------------------------------------------------------
        # 7. Verify persistent logs
        # --------------------------------------------------------------

        print("\n[7/10] Verifying persistent automation logs...")

        logs = automation_service.list_logs(
            started_run.id
        )

        assert len(logs) == 2

        event_types = [
            log.event_type
            for log in logs
        ]

        assert "run_started" in event_types
        assert "item_failed" in event_types

        log_count = automation_service.count_logs(
            started_run.id
        )

        assert log_count == 2

        print("PERSISTENT LOGGING successful")
        print(f"Total logs: {log_count}")

        for log in logs:
            print(
                f"- {log.event_type}: "
                f"{log.level.value} - "
                f"{log.message}"
            )

        # --------------------------------------------------------------
        # 8. Complete automation run
        # --------------------------------------------------------------

        print("\n[8/10] Completing automation run...")

        completed_run = automation_service.complete_run(
            started_run.id,
            metadata={
                "completion_test": True,
            },
        )

        assert completed_run.status == AutomationRunStatus.COMPLETED
        assert completed_run.completed_at is not None
        assert completed_run.items_processed == 7
        assert completed_run.items_succeeded == 5
        assert completed_run.items_failed == 2

        print("COMPLETE RUN successful")
        print(f"Status: {completed_run.status.value}")
        print(f"Completed at: {completed_run.completed_at}")
        print(f"Processed: {completed_run.items_processed}")
        print(f"Succeeded: {completed_run.items_succeeded}")
        print(f"Failed: {completed_run.items_failed}")

        # --------------------------------------------------------------
        # 9. Verify final lifecycle and logs
        # --------------------------------------------------------------

        print("\n[9/10] Verifying final automation lifecycle...")

        final_run = automation_service.get_run(
            started_run.id
        )

        assert final_run is not None
        assert final_run.status == AutomationRunStatus.COMPLETED
        assert final_run.completed_at is not None

        final_logs = automation_service.list_logs(
            started_run.id
        )

        assert len(final_logs) == 3

        final_event_types = [
            log.event_type
            for log in final_logs
        ]

        assert "run_started" in final_event_types
        assert "item_failed" in final_event_types
        assert "run_completed" in final_event_types

        print("FINAL LIFECYCLE successful")
        print(f"Final status: {final_run.status.value}")
        print(f"Final log count: {len(final_logs)}")

        for log in final_logs:
            print(
                f"- {log.event_type}: "
                f"{log.level.value}"
            )

        # --------------------------------------------------------------
        # 10. Cleanup
        # --------------------------------------------------------------

        print("\n[10/10] Cleaning up test data...")

        automation_repository.delete_run(
            started_run.id
        )

        cleanup_user = user_repository.get_by_id(
            created_user.id
        )

        if cleanup_user is not None:
            user_repository.delete(
                created_user.id
            )

        session.flush()

        assert automation_service.get_run(
            started_run.id
        ) is None

        print("AUTOMATION RUN CLEANUP successful")
        print("TEST USER CLEANUP successful")

    print("\n" + "=" * 70)
    print("AUTOMATION SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()