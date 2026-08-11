"""
Integration test for AutomationEventLogger.

Verifies that EventBus events associated with an automation run
are persisted into automation_logs.

Also verifies that events without an automation_run_id are ignored.
"""

from __future__ import annotations

import uuid

from src.modules.automation.infrastructure.repositories.automation_repository_impl import (
    SQLAlchemyAutomationRepository,
)
from src.modules.automation.services.automation_event_logger import (
    AutomationEventLogger,
    register_automation_event_logger,
)
from src.modules.automation.services.automation_service import AutomationService
from src.modules.users.domain.entities.user import User
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.shared.config.constants import EventType
from src.shared.database.session import session_scope
from src.shared.events.event_bus import Event, get_event_bus


def main() -> None:
    print("=" * 70)
    print("AUTOMATION EVENT LOGGER INTEGRATION TEST")
    print("=" * 70)

    event_bus = get_event_bus()

    # Prevent subscriptions from previous test runs in this process.
    event_bus.clear()

    with session_scope() as session:
        user_repository = SQLAlchemyUserRepository(session)
        automation_repository = SQLAlchemyAutomationRepository(session)
        automation_service = AutomationService(
            automation_repository
        )

        test_user_id = None
        run_id = None

        try:
            # ----------------------------------------------------------
            # 1. Create test user
            # ----------------------------------------------------------

            print("\n[1/10] Creating test user...")

            test_email = (
                f"event-logger-test-{uuid.uuid4().hex[:12]}"
                "@example.com"
            )

            user = User(
                full_name="Automation Event Logger Test User",
                email=test_email,
            )

            created_user = user_repository.create(user)
            test_user_id = created_user.id

            print("CREATE USER successful")
            print(f"User ID: {created_user.id}")

            # ----------------------------------------------------------
            # 2. Create automation run
            # ----------------------------------------------------------

            print("\n[2/10] Creating automation run...")

            run = automation_service.start_run(
                run_type="job_discovery",
                user_id=created_user.id,
                metadata={
                    "test": True,
                    "source": "event_logger_integration_test",
                },
            )

            run_id = run.id

            print("CREATE RUN successful")
            print(f"Run ID: {run.id}")
            print(f"Status: {run.status.value}")

            # ----------------------------------------------------------
            # 3. Register event logger
            # ----------------------------------------------------------

            print("\n[3/10] Registering automation event logger...")

            event_logger = AutomationEventLogger(
                automation_service
            )

            register_automation_event_logger(
                event_logger
            )

            print("EVENT LOGGER registration successful")

            # ----------------------------------------------------------
            # 4. Publish JOB_DISCOVERED
            # ----------------------------------------------------------

            print("\n[4/10] Publishing JOB_DISCOVERED event...")

            job_id = uuid.uuid4()

            event_bus.publish(
                Event(
                    type=EventType.JOB_DISCOVERED,
                    payload={
                        "automation_run_id": run.id,
                        "entity_type": "job",
                        "entity_id": job_id,
                        "status": "discovered",
                        "source": "linkedin",
                        "message": "Data Analyst job discovered.",
                    },
                )
            )

            print("JOB_DISCOVERED published successfully")

            # ----------------------------------------------------------
            # 5. Publish JOB_MATCHED
            # ----------------------------------------------------------

            print("\n[5/10] Publishing JOB_MATCHED event...")

            event_bus.publish(
                Event(
                    type=EventType.JOB_MATCHED,
                    payload={
                        "automation_run_id": run.id,
                        "entity_type": "job",
                        "entity_id": job_id,
                        "status": "matched",
                        "match_score": 91,
                        "message": "Job matched against active resume.",
                    },
                )
            )

            print("JOB_MATCHED published successfully")

            # ----------------------------------------------------------
            # 6. Publish APPLICATION_SUBMITTED
            # ----------------------------------------------------------

            print(
                "\n[6/10] Publishing APPLICATION_SUBMITTED event..."
            )

            application_id = uuid.uuid4()

            event_bus.publish(
                Event(
                    type=EventType.APPLICATION_SUBMITTED,
                    payload={
                        "automation_run_id": run.id,
                        "entity_type": "application",
                        "entity_id": application_id,
                        "status": "submitted",
                        "source": "linkedin",
                        "message": "Application submitted successfully.",
                    },
                )
            )

            print(
                "APPLICATION_SUBMITTED published successfully"
            )

            # ----------------------------------------------------------
            # 7. Publish APPLICATION_FAILED
            # ----------------------------------------------------------

            print("\n[7/10] Publishing APPLICATION_FAILED event...")

            failed_application_id = uuid.uuid4()

            event_bus.publish(
                Event(
                    type=EventType.APPLICATION_FAILED,
                    payload={
                        "automation_run_id": run.id,
                        "entity_type": "application",
                        "entity_id": failed_application_id,
                        "status": "failed",
                        "error_code": "TEST_APPLICATION_ERROR",
                        "message": "Test application failed.",
                    },
                )
            )

            print(
                "APPLICATION_FAILED published successfully"
            )

            # ----------------------------------------------------------
            # 8. Verify persistent logs
            # ----------------------------------------------------------

            print("\n[8/10] Verifying persistent automation logs...")

            logs = automation_service.list_logs(run.id)

            # start_run creates RUN_STARTED.
            # Four published events create four additional logs.
            assert len(logs) == 5

            event_types = [
                log.event_type
                for log in logs
            ]

            assert "run_started" in event_types
            assert "job_discovered" in event_types
            assert "job_matched" in event_types
            assert "application_submitted" in event_types
            assert "application_failed" in event_types

            print("PERSISTENT EVENT LOGGING successful")
            print(f"Total logs: {len(logs)}")

            for log in logs:
                print(
                    f"- {log.event_type}: "
                    f"level={log.level.value}, "
                    f"entity={log.entity_type}, "
                    f"status={log.status}"
                )

            # ----------------------------------------------------------
            # 9. Verify event metadata and ignored event
            # ----------------------------------------------------------

            print("\n[9/10] Verifying event metadata and filtering...")

            discovered_log = next(
                log
                for log in logs
                if log.event_type == "job_discovered"
            )

            assert discovered_log.entity_type == "job"
            assert discovered_log.entity_id == job_id
            assert discovered_log.status == "discovered"
            assert discovered_log.metadata["source"] == "linkedin"

            failed_log = next(
                log
                for log in logs
                if log.event_type == "application_failed"
            )

            assert failed_log.level.value == "error"
            assert failed_log.error_code == "TEST_APPLICATION_ERROR"
            assert failed_log.entity_type == "application"
            assert failed_log.entity_id == failed_application_id

            before_count = len(logs)

            # This event has no automation_run_id and must not
            # create a persistent automation log.
            event_bus.publish(
                Event(
                    type=EventType.JOB_DISCOVERED,
                    payload={
                        "entity_type": "job",
                        "entity_id": uuid.uuid4(),
                        "message": "This event must not be persisted.",
                    },
                )
            )

            after_logs = automation_service.list_logs(run.id)

            assert len(after_logs) == before_count

            print("EVENT FILTERING successful")
            print(
                "Events without automation_run_id "
                "are correctly ignored."
            )

            print("METADATA verification successful")
            print(
                "JOB_DISCOVERED metadata correctly persisted."
            )
            print(
                "APPLICATION_FAILED error metadata correctly persisted."
            )

        finally:
            # ----------------------------------------------------------
            # 10. Cleanup
            # ----------------------------------------------------------

            print("\n[10/10] Cleaning up test data...")

            if run_id is not None:
                automation_repository.delete_run(run_id)

            if test_user_id is not None:
                remaining_user = user_repository.get_by_id(
                    test_user_id
                )

                if remaining_user is not None:
                    user_repository.delete(
                        test_user_id
                    )

            session.flush()

            if run_id is not None:
                assert automation_service.get_run(run_id) is None

            print("AUTOMATION RUN CLEANUP successful")
            print("TEST USER CLEANUP successful")

    event_bus.clear()

    print("\n" + "=" * 70)
    print("AUTOMATION EVENT LOGGER INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()