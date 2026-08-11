"""
SQLAlchemy implementation of the ResumeRepository contract.

This repository handles persistence for logical resumes and their
versioned resume files.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.modules.resumes.domain.entities.resume import (
    Resume,
    ResumeStatus,
    ResumeVersion,
)
from src.modules.resumes.domain.repositories.resume_repository import (
    ResumeRepository,
)
from src.modules.resumes.infrastructure.models.resume_model import (
    ResumeModel,
    ResumeVersionModel,
)


class SQLAlchemyResumeRepository(ResumeRepository):
    """SQLAlchemy implementation of ResumeRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Resume operations
    # ------------------------------------------------------------------

    def create_resume(self, resume: Resume) -> Resume:
        """Create and persist a logical resume."""

        model = ResumeModel(
            id=resume.id,
            user_id=resume.user_id,
            name=resume.name,
            status=resume.status.value,
            created_at=resume.created_at,
            updated_at=resume.created_at,
        )

        self._session.add(model)
        self._session.flush()

        return self._to_domain_resume(model)

    def get_resume_by_id(self, resume_id: UUID) -> Resume | None:
        """Retrieve a logical resume by ID."""

        model = self._session.get(ResumeModel, resume_id)

        if model is None:
            return None

        return self._to_domain_resume(model)

    def get_user_resumes(self, user_id: UUID) -> list[Resume]:
        """Retrieve all resumes belonging to a user."""

        statement = (
            select(ResumeModel)
            .where(ResumeModel.user_id == user_id)
            .order_by(ResumeModel.created_at.desc())
        )

        models = self._session.scalars(statement).all()

        return [self._to_domain_resume(model) for model in models]

    # ------------------------------------------------------------------
    # Resume version operations
    # ------------------------------------------------------------------

    def create_version(self, version: ResumeVersion) -> ResumeVersion:
        """Create and persist a resume version."""

        model = ResumeVersionModel(
            id=version.id,
            resume_id=version.resume_id,
            version_number=version.version_number,
            filename=version.filename,
            file_extension=version.file_extension,
            storage_path=version.storage_path,
            file_hash=version.file_hash,
            file_size_bytes=version.file_size_bytes,
            is_active=version.is_active,
            uploaded_at=version.uploaded_at,
            created_at=version.uploaded_at,
            updated_at=version.uploaded_at,
        )

        self._session.add(model)
        self._session.flush()

        return self._to_domain_version(model)

    def get_version_by_id(self, version_id: UUID) -> ResumeVersion | None:
        """Retrieve a resume version by ID."""

        model = self._session.get(ResumeVersionModel, version_id)

        if model is None:
            return None

        return self._to_domain_version(model)

    def get_active_version(self, resume_id: UUID) -> ResumeVersion | None:
        """Retrieve the currently active resume version."""

        statement = (
            select(ResumeVersionModel)
            .where(
                ResumeVersionModel.resume_id == resume_id,
                ResumeVersionModel.is_active.is_(True),
            )
            .limit(1)
        )

        model = self._session.scalars(statement).first()

        if model is None:
            return None

        return self._to_domain_version(model)

    def get_version_by_hash(
        self,
        resume_id: UUID,
        file_hash: str,
    ) -> ResumeVersion | None:
        """Find an existing resume version using its SHA-256 hash."""

        statement = (
            select(ResumeVersionModel)
            .where(
                ResumeVersionModel.resume_id == resume_id,
                ResumeVersionModel.file_hash == file_hash,
            )
            .limit(1)
        )

        model = self._session.scalars(statement).first()

        if model is None:
            return None

        return self._to_domain_version(model)

    def list_versions(self, resume_id: UUID) -> list[ResumeVersion]:
        """List all versions for a resume."""

        statement = (
            select(ResumeVersionModel)
            .where(ResumeVersionModel.resume_id == resume_id)
            .order_by(ResumeVersionModel.version_number.asc())
        )

        models = self._session.scalars(statement).all()

        return [self._to_domain_version(model) for model in models]

    def activate_version(self, version_id: UUID) -> ResumeVersion:
        """
        Make one resume version active.

        The previous active version is deactivated before the requested
        version is activated. Both operations occur inside the caller's
        transaction.
        """

        version_model = self._session.get(
            ResumeVersionModel,
            version_id,
        )

        if version_model is None:
            raise ValueError(
                f"Resume version '{version_id}' was not found."
            )

        # Deactivate every currently active version belonging to the
        # same logical resume.
        self._session.execute(
            update(ResumeVersionModel)
            .where(
                ResumeVersionModel.resume_id == version_model.resume_id,
                ResumeVersionModel.id != version_id,
                ResumeVersionModel.is_active.is_(True),
            )
            .values(is_active=False)
        )

        # Activate the requested version.
        version_model.is_active = True

        self._session.flush()

        return self._to_domain_version(version_model)

    def archive_resume(self, resume_id: UUID) -> Resume:
        """Archive a logical resume."""

        model = self._session.get(ResumeModel, resume_id)

        if model is None:
            raise ValueError(
                f"Resume '{resume_id}' was not found."
            )

        model.status = ResumeStatus.ARCHIVED.value

        self._session.flush()

        return self._to_domain_resume(model)

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain_resume(model: ResumeModel) -> Resume:
        """Convert a SQLAlchemy resume model to the domain entity."""

        return Resume(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            status=ResumeStatus(model.status),
            created_at=model.created_at,
        )

    @staticmethod
    def _to_domain_version(
        model: ResumeVersionModel,
    ) -> ResumeVersion:
        """Convert a SQLAlchemy version model to the domain entity."""

        return ResumeVersion(
            id=model.id,
            resume_id=model.resume_id,
            version_number=model.version_number,
            filename=model.filename,
            file_extension=model.file_extension,
            storage_path=model.storage_path,
            file_hash=model.file_hash,
            file_size_bytes=model.file_size_bytes,
            is_active=model.is_active,
            uploaded_at=model.uploaded_at,
        )