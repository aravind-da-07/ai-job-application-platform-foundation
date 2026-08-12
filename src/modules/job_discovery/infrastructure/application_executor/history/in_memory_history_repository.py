"""
In-memory application execution history repository.

This implementation is intended for development, integration testing,
and local execution.

It does not provide durable persistence across process restarts.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor.history import (
    ApplicationExecutionHistory,
)
from src.modules.job_discovery.services.application_executor.history import (
    ApplicationExecutionHistoryRepository,
)


class InMemoryApplicationExecutionHistoryRepository(
    ApplicationExecutionHistoryRepository,
):
    """
    In-memory implementation of the execution history repository.
    """

    def __init__(self) -> None:
        self._records: list[
            ApplicationExecutionHistory
        ] = []

    def save(
        self,
        history: ApplicationExecutionHistory,
    ) -> ApplicationExecutionHistory:
        """
        Store one execution history record.
        """

        self._records.append(history)

        return history

    def get_by_application_id(
        self,
        application_id: str,
    ) -> tuple[ApplicationExecutionHistory, ...]:
        """
        Return all records belonging to an application.
        """

        if not application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        return tuple(
            record
            for record in self._records
            if record.application_id == application_id
        )

    def get_latest(
        self,
        application_id: str,
    ) -> ApplicationExecutionHistory | None:
        """
        Return the latest saved record for an application.
        """

        records = self.get_by_application_id(
            application_id
        )

        if not records:
            return None

        return records[-1]