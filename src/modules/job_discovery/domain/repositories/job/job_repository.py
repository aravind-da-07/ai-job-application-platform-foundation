"""
Domain repository contract for discovered jobs.

This module defines the persistence operations required by the job
discovery domain.

No SQLAlchemy, PostgreSQL, Supabase, or portal-specific logic belongs here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.shared.config.constants import JobSourceType


class JobRepository(ABC):
    """
    Abstract repository contract for discovered jobs.
    """

    @abstractmethod
    def create(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """Persist a newly discovered job."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(
        self,
        job_id: UUID,
    ) -> DiscoveredJob | None:
        """Retrieve a job by internal UUID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_external_id(
        self,
        *,
        source: JobSourceType,
        external_job_id: str,
    ) -> DiscoveredJob | None:
        """
        Retrieve a job using the portal's source and external job ID.
        """
        raise NotImplementedError

    @abstractmethod
    def get_internal_id_by_external_id(
        self,
        *,
        source: JobSourceType,
        external_job_id: str,
    ) -> UUID | None:
        """
        Retrieve the persistent database UUID for a job using its
        portal source and external job ID.

        This is required when another persistence model, such as an
        application, needs to reference jobs.id.
        """
        raise NotImplementedError

    @abstractmethod
    def upsert(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """
        Create the job if it does not exist, otherwise update it.
        """
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        job_id: UUID,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """Update an existing discovered job."""
        raise NotImplementedError

    @abstractmethod
    def list_active(
        self,
        *,
        source: JobSourceType | None = None,
        limit: int = 100,
    ) -> list[DiscoveredJob]:
        """
        Return active discovered jobs.

        Results are ordered newest-first.
        """
        raise NotImplementedError

    @abstractmethod
    def deactivate(
        self,
        job_id: UUID,
    ) -> None:
        """Mark a job as inactive."""
        raise NotImplementedError

    @abstractmethod
    def count_active(
        self,
        *,
        source: JobSourceType | None = None,
    ) -> int:
        """Return the number of active discovered jobs."""
        raise NotImplementedError