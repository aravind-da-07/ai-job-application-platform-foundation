"""
Resume application service.

Coordinates resume business operations between:
- Local resume files
- Resume domain entities
- Resume repository
- Resume versioning
- File validation
- SHA-256 duplicate detection

The service does not contain SQLAlchemy-specific code.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from src.modules.resumes.domain.entities.resume import (
    Resume,
    ResumeVersion,
)
from src.modules.resumes.domain.repositories.resume_repository import (
    ResumeRepository,
)
from src.shared.utils.file_helpers import (
    safe_filename,
    validate_resume_extension,
)


class ResumeService:
    """
    Application service responsible for resume lifecycle management.

    This service is intentionally independent of SQLAlchemy.
    It works through the ResumeRepository abstraction.
    """

    def __init__(self, repository: ResumeRepository) -> None:
        self._repository = repository

    # ------------------------------------------------------------------
    # Resume operations
    # ------------------------------------------------------------------

    def create_resume(
        self,
        user_id: UUID,
        name: str,
    ) -> Resume:
        """
        Create a new logical resume for a user.
        """

        resume = Resume(
            user_id=user_id,
            name=name,
        )

        return self._repository.create_resume(resume)

    def get_resume(
        self,
        resume_id: UUID,
    ) -> Resume | None:
        """Retrieve a resume by ID."""

        return self._repository.get_resume_by_id(resume_id)

    def get_user_resumes(
        self,
        user_id: UUID,
    ) -> list[Resume]:
        """Retrieve all resumes belonging to a user."""

        return self._repository.get_user_resumes(user_id)

    # ------------------------------------------------------------------
    # Resume file processing
    # ------------------------------------------------------------------

    def add_resume_version(
        self,
        resume_id: UUID,
        file_path: str | Path,
        storage_path: str,
    ) -> ResumeVersion:
        """
        Register a new resume file as a new version.

        Workflow:

        1. Validate the file exists.
        2. Validate the extension.
        3. Generate a safe filename.
        4. Calculate SHA-256 hash.
        5. Detect duplicate file.
        6. Determine the next version number.
        7. Create the version in the database.
        8. Activate the new version.

        The physical file is not moved by this method.
        File storage will be handled by the storage layer later.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Resume file does not exist: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Resume path is not a file: {path}"
            )

        # Validate supported resume format.
        extension = validate_resume_extension(path.name)

        # Normalize the filename for safe storage.
        filename = safe_filename(path.name)

        # Calculate SHA-256 fingerprint.
        file_hash = self._sha256_file(path)

        # Check whether this exact file already exists
        # for the logical resume.
        existing_version = self._repository.get_version_by_hash(
            resume_id,
            file_hash,
        )

        if existing_version is not None:
            raise ValueError(
                "This resume file already exists as "
                f"version {existing_version.version_number}."
            )

        # Determine the next version number.
        existing_versions = self._repository.list_versions(
            resume_id
        )

        if existing_versions:
            next_version_number = (
                max(
                    version.version_number
                    for version in existing_versions
                )
                + 1
            )
        else:
            next_version_number = 1

        # Create the new version initially as inactive.
        version = ResumeVersion(
            resume_id=resume_id,
            version_number=next_version_number,
            filename=filename,
            file_extension=extension,
            storage_path=storage_path,
            file_hash=file_hash,
            file_size_bytes=path.stat().st_size,
            is_active=False,
        )

        created_version = self._repository.create_version(
            version
        )

        # Make the new version the active version.
        return self._repository.activate_version(
            created_version.id
        )

    # ------------------------------------------------------------------
    # Version operations
    # ------------------------------------------------------------------

    def get_active_version(
        self,
        resume_id: UUID,
    ) -> ResumeVersion | None:
        """Return the currently active resume version."""

        return self._repository.get_active_version(
            resume_id
        )

    def get_version(
        self,
        version_id: UUID,
    ) -> ResumeVersion | None:
        """Retrieve a specific resume version."""

        return self._repository.get_version_by_id(
            version_id
        )

    def list_versions(
        self,
        resume_id: UUID,
    ) -> list[ResumeVersion]:
        """Return all historical versions of a resume."""

        return self._repository.list_versions(
            resume_id
        )

    def activate_version(
        self,
        version_id: UUID,
    ) -> ResumeVersion:
        """Make an existing resume version active."""

        return self._repository.activate_version(
            version_id
        )

    def archive_resume(
        self,
        resume_id: UUID,
    ) -> Resume:
        """Archive a logical resume."""

        return self._repository.archive_resume(
            resume_id
        )

    # ------------------------------------------------------------------
    # File utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256_file(
        file_path: Path,
        chunk_size: int = 1024 * 1024,
    ) -> str:
        """
        Calculate the SHA-256 hash of a file.

        The file is processed in chunks instead of loading the entire
        file into memory.
        """

        digest = hashlib.sha256()

        with file_path.open("rb") as file:
            while chunk := file.read(chunk_size):
                digest.update(chunk)

        return digest.hexdigest()