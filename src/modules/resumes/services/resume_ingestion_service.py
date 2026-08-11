"""
Automatic resume-folder ingestion service.

Scans the configured resume folder for new or modified resume files
and sends them through ResumeService.

This component is intentionally independent of the scheduler.
SchedulerManager can call `scan()` periodically.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from threading import Lock
from typing import Final
from uuid import UUID

from src.modules.resumes.services.resume_service import ResumeService
from src.shared.config.constants import EventType, SUPPORTED_RESUME_FORMATS
from src.shared.events.event_bus import Event, EventBus
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_STORAGE_PREFIX: Final[str] = "resumes"


class ResumeIngestionService:
    """
    Detects new or changed resume files and registers them through
    ResumeService.

    The scanner uses SHA-256 fingerprints so changing a resume file
    creates a new resume version while unchanged files are ignored.
    """

    def __init__(
        self,
        resume_service: ResumeService,
        event_bus: EventBus,
        resume_folder: str | Path,
        user_id: UUID,
        resume_id: UUID,
    ) -> None:
        self._resume_service = resume_service
        self._event_bus = event_bus
        self._resume_folder = Path(resume_folder)
        self._user_id = user_id
        self._resume_id = resume_id

        self._known_hashes: dict[str, str] = {}
        self._lock = Lock()

    def scan(self) -> int:
        """
        Scan the resume folder.

        Returns the number of newly registered resume versions.
        """

        if not self._resume_folder.exists():
            logger.warning(
                "Resume folder does not exist: {}",
                self._resume_folder,
            )
            return 0

        if not self._resume_folder.is_dir():
            logger.error(
                "Configured resume path is not a directory: {}",
                self._resume_folder,
            )
            return 0

        processed_count = 0

        for file_path in sorted(self._resume_folder.iterdir()):
            if not self._is_supported_file(file_path):
                continue

            try:
                file_hash = self._sha256_file(file_path)

                if self._is_known(file_path, file_hash):
                    continue

                storage_path = self._build_storage_path(
                    file_path
                )

                version = self._resume_service.add_resume_version(
                    resume_id=self._resume_id,
                    file_path=file_path,
                    storage_path=storage_path,
                )

                self._remember(
                    file_path,
                    file_hash,
                )

                self._event_bus.publish(
                    Event(
                        type=EventType.RESUME_UPLOADED,
                        payload={
                            "user_id": str(self._user_id),
                            "resume_id": str(self._resume_id),
                            "resume_version_id": str(version.id),
                            "version_number": version.version_number,
                            "filename": version.filename,
                            "file_extension": version.file_extension,
                            "file_hash": version.file_hash,
                            "file_size_bytes": version.file_size_bytes,
                            "storage_path": version.storage_path,
                        },
                    )
                )

                logger.info(
                    "Resume ingested successfully: {} "
                    "(version={})",
                    file_path,
                    version.version_number,
                )

                processed_count += 1

            except ValueError as exc:
                # Duplicate files and business validation failures
                # should not stop processing other files.
                logger.info(
                    "Resume skipped: {} ({})",
                    file_path,
                    exc,
                )

                # Remember the hash so the scheduler does not
                # repeatedly attempt the same duplicate.
                try:
                    file_hash = self._sha256_file(file_path)
                    self._remember(file_path, file_hash)
                except OSError:
                    pass

            except OSError as exc:
                logger.exception(
                    "Unable to read resume file {}: {}",
                    file_path,
                    exc,
                )

            except Exception:
                # One broken resume must never stop the entire
                # automatic ingestion cycle.
                logger.exception(
                    "Unexpected error while processing resume: {}",
                    file_path,
                )

        return processed_count

    def clear_cache(self) -> None:
        """
        Clear the in-memory fingerprint cache.

        Primarily useful for tests and controlled rescans.
        """

        with self._lock:
            self._known_hashes.clear()

    def _is_known(
        self,
        file_path: Path,
        file_hash: str,
    ) -> bool:
        """
        Determine whether a file has already been seen with
        the same content hash.
        """

        key = str(file_path.resolve())

        with self._lock:
            return self._known_hashes.get(key) == file_hash

    def _remember(
        self,
        file_path: Path,
        file_hash: str,
    ) -> None:
        """Remember the latest fingerprint for a file."""

        key = str(file_path.resolve())

        with self._lock:
            self._known_hashes[key] = file_hash

    @staticmethod
    def _is_supported_file(
        file_path: Path,
    ) -> bool:
        """Return True when the path is a supported resume file."""

        return (
            file_path.is_file()
            and file_path.suffix.lower()
            in SUPPORTED_RESUME_FORMATS
        )

    @staticmethod
    def _sha256_file(
        file_path: Path,
        chunk_size: int = 1024 * 1024,
    ) -> str:
        """Calculate SHA-256 without loading the entire file."""

        digest = hashlib.sha256()

        with file_path.open("rb") as file:
            while chunk := file.read(chunk_size):
                digest.update(chunk)

        return digest.hexdigest()

    @staticmethod
    def _build_storage_path(
        file_path: Path,
    ) -> str:
        """
        Build the logical storage path.

        Actual Supabase Storage upload will be implemented in the
        storage infrastructure layer later.
        """

        return (
            f"{_DEFAULT_STORAGE_PREFIX}/"
            f"incoming/{file_path.name}"
        )