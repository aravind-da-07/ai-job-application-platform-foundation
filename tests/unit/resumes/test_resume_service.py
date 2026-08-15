"""
Unit tests for ResumeService.

These tests focus on resume business logic rather than SQLAlchemy.

Covered behavior:

- logical resume creation
- resume retrieval
- user resume retrieval
- first version creation
- sequential version numbering
- automatic activation of new versions
- duplicate SHA-256 protection
- unsupported file protection
- missing file protection
- directory protection
- safe filename processing
- SHA-256 calculation
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import pytest

from src.modules.resumes.domain.entities.resume import (
    Resume,
    ResumeVersion,
)
from src.modules.resumes.domain.repositories.resume_repository import (
    ResumeRepository,
)
from src.modules.resumes.services.resume_service import (
    ResumeService,
)
from src.shared.core.exceptions import (
    UnsupportedFileFormatError,
)


class InMemoryResumeRepository(ResumeRepository):
    """
    In-memory repository used to test ResumeService business logic.

    This intentionally does not use SQLAlchemy.

    Repository integration behavior is tested separately in:
        tests/integration/resumes/test_resume_repository.py
    """

    def __init__(self) -> None:
        self.resumes: dict[UUID, Resume] = {}
        self.versions: dict[UUID, ResumeVersion] = {}

    # ------------------------------------------------------------------
    # Resume operations
    # ------------------------------------------------------------------

    def create_resume(
        self,
        resume: Resume,
    ) -> Resume:
        self.resumes[resume.id] = resume
        return resume

    def get_resume_by_id(
        self,
        resume_id: UUID,
    ) -> Resume | None:
        return self.resumes.get(resume_id)

    def get_user_resumes(
        self,
        user_id: UUID,
    ) -> list[Resume]:
        return sorted(
            [
                resume
                for resume in self.resumes.values()
                if resume.user_id == user_id
            ],
            key=lambda resume: resume.created_at,
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Version operations
    # ------------------------------------------------------------------

    def create_version(
        self,
        version: ResumeVersion,
    ) -> ResumeVersion:
        self.versions[version.id] = version
        return version

    def get_version_by_id(
        self,
        version_id: UUID,
    ) -> ResumeVersion | None:
        return self.versions.get(version_id)

    def get_active_version(
        self,
        resume_id: UUID,
    ) -> ResumeVersion | None:
        active_versions = [
            version
            for version in self.versions.values()
            if (
                version.resume_id == resume_id
                and version.is_active
            )
        ]

        if not active_versions:
            return None

        return active_versions[0]

    def get_version_by_hash(
        self,
        resume_id: UUID,
        file_hash: str,
    ) -> ResumeVersion | None:
        for version in self.versions.values():
            if (
                version.resume_id == resume_id
                and version.file_hash == file_hash
            ):
                return version

        return None

    def list_versions(
        self,
        resume_id: UUID,
    ) -> list[ResumeVersion]:
        return sorted(
            [
                version
                for version in self.versions.values()
                if version.resume_id == resume_id
            ],
            key=lambda version: version.version_number,
        )

    def activate_version(
        self,
        version_id: UUID,
    ) -> ResumeVersion:
        version = self.versions.get(version_id)

        if version is None:
            raise ValueError(
                f"Resume version '{version_id}' was not found."
            )

        # Deactivate every other version belonging to
        # the same logical resume.
        for existing in self.versions.values():
            if (
                existing.resume_id == version.resume_id
                and existing.id != version_id
                and existing.is_active
            ):
                self.versions[existing.id] = ResumeVersion(
                    id=existing.id,
                    resume_id=existing.resume_id,
                    version_number=existing.version_number,
                    filename=existing.filename,
                    file_extension=existing.file_extension,
                    storage_path=existing.storage_path,
                    file_hash=existing.file_hash,
                    file_size_bytes=existing.file_size_bytes,
                    is_active=False,
                    uploaded_at=existing.uploaded_at,
                )

        activated = ResumeVersion(
            id=version.id,
            resume_id=version.resume_id,
            version_number=version.version_number,
            filename=version.filename,
            file_extension=version.file_extension,
            storage_path=version.storage_path,
            file_hash=version.file_hash,
            file_size_bytes=version.file_size_bytes,
            is_active=True,
            uploaded_at=version.uploaded_at,
        )

        self.versions[version_id] = activated

        return activated

    def archive_resume(
        self,
        resume_id: UUID,
    ) -> Resume:
        resume = self.resumes.get(resume_id)

        if resume is None:
            raise ValueError(
                f"Resume '{resume_id}' was not found."
            )

        archived = Resume(
            id=resume.id,
            user_id=resume.user_id,
            name=resume.name,
            status=resume.status.ARCHIVED,
            created_at=resume.created_at,
        )

        self.resumes[resume_id] = archived

        return archived


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def create_service() -> tuple[
    ResumeService,
    InMemoryResumeRepository,
]:
    """Create a ResumeService with an isolated repository."""

    repository = InMemoryResumeRepository()

    service = ResumeService(
        repository
    )

    return service, repository


def create_resume(
    service: ResumeService,
    *,
    user_id: UUID | None = None,
    name: str = "Test Resume",
) -> Resume:
    """Create a logical resume for testing."""

    return service.create_resume(
        user_id=user_id or uuid4(),
        name=name,
    )


def write_file(
    directory: Path,
    filename: str,
    content: bytes,
) -> Path:
    """Create a test resume file."""

    path = directory / filename
    path.write_bytes(content)
    return path


# ----------------------------------------------------------------------
# Logical resume tests
# ----------------------------------------------------------------------


def test_create_resume() -> None:
    """ResumeService should create a logical resume."""

    service, repository = create_service()

    user_id = uuid4()

    resume = service.create_resume(
        user_id=user_id,
        name="Data Analyst Resume",
    )

    assert resume.id is not None
    assert resume.user_id == user_id
    assert resume.name == "Data Analyst Resume"

    stored = repository.get_resume_by_id(
        resume.id
    )

    assert stored is not None
    assert stored.id == resume.id


def test_get_resume() -> None:
    """ResumeService should retrieve a resume by ID."""

    service, _ = create_service()

    resume = create_resume(
        service,
        name="Stored Resume",
    )

    result = service.get_resume(
        resume.id
    )

    assert result is not None
    assert result.id == resume.id
    assert result.name == "Stored Resume"

    assert (
        service.get_resume(uuid4())
        is None
    )


def test_get_user_resumes() -> None:
    """ResumeService should return resumes belonging to a user."""

    service, _ = create_service()

    user_id = uuid4()
    another_user_id = uuid4()

    first = create_resume(
        service,
        user_id=user_id,
        name="Resume One",
    )

    second = create_resume(
        service,
        user_id=user_id,
        name="Resume Two",
    )

    create_resume(
        service,
        user_id=another_user_id,
        name="Other User Resume",
    )

    results = service.get_user_resumes(
        user_id
    )

    result_ids = {
        resume.id
        for resume in results
    }

    assert first.id in result_ids
    assert second.id in result_ids
    assert len(results) == 2


# ----------------------------------------------------------------------
# Resume version tests
# ----------------------------------------------------------------------


def test_add_first_resume_version() -> None:
    """The first uploaded file should become version 1 and active."""

    service, repository = create_service()

    resume = create_resume(
        service,
        name="Candidate Resume",
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        content = b"candidate resume version one"

        file_path = write_file(
            directory,
            "candidate.pdf",
            content,
        )

        version = service.add_resume_version(
            resume_id=resume.id,
            file_path=file_path,
            storage_path=(
                "resumes/incoming/candidate.pdf"
            ),
        )

    expected_hash = hashlib.sha256(
        content
    ).hexdigest()

    assert version.resume_id == resume.id
    assert version.version_number == 1

    # validate_resume_extension() returns the
    # extension including the leading dot.
    assert version.file_extension == ".pdf"

    assert version.file_hash == expected_hash
    assert version.file_size_bytes == len(content)
    assert version.is_active is True

    stored = repository.get_active_version(
        resume.id
    )

    assert stored is not None
    assert stored.id == version.id
    assert stored.is_active is True


def test_add_second_resume_version() -> None:
    """
    A changed resume file should become the next sequential version
    and the new version should become active.
    """

    service, repository = create_service()

    resume = create_resume(
        service,
        name="Versioned Resume",
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        first_content = b"resume version one"

        first_file = write_file(
            directory,
            "resume_v1.pdf",
            first_content,
        )

        first_version = service.add_resume_version(
            resume_id=resume.id,
            file_path=first_file,
            storage_path=(
                "resumes/incoming/resume_v1.pdf"
            ),
        )

        second_content = (
            b"resume version two with updates"
        )

        second_file = write_file(
            directory,
            "resume_v2.pdf",
            second_content,
        )

        second_version = service.add_resume_version(
            resume_id=resume.id,
            file_path=second_file,
            storage_path=(
                "resumes/incoming/resume_v2.pdf"
            ),
        )

    assert first_version.version_number == 1
    assert second_version.version_number == 2

    assert first_version.is_active is True
    assert second_version.is_active is True

    versions = repository.list_versions(
        resume.id
    )

    assert len(versions) == 2

    active = repository.get_active_version(
        resume.id
    )

    assert active is not None
    assert active.id == second_version.id

    first_stored = repository.get_version_by_id(
        first_version.id
    )

    assert first_stored is not None
    assert first_stored.is_active is False


def test_duplicate_resume_file_is_rejected() -> None:
    """Uploading the exact same file twice should be rejected."""

    service, repository = create_service()

    resume = create_resume(
        service,
        name="Duplicate Protection Resume",
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        content = b"duplicate resume content"

        first_file = write_file(
            directory,
            "resume.pdf",
            content,
        )

        service.add_resume_version(
            resume_id=resume.id,
            file_path=first_file,
            storage_path=(
                "resumes/incoming/resume.pdf"
            ),
        )

        second_file = write_file(
            directory,
            "resume_copy.pdf",
            content,
        )

        with pytest.raises(
            ValueError,
            match="already exists",
        ):
            service.add_resume_version(
                resume_id=resume.id,
                file_path=second_file,
                storage_path=(
                    "resumes/incoming/resume_copy.pdf"
                ),
            )

    versions = repository.list_versions(
        resume.id
    )

    assert len(versions) == 1


def test_missing_resume_file_is_rejected() -> None:
    """A missing file should raise FileNotFoundError."""

    service, _ = create_service()

    resume = create_resume(
        service
    )

    with TemporaryDirectory() as temporary_directory:
        missing_file = (
            Path(temporary_directory)
            / "missing.pdf"
        )

        with pytest.raises(
            FileNotFoundError,
            match="does not exist",
        ):
            service.add_resume_version(
                resume_id=resume.id,
                file_path=missing_file,
                storage_path=(
                    "resumes/incoming/missing.pdf"
                ),
            )


def test_resume_directory_is_rejected() -> None:
    """A directory cannot be registered as a resume file."""

    service, _ = create_service()

    resume = create_resume(
        service
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        with pytest.raises(
            ValueError,
            match="is not a file",
        ):
            service.add_resume_version(
                resume_id=resume.id,
                file_path=directory,
                storage_path=(
                    "resumes/incoming"
                ),
            )


def test_unsupported_resume_extension_is_rejected() -> None:
    """Unsupported file extensions should be rejected."""

    service, _ = create_service()

    resume = create_resume(
        service
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        file_path = write_file(
            directory,
            "resume.exe",
            b"not a resume",
        )

        with pytest.raises(
            UnsupportedFileFormatError,
            match="Unsupported resume format",
        ):
            service.add_resume_version(
                resume_id=resume.id,
                file_path=file_path,
                storage_path=(
                    "resumes/incoming/resume.exe"
                ),
            )


def test_supported_resume_extensions_are_accepted() -> None:
    """Supported resume formats should be accepted."""

    service, repository = create_service()

    resume = create_resume(
        service
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        pdf_file = write_file(
            directory,
            "resume.pdf",
            b"pdf resume content",
        )

        pdf_version = service.add_resume_version(
            resume_id=resume.id,
            file_path=pdf_file,
            storage_path=(
                "resumes/incoming/resume.pdf"
            ),
        )

        docx_file = write_file(
            directory,
            "resume.docx",
            b"docx resume content",
        )

        docx_version = service.add_resume_version(
            resume_id=resume.id,
            file_path=docx_file,
            storage_path=(
                "resumes/incoming/resume.docx"
            ),
        )

        txt_file = write_file(
            directory,
            "resume.txt",
            b"text resume content",
        )

        txt_version = service.add_resume_version(
            resume_id=resume.id,
            file_path=txt_file,
            storage_path=(
                "resumes/incoming/resume.txt"
            ),
        )

    assert pdf_version.file_extension == ".pdf"
    assert docx_version.file_extension == ".docx"
    assert txt_version.file_extension == ".txt"

    assert [
        version.version_number
        for version in repository.list_versions(
            resume.id
        )
    ] == [1, 2, 3]


def test_safe_filename_is_used() -> None:
    """The stored filename should pass through safe filename handling."""

    service, _ = create_service()

    resume = create_resume(
        service
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        file_path = write_file(
            directory,
            "My Candidate Resume.pdf",
            b"safe filename test",
        )

        version = service.add_resume_version(
            resume_id=resume.id,
            file_path=file_path,
            storage_path=(
                "resumes/incoming/"
                "My Candidate Resume.pdf"
            ),
        )

    assert version.filename
    assert version.filename.endswith(".pdf")


def test_get_active_version() -> None:
    """ResumeService should expose the active version."""

    service, _ = create_service()

    resume = create_resume(
        service
    )

    with TemporaryDirectory() as temporary_directory:
        file_path = write_file(
            Path(temporary_directory),
            "active.pdf",
            b"active version",
        )

        created = service.add_resume_version(
            resume_id=resume.id,
            file_path=file_path,
            storage_path=(
                "resumes/incoming/active.pdf"
            ),
        )

    active = service.get_active_version(
        resume.id
    )

    assert active is not None
    assert active.id == created.id
    assert active.is_active is True


def test_list_versions() -> None:
    """ResumeService should expose the complete version history."""

    service, _ = create_service()

    resume = create_resume(
        service
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        for number in range(1, 4):
            file_path = write_file(
                directory,
                f"resume_{number}.pdf",
                f"resume version {number}".encode(),
            )

            service.add_resume_version(
                resume_id=resume.id,
                file_path=file_path,
                storage_path=(
                    f"resumes/incoming/"
                    f"resume_{number}.pdf"
                ),
            )

    versions = service.list_versions(
        resume.id
    )

    assert len(versions) == 3

    assert [
        version.version_number
        for version in versions
    ] == [1, 2, 3]


def test_service_can_activate_existing_version() -> None:
    """An existing historical version can be made active again."""

    service, _ = create_service()

    resume = create_resume(
        service
    )

    with TemporaryDirectory() as temporary_directory:
        directory = Path(
            temporary_directory
        )

        first_file = write_file(
            directory,
            "first.pdf",
            b"first resume",
        )

        first = service.add_resume_version(
            resume_id=resume.id,
            file_path=first_file,
            storage_path=(
                "resumes/incoming/first.pdf"
            ),
        )

        second_file = write_file(
            directory,
            "second.pdf",
            b"second resume",
        )

        second = service.add_resume_version(
            resume_id=resume.id,
            file_path=second_file,
            storage_path=(
                "resumes/incoming/second.pdf"
            ),
        )

    active_before = service.get_active_version(
        resume.id
    )

    assert active_before is not None
    assert active_before.id == second.id

    reactivated = service.activate_version(
        first.id
    )

    assert reactivated.id == first.id
    assert reactivated.is_active is True

    active_after = service.get_active_version(
        resume.id
    )

    assert active_after is not None
    assert active_after.id == first.id


def test_sha256_file_helper() -> None:
    """The service SHA-256 helper should match hashlib."""

    service, _ = create_service()

    content = (
        b"known content for sha256 verification"
    )

    expected_hash = hashlib.sha256(
        content
    ).hexdigest()

    with TemporaryDirectory() as temporary_directory:
        file_path = write_file(
            Path(temporary_directory),
            "hash-test.pdf",
            content,
        )

        actual_hash = (
            service._sha256_file(file_path)
        )

    assert actual_hash == expected_hash