"""
Repository contract for resume management.

The domain layer defines what resume persistence operations are required.
The infrastructure layer will provide the SQLAlchemy implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.resumes.domain.entities.resume import Resume, ResumeVersion


class ResumeRepository(ABC):
    """Abstract repository for resumes and resume versions."""

    @abstractmethod
    def create_resume(self, resume: Resume) -> Resume:
        """Create a new logical resume."""
        raise NotImplementedError

    @abstractmethod
    def get_resume_by_id(self, resume_id: UUID) -> Resume | None:
        """Retrieve a logical resume by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_user_resumes(self, user_id: UUID) -> list[Resume]:
        """Retrieve all resumes belonging to a user."""
        raise NotImplementedError

    @abstractmethod
    def create_version(self, version: ResumeVersion) -> ResumeVersion:
        """Create a new resume version."""
        raise NotImplementedError

    @abstractmethod
    def get_version_by_id(self, version_id: UUID) -> ResumeVersion | None:
        """Retrieve a resume version by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_active_version(self, resume_id: UUID) -> ResumeVersion | None:
        """Retrieve the currently active version."""
        raise NotImplementedError

    @abstractmethod
    def get_version_by_hash(
        self,
        resume_id: UUID,
        file_hash: str,
    ) -> ResumeVersion | None:
        """Find an existing version using its SHA-256 hash."""
        raise NotImplementedError

    @abstractmethod
    def list_versions(self, resume_id: UUID) -> list[ResumeVersion]:
        """List all versions for a logical resume."""
        raise NotImplementedError

    @abstractmethod
    def activate_version(self, version_id: UUID) -> ResumeVersion:
        """
        Make one resume version active and deactivate the previous
        active version.
        """
        raise NotImplementedError

    @abstractmethod
    def archive_resume(self, resume_id: UUID) -> Resume:
        """Archive a logical resume."""
        raise NotImplementedError