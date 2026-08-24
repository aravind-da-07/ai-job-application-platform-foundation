"""
Repository contract for persistent job applications.

The domain/application layers depend on this abstraction rather than
directly depending on SQLAlchemy or PostgreSQL.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.job_discovery.domain.application_queue import (
    ApplicationQueueItem,
)


class ApplicationRepository(ABC):
    """
    Persistence contract for application lifecycle management.

    Implementations belong to the infrastructure layer.
    """

    @abstractmethod
    def create(
        self,
        item: ApplicationQueueItem,
        *,
        user_id: UUID,
        job_id: UUID,
        resume_id: UUID | None = None,
        resume_version_id: UUID | None = None,
        queued_at=None,
    ) -> ApplicationQueueItem:
        """Persist a new application queue item."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(
        self,
        application_id: str,
    ) -> ApplicationQueueItem | None:
        """Return an application by its application ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_job(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        resume_id: UUID | None = None,
    ) -> ApplicationQueueItem | None:
        """Return an existing application for a user/job/resume."""
        raise NotImplementedError

    @abstractmethod
    def list_queued(
        self,
        *,
        user_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ApplicationQueueItem]:
        """Return queued applications in execution order."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        item: ApplicationQueueItem,
    ) -> ApplicationQueueItem:
        """Persist application state changes."""
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        application_id: str,
    ) -> None:
        """Delete an application record."""
        raise NotImplementedError