"""
Abstract repository contract for automation runs and audit logs.

The domain layer defines what automation persistence must support.
The infrastructure layer will provide the SQLAlchemy implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.automation.domain.entities.automation import (
    AutomationLog,
    AutomationRun,
    AutomationRunStatus,
)


class AutomationRepository(ABC):
    """
    Repository contract for automation persistence.

    Implementations must not change the domain contract.
    """

    @abstractmethod
    def create_run(self, run: AutomationRun) -> AutomationRun:
        """Create and persist a new automation run."""
        raise NotImplementedError

    @abstractmethod
    def get_run_by_id(self, run_id: UUID) -> AutomationRun | None:
        """Retrieve an automation run by its identifier."""
        raise NotImplementedError

    @abstractmethod
    def update_run(self, run: AutomationRun) -> AutomationRun:
        """Persist changes to an existing automation run."""
        raise NotImplementedError

    @abstractmethod
    def update_run_status(
        self,
        run_id: UUID,
        status: AutomationRunStatus,
    ) -> AutomationRun:
        """Update the lifecycle status of an automation run."""
        raise NotImplementedError

    @abstractmethod
    def create_log(self, log: AutomationLog) -> AutomationLog:
        """Create and persist an automation audit log."""
        raise NotImplementedError

    @abstractmethod
    def get_log_by_id(self, log_id: UUID) -> AutomationLog | None:
        """Retrieve an automation log by its identifier."""
        raise NotImplementedError

    @abstractmethod
    def list_logs(
        self,
        run_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AutomationLog]:
        """Return audit logs belonging to an automation run."""
        raise NotImplementedError

    @abstractmethod
    def list_runs(
        self,
        *,
        user_id: UUID | None = None,
        status: AutomationRunStatus | None = None,
        run_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AutomationRun]:
        """List automation runs using optional filters."""
        raise NotImplementedError

    @abstractmethod
    def count_logs(self, run_id: UUID) -> int:
        """Return the number of logs associated with an automation run."""
        raise NotImplementedError

    @abstractmethod
    def delete_run(self, run_id: UUID) -> None:
        """
        Delete an automation run.

        Database cascade behavior removes its associated audit logs.
        """
        raise NotImplementedError