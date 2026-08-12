"""
Application execution history repository contract.

This module defines the service-layer contract for storing and
retrieving application execution history.

The contract is intentionally independent of any database or
infrastructure implementation.
"""

from __future__ import annotations

from typing import Protocol

from src.modules.job_discovery.domain.application_executor.history import (
    ApplicationExecutionHistory,
)


class ApplicationExecutionHistoryRepository(Protocol):
    """
    Contract for application execution history persistence.
    """

    def save(
        self,
        history: ApplicationExecutionHistory,
    ) -> ApplicationExecutionHistory:
        """
        Persist one execution history record.

        Implementations should return the persisted record.
        """
        ...

    def get_by_application_id(
        self,
        application_id: str,
    ) -> tuple[ApplicationExecutionHistory, ...]:
        """
        Return all execution history records for an application.
        """
        ...

    def get_latest(
        self,
        application_id: str,
    ) -> ApplicationExecutionHistory | None:
        """
        Return the latest execution history record for an application.

        Return None when no history exists.
        """
        ...