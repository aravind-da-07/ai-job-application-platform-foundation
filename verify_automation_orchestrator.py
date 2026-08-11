"""
Integration test for AutomationOrchestrator.

This test verifies:

1. Workflow registration.
2. Workflow discovery.
3. Automation run creation.
4. Workflow execution.
5. Successful item counters.
6. Metadata persistence.
7. Automatic run completion.
8. Persistent audit logging.
9. Workflow failure handling.
10. Automatic failed-run lifecycle.
"""

from __future__ import annotations

import uuid

from src.modules.automation.domain.entities.automation import (
    AutomationRunStatus,
)
from src.modules.automation.infrastructure.repositories.automation_repository_impl import (
    SQLAlchemyAutomationRepository,
)
from src.modules.automation.services.automation_orchestrator import (
    AutomationOrchestrator,
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
    print("AUTOMATION ORCHESTRATOR INTEGRATION TEST")
    print("=" * 70)

    with session_scope() as session:
        user_repository = SQLAlchemyUserRepository(session)
        automation_repository = SQLAlchemyAutomationRepository(session)

        automation_service = AutomationService(
            automation_repository
        )

        orchestrator = AutomationOrchestrator(
            automation_service
        )

        # --------------------------------------------------------------
        # 1. Create test user
        # --------------------------------------------------------------

        print("\n[1/10] Creating test user...")

        test_email = (
            f"orchestrator-test-{uuid.uuid4().hex[:12]}"
            "@example.com"
        )

        user = User(
            full_name="Automation Orchestrator Test User",
            email=test_email,
        )

        created_user = user_repository.create(
            user
        )

        print("CREATE USER successful")
        print(f"User ID: {created_user.id}")

        # --------------------------------------------------------------
        # 2. Register successful workflow
        # --------------------------------------------------------------

        print("\n[2/10] Registering successful workflow...")

        def successful_workflow(
            user_id,
            metadata,
        ):
            assert user_id == created_user.id
            assert metadata["test"] is True

            return {
                "items_processed": 10,
                "items_succeeded": 8,
                "items_failed": 2,
                "metadata": {
                    "workflow": "test_success",
                    "source": "integration_test",
                },
            }

        orchestrator.register_workflow(
            run_type="test_success",
            handler=successful_workflow,
        )

        assert orchestrator.has_workflow(
            "test_success"
        )

        print("WORKFLOW REGISTRATION successful")

        # --------------------------------------------------------------
        # 3. List workflows
        # --------------------------------------------------------------

        print("\n[3/10] Listing registered workflows...")

        workflows = orchestrator.list_workflows()

        assert "test_success" in workflows

        print("WORKFLOW LIST successful")
        print(f"Registered workflows: {workflows}")

        # --------------------------------------------------------------
        # 4. Execute successful workflow
        # --------------------------------------------------------------

        print("\n[4/10] Executing successful workflow...")

        completed_run = orchestrator.execute(
            run_type="test_success",
            user_id=created_user.id,
            metadata={
                "test": True,
            },
        )

        assert (
            completed_run.status
            == AutomationRunStatus.COMPLETED
        )

        print("WORKFLOW EXECUTION successful")
        print(f"Run ID: {completed_run.id}")
        print(f"Status: {completed_run.status.value}")

        # --------------------------------------------------------------
        # 5. Verify counters
        # --------------------------------------------------------------

        print("\n[5/10] Verifying workflow counters...")

        assert completed_run.items_processed == 10
        assert completed_run.items_succeeded == 8
        assert completed_run.items_failed == 2

        print("COUNTERS successful")
        print(
            f"Processed: {completed_run.items_processed}"
        )
        print(
            f"Succeeded: {completed_run.items_succeeded}"
        )
        print(
            f"Failed: {completed_run.items_failed}"
        )

        # --------------------------------------------------------------
        # 6. Verify metadata
        # --------------------------------------------------------------

        print("\n[6/10] Verifying workflow metadata...")

        assert (
            completed_run.metadata["test"]
            is True
        )

        assert (
            completed_run.metadata["workflow"]
            == "test_success"
        )

        assert (
            completed_run.metadata["source"]
            == "integration_test"
        )

        print("METADATA successful")
        print(completed_run.metadata)

        # --------------------------------------------------------------
        # 7. Verify persistent lifecycle logs
        # --------------------------------------------------------------

        print("\n[7/10] Verifying persistent lifecycle logs...")

        logs = automation_service.list_logs(
            completed_run.id
        )

        event_types = [
            log.event_type
            for log in logs
        ]

        assert "run_started" in event_types
        assert "run_completed" in event_types

        print("LIFECYCLE LOGGING successful")

        for log in logs:
            print(
                f"- {log.event_type}: "
                f"{log.level.value} - "
                f"{log.message}"
            )

        # --------------------------------------------------------------
        # 8. Register failing workflow
        # --------------------------------------------------------------

        print("\n[8/10] Registering failing workflow...")

        def failing_workflow(
            user_id,
            metadata,
        ):
            raise RuntimeError(
                "Intentional orchestrator test failure."
            )

        orchestrator.register_workflow(
            run_type="test_failure",
            handler=failing_workflow,
        )

        print("FAILING WORKFLOW registration successful")

        # --------------------------------------------------------------
        # 9. Execute failing workflow
        # --------------------------------------------------------------

        print("\n[9/10] Testing workflow failure handling...")

        failed_run_id = None

        try:
            orchestrator.execute(
                run_type="test_failure",
                user_id=created_user.id,
                metadata={
                    "test": True,
                },
            )
        except RuntimeError as exc:
            print(
                f"EXPECTED workflow failure: {exc}"
            )

        # Find the latest failure run.
        failure_runs = automation_repository.list_runs(
            user_id=created_user.id,
            run_type="test_failure",
            limit=10,
        )

        assert len(failure_runs) == 1

        failed_run = failure_runs[0]
        failed_run_id = failed_run.id

        assert (
            failed_run.status
            == AutomationRunStatus.FAILED
        )

        assert (
            failed_run.error_message
            == "Intentional orchestrator test failure."
        )

        print("FAILURE HANDLING successful")
        print(
            f"Failed run ID: {failed_run.id}"
        )
        print(
            f"Status: {failed_run.status.value}"
        )

        # --------------------------------------------------------------
        # 10. Cleanup
        # --------------------------------------------------------------

        print("\n[10/10] Cleaning up test data...")

        automation_repository.delete_run(
            completed_run.id
        )

        if failed_run_id is not None:
            automation_repository.delete_run(
                failed_run_id
            )

        user_repository.delete(
            created_user.id
        )

        session.flush()

        print("CLEANUP successful")

    print("\n" + "=" * 70)
    print("AUTOMATION ORCHESTRATOR INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()