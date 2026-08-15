"""
Domain repository contract for job matching results.

No SQLAlchemy, PostgreSQL, Supabase, or infrastructure-specific
implementation belongs in this module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.job_discovery.domain.matching.job_matching import (
    JobMatchResult,
)


class JobMatchRepository(ABC):
    """
    Abstract repository contract for persisted job-match results.
    """

    @abstractmethod
    def create(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        resume_id: UUID | None,
        result: JobMatchResult,
    ) -> UUID:
        """Persist a new job-match result."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(
        self,
        match_id: UUID,
    ) -> JobMatchResult | None:
        """Retrieve a persisted match result."""
        raise NotImplementedError

    @abstractmethod
    def get_for_job(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        resume_id: UUID | None = None,
    ) -> JobMatchResult | None:
        """
        Retrieve the persisted match for a job/user/resume combination.
        """
        raise NotImplementedError

    @abstractmethod
    def list_for_user(
        self,
        *,
        user_id: UUID,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[JobMatchResult]:
        """Retrieve persisted matching results for a user."""
        raise NotImplementedError