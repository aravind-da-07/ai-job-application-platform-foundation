"""
Resume upload application service.

Coordinates physical file storage with ResumeService.

Responsibilities:
- Validate the supplied local file.
- Retrieve the logical resume.
- Generate a safe storage path.
- Upload the file through StorageAdapter.
- Register the uploaded file through ResumeService.
- Remove the uploaded object if database registration fails.

This service contains no SQLAlchemy-specific code and does not
depend directly on Supabase.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from src.modules.resumes.domain.entities.resume import (
    Resume,
    ResumeVersion,
)
from src.modules.resumes.services.resume_service import ResumeService
from src.shared.storage.storage_adapter import StorageAdapter
from src.shared.utils.file_helpers import safe_filename


class UploadService:
    """
    Application service responsible for resume file uploads.
    """

    def __init__(
        self,
        *,
        resume_service: ResumeService,
        storage: StorageAdapter,
    ) -> None:
        self._resume_service = resume_service
        self._storage = storage

    def get_resume(
        self,
        resume_id: UUID,
    ) -> Resume | None:
        """
        Retrieve the logical resume associated with an upload.
        """

        return self._resume_service.get_resume(
            resume_id
        )

    def upload_resume(
        self,
        *,
        user_id: UUID,
        resume_id: UUID,
        file_path: str | Path,
    ) -> ResumeVersion:
        """
        Upload and register a resume version.

        Workflow:

        1. Validate local file.
        2. Generate safe filename.
        3. Generate logical storage path.
        4. Upload file to configured storage.
        5. Register ResumeVersion through ResumeService.
        6. If registration fails, remove uploaded storage object.

        Args:
            user_id:
                Owner of the resume.

            resume_id:
                Logical resume receiving the new version.

            file_path:
                Local path to the resume file.

        Returns:
            The newly created and activated ResumeVersion.

        Raises:
            FileNotFoundError:
                If the local file does not exist.

            ValueError:
                If the local path is not a file or resume validation fails.

            StorageError:
                If storage upload fails.
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

        filename = safe_filename(
            path.name
        )

        storage_path = self._build_storage_path(
            user_id=user_id,
            resume_id=resume_id,
            filename=filename,
        )

        uploaded_path = self._storage.upload(
            source_path=path,
            destination_path=storage_path,
        )

        try:
            version = self._resume_service.add_resume_version(
                resume_id=resume_id,
                file_path=path,
                storage_path=uploaded_path,
            )

        except Exception:
            # Database/business registration failed after the
            # physical object was uploaded. Remove the object
            # to prevent orphaned files in storage.
            try:
                self._storage.delete(
                    uploaded_path
                )
            except Exception:
                # The original exception is more useful to the caller.
                # Storage cleanup failure should be logged by the
                # storage implementation.
                pass

            raise

        return version

    @staticmethod
    def _build_storage_path(
        *,
        user_id: UUID,
        resume_id: UUID,
        filename: str,
    ) -> str:
        """
        Build a unique logical storage path.

        The existing `resumes/incoming` convention is retained while
        adding user/resume identifiers to prevent filename collisions.
        """

        return (
            "resumes/incoming/"
            f"{user_id}/"
            f"{resume_id}/"
            f"{filename}"
        )


__all__ = ["UploadService"]