"""
Integration test for AutomationScheduler.

This test verifies:

1. Workflow registration.
2. Scheduler creation.
3. Interval job registration.
4. Scheduler startup.
5. APScheduler triggering the workflow.
6. Automation run creation.
7. Automation run completion.
8. Multiple scheduled executions.
9. Scheduler job listing and persistent lifecycle logs.
10. Scheduler shutdown and database cleanup.

IMPORTANT:

The test user is committed BEFORE APScheduler starts.

The scheduler executes workflows in background threads using
fresh SQLAlchemy sessions. Therefore, the user referenced by
automation runs must already exist in a committed transaction.

The test also uses separate database sessions for:

- test-user creation
- scheduler execution
- verification
- cleanup

This prevents SQLAlchemy session/thread conflicts and transaction
visibility problems.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from src.modules.automation.domain.entities.automation import (
    AutomationRunStatus,
)
from src.modules.automation.infrastructure.repositories.automation_repository_impl import (
    SQLAlchemyAutomationRepository,
)
from src.modules.automation.services.automation_orchestrator import (
    AutomationOrchestrator,
)
from src.modules.automation.services.automation_scheduler import (
    AutomationScheduler,
)
from src.modules.automation.services.automation_service import (
    AutomationService,
)
from src.modules.users.domain.entities.user import User
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.shared.database.session import session_scope


JOB_ID = "scheduler-integration-test"
RUN_TYPE = "scheduler_test"


def create_committed_test_user():
    """
    Create the test user in its own transaction.

    The transaction is committed before returning.

    This is critical because APScheduler runs the workflow in
    another thread using another SQLAlchemy session.
    """

    test_email = (
        f"scheduler-test-{uuid.uuid4().hex[:12]}"
        "@example.com"
    )

    with session_scope() as session:
        user_repository = SQLAlchemyUserRepository(
            session
        )

        user = User(
            full_name="Automation Scheduler Test User",
            email=test_email,
        )

        created_user = user_repository.create(user)

        # Explicitly commit before the scheduler starts.
        #
        # session_scope() may commit on successful exit, but we need
        # the user committed before this function returns so the
        # scheduler's independent session can see it.
        session.commit()

        print("CREATE USER successful")
        print(f"User ID: {created_user.id}")
        print(f"Email: {created_user.email}")

        return created_user.id


def cleanup_test_data(
    user_id,
) -> None:
    """
    Delete all automation test runs and the test user.

    Cleanup uses a completely fresh database session.
    """

    with session_scope() as session:
        automation_repository = (
            SQLAlchemyAutomationRepository(
                session
            )
        )

        user_repository = (
            SQLAlchemyUserRepository(
                session
            )
        )

        # Find all test automation runs belonging to the test user.
        runs = automation_repository.list_runs(
            user_id=user_id,
            run_type=RUN_TYPE,
            limit=100,
            offset=0,
        )

        print(
            f"Cleanup found {len(runs)} automation run(s)."
        )

        # Delete runs first.
        #
        # Automation logs are configured with CASCADE, so deleting
        # the run also removes its associated logs.
        for run in runs:
            automation_repository.delete_run(
                run.id
            )

        # Delete the test user after its automation runs have
        # been removed.
        user_repository.delete(
            user_id
        )

        session.commit()

        print(
            "DATABASE CLEANUP successful"
        )


def main() -> None:
    print("=" * 70)
    print("AUTOMATION SCHEDULER INTEGRATION TEST")
    print("=" * 70)

    scheduler: AutomationScheduler | None = None
    test_user_id = None

    execution_counter = {
        "count": 0,
    }

    try:
        # --------------------------------------------------------------
        # 1. Create test user
        # --------------------------------------------------------------

        print(
            "\n[1/10] Creating test user..."
        )

        test_user_id = create_committed_test_user()

        # --------------------------------------------------------------
        # 2. Register scheduled workflow
        # --------------------------------------------------------------

        print(
            "\n[2/10] Registering scheduled workflow..."
        )

        def scheduled_workflow(
            user_id,
            metadata: dict[str, Any],
        ) -> dict[str, Any]:
            """
            Small deterministic workflow used by the integration test.
            """

            execution_counter["count"] += 1

            execution_number = (
                execution_counter["count"]
            )

            print(
                f"  Workflow execution "
                f"#{execution_number}"
            )

            print(
                f"  Workflow user_id: "
                f"{user_id}"
            )

            return {
                "items_processed": 3,
                "items_succeeded": 3,
                "items_failed": 0,
                "metadata": {
                    "execution_number": (
                        execution_number
                    ),
                    "trigger": "apscheduler",
                    "test": True,
                },
            }

        # The orchestrator used here is only responsible for holding
        # workflow definitions.
        #
        # The AutomationScheduler creates a fresh persistence layer
        # for each background execution.
        with session_scope() as session:
            automation_repository = (
                SQLAlchemyAutomationRepository(
                    session
                )
            )

            automation_service = AutomationService(
                automation_repository
            )

            orchestrator = AutomationOrchestrator(
                automation_service
            )

            orchestrator.register_workflow(
                run_type=RUN_TYPE,
                handler=scheduled_workflow,
            )

            assert orchestrator.has_workflow(
                RUN_TYPE
            )

            print(
                "WORKFLOW REGISTRATION successful"
            )

        # --------------------------------------------------------------
        # 3. Create AutomationScheduler
        # --------------------------------------------------------------

        print(
            "\n[3/10] Creating automation scheduler..."
        )

        scheduler = AutomationScheduler(
            orchestrator
        )

        assert scheduler.running is False

        print(
            "SCHEDULER CREATION successful"
        )

        print(
            f"Scheduler running: "
            f"{scheduler.running}"
        )

        # --------------------------------------------------------------
        # 4. Register interval job
        # --------------------------------------------------------------

        print(
            "\n[4/10] Registering interval job..."
        )

        scheduler.add_interval_workflow(
            job_id=JOB_ID,
            run_type=RUN_TYPE,
            seconds=1,
            user_id=test_user_id,
            metadata={
                "test": True,
                "source": "integration_test",
            },
        )

        jobs = scheduler.list_jobs()

        assert len(jobs) == 1, (
            f"Expected 1 scheduler job, "
            f"found {len(jobs)}."
        )

        assert (
            jobs[0]["id"] == JOB_ID
        ), (
            f"Expected job ID '{JOB_ID}', "
            f"found '{jobs[0]['id']}'."
        )

        print(
            "INTERVAL JOB REGISTRATION successful"
        )

        print(
            f"Registered jobs: {len(jobs)}"
        )

        for job in jobs:
            print(
                f"- {job['id']}: "
                f"next_run={job['next_run_time']}"
            )

        # --------------------------------------------------------------
        # 5. Start scheduler
        # --------------------------------------------------------------

        print(
            "\n[5/10] Starting scheduler..."
        )

        scheduler.start()

        assert scheduler.running is True

        print(
            "SCHEDULER START successful"
        )

        print(
            f"Scheduler running: "
            f"{scheduler.running}"
        )

        # --------------------------------------------------------------
        # 6. Wait for first scheduled execution
        # --------------------------------------------------------------

        print(
            "\n[6/10] Waiting for scheduled execution..."
        )

        first_deadline = (
            time.time() + 8
        )

        while (
            execution_counter["count"] < 1
            and time.time() < first_deadline
        ):
            time.sleep(0.25)

        assert (
            execution_counter["count"] >= 1
        ), (
            "Scheduled workflow did not execute "
            "within 8 seconds."
        )

        print(
            "FIRST SCHEDULED EXECUTION successful"
        )

        print(
            f"Executions: "
            f"{execution_counter['count']}"
        )

        # --------------------------------------------------------------
        # 7. Verify repeated execution
        # --------------------------------------------------------------

        print(
            "\n[7/10] Verifying repeated execution..."
        )

        second_deadline = (
            time.time() + 8
        )

        while (
            execution_counter["count"] < 2
            and time.time() < second_deadline
        ):
            time.sleep(0.25)

        assert (
            execution_counter["count"] >= 2
        ), (
            "Scheduled workflow did not execute "
            "twice within the expected time."
        )

        print(
            "REPEATED EXECUTION successful"
        )

        print(
            f"Executions: "
            f"{execution_counter['count']}"
        )

        # --------------------------------------------------------------
        # 8. Verify persisted automation runs
        # --------------------------------------------------------------

        print(
            "\n[8/10] Verifying persisted automation runs..."
        )

        # Use a completely fresh session.
        with session_scope() as verification_session:
            verification_repository = (
                SQLAlchemyAutomationRepository(
                    verification_session
                )
            )

            runs = verification_repository.list_runs(
                user_id=test_user_id,
                run_type=RUN_TYPE,
                limit=20,
                offset=0,
            )

            assert len(runs) >= 2, (
                "Expected at least 2 persisted "
                f"automation runs, found {len(runs)}."
            )

            for run in runs:
                assert (
                    run.status
                    == AutomationRunStatus.COMPLETED
                ), (
                    f"Run {run.id} has unexpected "
                    f"status: {run.status}"
                )

                assert (
                    run.items_processed == 3
                ), (
                    f"Run {run.id}: expected "
                    "items_processed=3, got "
                    f"{run.items_processed}"
                )

                assert (
                    run.items_succeeded == 3
                ), (
                    f"Run {run.id}: expected "
                    "items_succeeded=3, got "
                    f"{run.items_succeeded}"
                )

                assert (
                    run.items_failed == 0
                ), (
                    f"Run {run.id}: expected "
                    "items_failed=0, got "
                    f"{run.items_failed}"
                )

            print(
                "PERSISTED RUNS successful"
            )

            print(
                f"Scheduled runs persisted: "
                f"{len(runs)}"
            )

            for run in runs:
                print(
                    f"- {run.id}: "
                    f"status={run.status.value}, "
                    f"processed={run.items_processed}, "
                    f"succeeded={run.items_succeeded}, "
                    f"failed={run.items_failed}"
                )

        # --------------------------------------------------------------
        # 9. Verify logs and scheduler state
        # --------------------------------------------------------------

        print(
            "\n[9/10] Verifying logs and scheduler state..."
        )

        with session_scope() as verification_session:
            verification_repository = (
                SQLAlchemyAutomationRepository(
                    verification_session
                )
            )

            verification_service = AutomationService(
                verification_repository
            )

            runs = verification_repository.list_runs(
                user_id=test_user_id,
                run_type=RUN_TYPE,
                limit=20,
                offset=0,
            )

            total_logs = 0

            for run in runs:
                logs = verification_service.list_logs(
                    run.id
                )

                assert len(logs) >= 2, (
                    f"Expected at least 2 lifecycle "
                    f"logs for run {run.id}, "
                    f"found {len(logs)}."
                )

                event_types = [
                    log.event_type
                    for log in logs
                ]

                assert (
                    "run_started"
                    in event_types
                ), (
                    f"run_started log missing "
                    f"for run {run.id}"
                )

                assert (
                    "run_completed"
                    in event_types
                ), (
                    f"run_completed log missing "
                    f"for run {run.id}"
                )

                total_logs += len(logs)

                print(
                    f"- Run {run.id}: "
                    f"{len(logs)} logs"
                )

            current_jobs = (
                scheduler.list_jobs()
            )

            assert len(current_jobs) == 1, (
                "Expected exactly one active "
                f"scheduler job, found "
                f"{len(current_jobs)}."
            )

            assert (
                current_jobs[0]["id"]
                == JOB_ID
            ), (
                f"Expected active job "
                f"'{JOB_ID}'."
            )

            print(
                "PERSISTENT LOGGING successful"
            )

            print(
                f"Total lifecycle logs: "
                f"{total_logs}"
            )

            print(
                "SCHEDULER STATE successful"
            )

            print(
                f"Active scheduler jobs: "
                f"{len(current_jobs)}"
            )

        # --------------------------------------------------------------
        # 10. Remove job, shutdown scheduler, cleanup database
        # --------------------------------------------------------------

        print(
            "\n[10/10] Shutting down and cleaning up..."
        )

        # Stop future executions first.
        scheduler.remove_job(
            JOB_ID
        )

        remaining_jobs = (
            scheduler.list_jobs()
        )

        assert remaining_jobs == [], (
            "Scheduler job still exists "
            "after removal."
        )

        print(
            "JOB REMOVAL successful"
        )

        # Now stop the scheduler completely.
        scheduler.shutdown(
            wait=True
        )

        assert scheduler.running is False

        print(
            "SCHEDULER SHUTDOWN successful"
        )

        # Only clean database records AFTER the scheduler is stopped.
        cleanup_test_data(
            test_user_id
        )

        print(
            "CLEANUP successful"
        )

        print("\n" + "=" * 70)
        print(
            "AUTOMATION SCHEDULER INTEGRATION TEST PASSED"
        )
        print("=" * 70)

    except Exception:
        print(
            "\nTEST FAILED - performing emergency cleanup..."
        )

        # First stop the scheduler so it cannot create another
        # automation run while cleanup is happening.
        if scheduler is not None:
            try:
                if scheduler.running:
                    scheduler.shutdown(
                        wait=True
                    )
                    print(
                        "Emergency scheduler shutdown successful"
                    )
            except Exception as shutdown_error:
                print(
                    "Emergency scheduler shutdown "
                    f"failed: {shutdown_error}"
                )

        # Then remove the scheduled job if possible.
        if scheduler is not None:
            try:
                scheduler.remove_job(
                    JOB_ID
                )
            except Exception:
                pass

        # Finally clean database records.
        if test_user_id is not None:
            try:
                cleanup_test_data(
                    test_user_id
                )
            except Exception as cleanup_error:
                print(
                    "Emergency database cleanup "
                    f"failed: {cleanup_error}"
                )

        raise


if __name__ == "__main__":
    main()