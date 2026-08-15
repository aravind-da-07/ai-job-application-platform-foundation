"""
Unit tests for ResumeIngestionService.

The tests use:

- a temporary filesystem folder
- the real ResumeService
- an in-memory ResumeRepository
- the real in-process EventBus

No SQLAlchemy database or external storage is required.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from src.modules.resumes.services.resume_ingestion_service import (
    ResumeIngestionService,
)
from src.modules.resumes.services.resume_service import (
    ResumeService,
)
from src.shared.config.constants import EventType
from src.shared.events.event_bus import (
    Event,
    EventBus,
)

from tests.unit.resumes.test_resume_service import (
    InMemoryResumeRepository,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def create_ingestion_service(
    resume_folder: str | Path,
) -> tuple[
    ResumeIngestionService,
    ResumeService,
    InMemoryResumeRepository,
    EventBus,
]:
    """
    Create an isolated ingestion service.

    A fresh repository and event bus are created for every test.
    """

    repository = InMemoryResumeRepository()

    resume_service = ResumeService(
        repository
    )

    event_bus = EventBus()

    user_id = uuid4()
    resume_id = uuid4()

    resume_service.create_resume(
        user_id=user_id,
        name="Test Candidate Resume",
    )

    # The ingestion service receives the logical resume ID.
    # Create the logical resume using the requested ID instead of
    # relying on the generated ID above.
    #
    # Rebuild the repository state cleanly.
    repository.resumes.clear()

    from src.modules.resumes.domain.entities.resume import Resume

    resume = Resume(
        id=resume_id,
        user_id=user_id,
        name="Test Candidate Resume",
    )

    repository.create_resume(resume)

    service = ResumeIngestionService(
        resume_service=resume_service,
        event_bus=event_bus,
        resume_folder=resume_folder,
        user_id=user_id,
        resume_id=resume_id,
    )

    return (
        service,
        resume_service,
        repository,
        event_bus,
    )


def write_file(
    directory: Path,
    filename: str,
    content: bytes,
) -> Path:
    """Create a file inside the temporary resume folder."""

    path = directory / filename
    path.write_bytes(content)
    return path


# ----------------------------------------------------------------------
# Basic discovery tests
# ----------------------------------------------------------------------


def test_scan_processes_new_pdf() -> None:
    """A new PDF should create one resume version."""

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        resume_file = write_file(
            directory,
            "candidate.pdf",
            b"candidate resume",
        )

        (
            ingestion_service,
            resume_service,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        processed = ingestion_service.scan()

        assert processed == 1

        assert len(repository.versions) == 1

        version = next(
            iter(repository.versions.values())
        )

        assert version.version_number == 1
        assert version.file_extension == ".pdf"
        assert version.filename == "candidate.pdf"

        active = resume_service.get_active_version(
            version.resume_id
        )

        assert active is not None
        assert active.id == version.id

        assert resume_file.exists()


def test_scan_processes_multiple_supported_files() -> None:
    """
    Multiple supported resume files should all be processed during
    one scan.
    """

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        write_file(
            directory,
            "candidate.pdf",
            b"pdf resume",
        )

        write_file(
            directory,
            "candidate.docx",
            b"docx resume",
        )

        write_file(
            directory,
            "candidate.txt",
            b"text resume",
        )

        (
            ingestion_service,
            _,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        processed = ingestion_service.scan()

        assert processed == 3
        assert len(repository.versions) == 3

        versions = sorted(
            repository.versions.values(),
            key=lambda version: version.version_number,
        )

        assert [
            version.version_number
            for version in versions
        ] == [1, 2, 3]

        assert {
            version.file_extension
            for version in versions
        } == {
            ".pdf",
            ".docx",
            ".txt",
        }


def test_scan_ignores_unsupported_files() -> None:
    """Unsupported files should not be processed."""

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        write_file(
            directory,
            "candidate.pdf",
            b"valid resume",
        )

        write_file(
            directory,
            "photo.png",
            b"not a resume",
        )

        write_file(
            directory,
            "spreadsheet.xlsx",
            b"not a resume",
        )

        write_file(
            directory,
            "document.exe",
            b"not a resume",
        )

        (
            ingestion_service,
            _,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        processed = ingestion_service.scan()

        assert processed == 1
        assert len(repository.versions) == 1

        version = next(
            iter(repository.versions.values())
        )

        assert version.file_extension == ".pdf"


# ----------------------------------------------------------------------
# Fingerprint / duplicate tests
# ----------------------------------------------------------------------


def test_second_scan_ignores_unchanged_file() -> None:
    """
    Scanning the same unchanged file twice should only create one
    version.
    """

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        write_file(
            directory,
            "candidate.pdf",
            b"unchanged resume",
        )

        (
            ingestion_service,
            _,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        first_scan = ingestion_service.scan()
        second_scan = ingestion_service.scan()

        assert first_scan == 1
        assert second_scan == 0

        assert len(repository.versions) == 1


def test_modified_file_creates_new_version() -> None:
    """
    Changing the content of an already-known file should create
    another resume version.
    """

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        resume_file = write_file(
            directory,
            "candidate.pdf",
            b"version one",
        )

        (
            ingestion_service,
            resume_service,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        first_scan = ingestion_service.scan()

        assert first_scan == 1

        first_active = (
            resume_service.get_active_version(
                next(
                    iter(repository.resumes
                        .keys())
                )
            )
        )

        assert first_active is not None
        assert first_active.version_number == 1

        resume_file.write_bytes(
            b"version two with changes"
        )

        second_scan = ingestion_service.scan()

        assert second_scan == 1
        assert len(repository.versions) == 2

        versions = sorted(
            repository.versions.values(),
            key=lambda version: version.version_number,
        )

        assert [
            version.version_number
            for version in versions
        ] == [1, 2]

        active = resume_service.get_active_version(
            versions[0].resume_id
        )

        assert active is not None
        assert active.version_number == 2


def test_clear_cache_allows_controlled_rescan() -> None:
    """
    Clearing the in-memory fingerprint cache should allow the same
    file to be processed again.

    ResumeService still protects against the duplicate SHA-256 hash,
    so the second scan should not create a second database version.
    """

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        write_file(
            directory,
            "candidate.pdf",
            b"same content",
        )

        (
            ingestion_service,
            _,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        first_scan = ingestion_service.scan()

        assert first_scan == 1
        assert len(repository.versions) == 1

        ingestion_service.clear_cache()

        second_scan = ingestion_service.scan()

        # ResumeIngestionService retries the file after clearing
        # its memory cache, but ResumeService rejects the duplicate
        # SHA-256 hash.
        assert second_scan == 0

        assert len(repository.versions) == 1


# ----------------------------------------------------------------------
# Event tests
# ----------------------------------------------------------------------


def test_scan_publishes_resume_uploaded_event() -> None:
    """A successfully ingested resume should publish an event."""

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        write_file(
            directory,
            "candidate.pdf",
            b"event test resume",
        )

        (
            ingestion_service,
            _,
            repository,
            event_bus,
        ) = create_ingestion_service(
            directory
        )

        received_events: list[Event] = []

        event_bus.subscribe(
            EventType.RESUME_UPLOADED,
            received_events.append,
        )

        processed = ingestion_service.scan()

        assert processed == 1
        assert len(received_events) == 1

        event = received_events[0]

        assert (
            event.type
            == EventType.RESUME_UPLOADED
        )

        version = next(
            iter(repository.versions.values())
        )

        assert (
            event.payload["resume_version_id"]
            == str(version.id)
        )

        assert (
            event.payload["resume_id"]
            == str(version.resume_id)
        )

        assert (
            event.payload["version_number"]
            == version.version_number
        )

        assert (
            event.payload["filename"]
            == version.filename
        )

        assert (
            event.payload["file_extension"]
            == version.file_extension
        )

        assert (
            event.payload["file_hash"]
            == version.file_hash
        )

        assert (
            event.payload["file_size_bytes"]
            == version.file_size_bytes
        )

        assert (
            event.payload["storage_path"]
            == version.storage_path
        )


def test_unsupported_file_does_not_publish_event() -> None:
    """Ignored files must not produce RESUME_UPLOADED events."""

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        write_file(
            directory,
            "image.png",
            b"not a resume",
        )

        (
            ingestion_service,
            _,
            _,
            event_bus,
        ) = create_ingestion_service(
            directory
        )

        received_events: list[Event] = []

        event_bus.subscribe(
            EventType.RESUME_UPLOADED,
            received_events.append,
        )

        processed = ingestion_service.scan()

        assert processed == 0
        assert received_events == []


def test_second_scan_does_not_publish_duplicate_event() -> None:
    """
    An unchanged file should not publish another upload event.
    """

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        write_file(
            directory,
            "candidate.pdf",
            b"same resume",
        )

        (
            ingestion_service,
            _,
            _,
            event_bus,
        ) = create_ingestion_service(
            directory
        )

        received_events: list[Event] = []

        event_bus.subscribe(
            EventType.RESUME_UPLOADED,
            received_events.append,
        )

        assert ingestion_service.scan() == 1
        assert ingestion_service.scan() == 0

        assert len(received_events) == 1


# ----------------------------------------------------------------------
# Folder validation tests
# ----------------------------------------------------------------------


def test_missing_folder_returns_zero() -> None:
    """A missing resume folder should safely return zero."""

    with TemporaryDirectory() as temporary_directory:
        missing_folder = (
            Path(temporary_directory)
            / "does-not-exist"
        )

        (
            ingestion_service,
            _,
            repository,
            event_bus,
        ) = create_ingestion_service(
            missing_folder
        )

        received_events: list[Event] = []

        event_bus.subscribe(
            EventType.RESUME_UPLOADED,
            received_events.append,
        )

        processed = ingestion_service.scan()

        assert processed == 0
        assert repository.versions == {}
        assert received_events == []


def test_file_path_as_resume_folder_returns_zero() -> None:
    """A configured file path cannot be used as a resume folder."""

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        configured_file = write_file(
            directory,
            "not-a-folder.txt",
            b"this is a file",
        )

        (
            ingestion_service,
            _,
            repository,
            _,
        ) = create_ingestion_service(
            configured_file
        )

        processed = ingestion_service.scan()

        assert processed == 0
        assert repository.versions == {}


def test_empty_folder_returns_zero() -> None:
    """An empty resume folder should produce zero processed files."""

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        (
            ingestion_service,
            _,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        processed = ingestion_service.scan()

        assert processed == 0
        assert repository.versions == {}


# ----------------------------------------------------------------------
# Error isolation tests
# ----------------------------------------------------------------------


def test_bad_file_does_not_stop_other_files(
    monkeypatch,
) -> None:
    """
    A file that fails during processing should not prevent another
    valid resume from being processed.

    The scanner itself still handles the exception and continues.
    """

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        bad_file = write_file(
            directory,
            "bad.pdf",
            b"bad resume",
        )

        good_file = write_file(
            directory,
            "good.pdf",
            b"good resume",
        )

        (
            ingestion_service,
            _,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        original_sha256 = (
            ingestion_service._sha256_file
        )

        def failing_sha256(
            file_path: Path,
            chunk_size: int = 1024 * 1024,
        ) -> str:
            if file_path.name == bad_file.name:
                raise OSError(
                    "Simulated file read failure"
                )

            return original_sha256(
                file_path,
                chunk_size,
            )

        monkeypatch.setattr(
            ingestion_service,
            "_sha256_file",
            failing_sha256,
        )

        processed = ingestion_service.scan()

        assert processed == 1
        assert len(repository.versions) == 1

        version = next(
            iter(repository.versions.values())
        )

        assert version.filename == good_file.name


def test_business_validation_error_does_not_stop_scan(
    monkeypatch,
) -> None:
    """
    A ValueError from ResumeService should cause the affected file
    to be skipped while other files continue processing.
    """

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        rejected_file = write_file(
            directory,
            "rejected.pdf",
            b"rejected resume",
        )

        accepted_file = write_file(
            directory,
            "accepted.pdf",
            b"accepted resume",
        )

        (
            ingestion_service,
            resume_service,
            repository,
            _,
        ) = create_ingestion_service(
            directory
        )

        original_add_version = (
            resume_service.add_resume_version
        )

        def controlled_add_version(
            resume_id,
            file_path,
            storage_path,
        ):
            if (
                Path(file_path).name
                == rejected_file.name
            ):
                raise ValueError(
                    "Simulated duplicate"
                )

            return original_add_version(
                resume_id=resume_id,
                file_path=file_path,
                storage_path=storage_path,
            )

        monkeypatch.setattr(
            resume_service,
            "add_resume_version",
            controlled_add_version,
        )

        processed = ingestion_service.scan()

        assert processed == 1
        assert len(repository.versions) == 1

        version = next(
            iter(repository.versions.values())
        )

        assert (
            version.filename
            == accepted_file.name
        )