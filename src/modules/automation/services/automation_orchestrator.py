"""
Automation workflow orchestrator.

This module connects scheduled/external triggers with AutomationService.

Responsibilities:

- Start an automation run.
- Execute the registered workflow.
- Track successful and failed execution.
- Complete or fail the automation run.
- Keep business workflows independent from APScheduler.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from src.modules.automation.services.automation_service import (
    AutomationService,
)
from src.shared.logging.logger import get_logger


logger = get_logger(__name__)


WorkflowFunction = Callable[
    [UUID | None, dict[str, Any]],
    dict[str, Any] | None,
]


@dataclass(frozen=True)
class AutomationWorkflow:
    """
    Definition of one executable automation workflow.
    """

    run_type: str
    handler: WorkflowFunction


class AutomationOrchestrator:
    """
    Coordinates automation lifecycle and workflow execution.

    The orchestrator does not know about APScheduler.

    APScheduler calls this orchestrator, and the orchestrator
    delegates persistence/lifecycle management to AutomationService.
    """

    def __init__(
        self,
        automation_service: AutomationService,
    ) -> None:
        self.automation_service = automation_service
        self._workflows: dict[str, AutomationWorkflow] = {}

    # ------------------------------------------------------------------
    # Workflow registration
    # ------------------------------------------------------------------

    def register_workflow(
        self,
        *,
        run_type: str,
        handler: WorkflowFunction,
    ) -> None:
        """
        Register a workflow handler.

        Existing handlers with the same run_type are replaced.
        """

        normalized_run_type = run_type.strip()

        if not normalized_run_type:
            raise ValueError(
                "run_type cannot be empty."
            )

        if not callable(handler):
            raise TypeError(
                "handler must be callable."
            )

        self._workflows[
            normalized_run_type
        ] = AutomationWorkflow(
            run_type=normalized_run_type,
            handler=handler,
        )

        logger.info(
            "Automation workflow '{}' registered.",
            normalized_run_type,
        )

    def unregister_workflow(
        self,
        run_type: str,
    ) -> None:
        """
        Remove a registered workflow.

        Raises KeyError if the workflow does not exist.
        """

        normalized_run_type = run_type.strip()

        if normalized_run_type not in self._workflows:
            raise KeyError(
                f"Automation workflow '{normalized_run_type}' "
                "is not registered."
            )

        del self._workflows[
            normalized_run_type
        ]

        logger.info(
            "Automation workflow '{}' unregistered.",
            normalized_run_type,
        )

    def has_workflow(
        self,
        run_type: str,
    ) -> bool:
        """
        Return True when a workflow is registered.
        """

        return run_type.strip() in self._workflows

    def get_workflow(
        self,
        run_type: str,
    ) -> AutomationWorkflow:
        """
        Return a registered workflow definition.

        This allows infrastructure adapters such as the scheduler
        to reuse the workflow handler while creating an isolated
        execution context.
        """

        normalized_run_type = run_type.strip()

        if not normalized_run_type:
            raise ValueError(
                "run_type cannot be empty."
            )

        workflow = self._workflows.get(
            normalized_run_type
        )

        if workflow is None:
            raise ValueError(
                f"Automation workflow '{normalized_run_type}' "
                "is not registered."
            )

        return workflow

    def list_workflows(
        self,
    ) -> list[str]:
        """
        Return registered workflow names.
        """

        return sorted(
            self._workflows.keys()
        )

    # ------------------------------------------------------------------
    # Workflow execution
    # ------------------------------------------------------------------

    def execute(
        self,
        *,
        run_type: str,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Start and execute a registered automation workflow.

        The workflow receives:

            user_id
            metadata

        The workflow may return:

            {
                "items_processed": 10,
                "items_succeeded": 8,
                "items_failed": 2,
                "metadata": {...},
            }

        If the workflow raises an exception, the automation run is
        marked as failed and the exception is re-raised.
        """

        normalized_run_type = run_type.strip()

        if not normalized_run_type:
            raise ValueError(
                "run_type cannot be empty."
            )

        workflow = self._workflows.get(
            normalized_run_type
        )

        if workflow is None:
            raise ValueError(
                f"Automation workflow '{normalized_run_type}' "
                "is not registered."
            )

        run_metadata = dict(
            metadata or {}
        )

        logger.info(
            "Starting automation workflow '{}'.",
            normalized_run_type,
        )

        run = self.automation_service.start_run(
            run_type=normalized_run_type,
            user_id=user_id,
            metadata=run_metadata,
        )

        try:
            result = workflow.handler(
                user_id,
                run_metadata,
            )

            result = result or {}

            items_processed = int(
                result.get(
                    "items_processed",
                    0,
                )
            )

            items_succeeded = int(
                result.get(
                    "items_succeeded",
                    0,
                )
            )

            items_failed = int(
                result.get(
                    "items_failed",
                    0,
                )
            )

            workflow_metadata = result.get(
                "metadata",
                {},
            )

            if not isinstance(
                workflow_metadata,
                dict,
            ):
                raise ValueError(
                    "Workflow result 'metadata' "
                    "must be a dictionary."
                )

            completed_run = (
                self.automation_service.complete_run(
                    run.id,
                    items_processed=items_processed,
                    items_succeeded=items_succeeded,
                    items_failed=items_failed,
                    metadata=workflow_metadata,
                )
            )

            logger.info(
                "Automation workflow '{}' "
                "completed successfully.",
                normalized_run_type,
            )

            return completed_run

        except Exception as exc:
            logger.exception(
                "Automation workflow '{}' failed.",
                normalized_run_type,
            )

            self.automation_service.fail_run(
                run.id,
                error_message=(
                    str(exc)
                    or type(exc).__name__
                ),
                error_code=type(exc).__name__,
            )

            raise