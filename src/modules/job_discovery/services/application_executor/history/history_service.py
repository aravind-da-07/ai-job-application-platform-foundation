"""
Application execution history service.

This service provides the application-level API for recording and
retrieving execution history.

It intentionally depends only on the repository contract and domain
history model. It contains no LinkedIn, Playwright, or database-specific
logic.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor.history import (
    ApplicationExecutionHistory,
)
from src.modules.job_discovery.services.application_executor.history.repository import (
    ApplicationExecutionHistoryRepository,
)


class ApplicationExecutionHistoryService:
    """
    Application-level service for execution history.

    The service keeps persistence concerns behind the repository
    contract so that callers do not need to know which storage
    implementation is being used.
    """

    def __init__(
        self,
        repository: ApplicationExecutionHistoryRepository,
    ) -> None:
        self._repository = repository

    @property
    def configured(self) -> bool:
        """
        Return whether a repository is configured.
        """

        return self._repository is not None

    def record(
        self,
        history: ApplicationExecutionHistory,
    ) -> ApplicationExecutionHistory:
        """
        Record one application execution history entry.
        """

        if history is None:
            raise ValueError(
                "history cannot be None."
            )

        return self._repository.save(history)

    def get_history(
        self,
        application_id: str,
    ) -> tuple[ApplicationExecutionHistory, ...]:
        """
        Return all execution history records for an application.
        """

        if not application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        return self._repository.get_by_application_id(
            application_id
        )

    def get_latest(
        self,
        application_id: str,
    ) -> ApplicationExecutionHistory | None:
        """
        Return the latest execution history record.

        Returns None when the application has no history.
        """

        if not application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        return self._repository.get_latest(
            application_id
        )