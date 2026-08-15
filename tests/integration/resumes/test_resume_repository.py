"""
Integration tests for the SQLAlchemy resume repository.

Coverage:

- logical resume creation
- resume retrieval
- user resume listing
- resume version creation
- version retrieval
- active version lookup
- SHA-256 hash lookup
- version listing
- version activation
- previous active version deactivation
- resume archiving
- missing-record protection
- domain/ORM mapping
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
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
from src.modules.resumes.infrastructure.repositories.resume_repository_impl import (
    SQLAlchemyResumeRepository,
)
from src.modules.users.infrastructure.models.user_model import (
    UserModel,
)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture()
def repository(
    db_session: Session,
) -> SQLAlchemyResumeRepository:
    """Create a resume repository backed by the test session."""

    return SQLAlchemyResumeRepository(db_session)


def create_user(
    session: Session,
    *,
    full_name: str = "Test Candidate",
    email: str | None = None,
) -> UserModel:
    """Create a valid user for resume foreign-key relationships."""

    user = UserModel(
        full_name=full_name,
        email=email or f"{uuid4()}@example.com",
    )

    session.add(user)
    session.flush()

    return user


def build_resume(
    user_id: UUID,
    *,
    name: str = "Primary Resume",
    status: ResumeStatus = ResumeStatus.ACTIVE,
) -> Resume:
    """Build a valid domain resume."""

    return Resume(
        user_id=user_id,
        name=name,
        status=status,
    )


def build_version(
    resume_id: UUID,
    *,
    version_number: int = 1,
    filename: str = "resume.pdf",
    file_extension: str = "pdf",
    storage_path: str = "resumes/test/resume.pdf",
    file_hash: str | None = None,
    file_size_bytes: int = 102400,
    is_active: bool = False,
) -> ResumeVersion:
    """Build a valid domain resume version."""

    return ResumeVersion(
        resume_id=resume_id,
        version_number=version_number,
        filename=filename,
        file_extension=file_extension,
        storage_path=storage_path,
        file_hash=file_hash
        or (
            "a" * 64
        ),
        file_size_bytes=file_size_bytes,
        is_active=is_active,
    )


# ----------------------------------------------------------------------
# Resume tests
# ----------------------------------------------------------------------


def test_create_and_get_resume(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """A created resume should be retrievable by its UUID."""

    user = create_user(
        db_session,
        full_name="Create Resume Candidate",
    )

    resume = build_resume(
        user.id,
        name="Data Analyst Resume",
    )

    persisted = repository.create_resume(
        resume
    )

    assert persisted.id == resume.id
    assert persisted.user_id == user.id
    assert persisted.name == "Data Analyst Resume"
    assert persisted.status == ResumeStatus.ACTIVE

    fetched = repository.get_resume_by_id(
        resume.id
    )

    assert fetched is not None
    assert fetched.id == resume.id
    assert fetched.user_id == user.id
    assert fetched.name == resume.name
    assert fetched.status == ResumeStatus.ACTIVE


def test_get_resume_returns_none_when_missing(
    repository: SQLAlchemyResumeRepository,
) -> None:
    """An unknown resume ID should return None."""

    result = repository.get_resume_by_id(
        uuid4()
    )

    assert result is None


def test_resume_domain_mapping(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """ORM values should map back into the domain entity correctly."""

    user = create_user(
        db_session,
        full_name="Mapping Candidate",
    )

    resume = Resume(
        id=uuid4(),
        user_id=user.id,
        name="Mapped Resume",
        status=ResumeStatus.ACTIVE,
    )

    persisted = repository.create_resume(
        resume
    )

    assert persisted.id == resume.id
    assert persisted.user_id == resume.user_id
    assert persisted.name == resume.name
    assert persisted.status == resume.status
    assert persisted.created_at == resume.created_at


def test_get_user_resumes(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """A user should receive only their own resumes."""

    first_user = create_user(
        db_session,
        full_name="First User",
    )

    second_user = create_user(
        db_session,
        full_name="Second User",
    )

    first_resume = build_resume(
        first_user.id,
        name="First Resume",
    )

    second_resume = build_resume(
        first_user.id,
        name="Second Resume",
    )

    other_resume = build_resume(
        second_user.id,
        name="Other User Resume",
    )

    repository.create_resume(first_resume)
    repository.create_resume(second_resume)
    repository.create_resume(other_resume)

    resumes = repository.get_user_resumes(
        first_user.id
    )

    assert len(resumes) == 2

    resume_ids = {
        resume.id
        for resume in resumes
    }

    assert first_resume.id in resume_ids
    assert second_resume.id in resume_ids
    assert other_resume.id not in resume_ids


def test_get_user_resumes_returns_newest_first(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """User resume listing should be ordered newest-first."""

    user = create_user(
        db_session,
        full_name="Ordering Candidate",
    )

    older = build_resume(
        user.id,
        name="Older Resume",
    )

    repository.create_resume(
        older
    )

    newer = build_resume(
        user.id,
        name="Newer Resume",
    )

    repository.create_resume(
        newer
    )

    results = repository.get_user_resumes(
        user.id
    )

    assert len(results) == 2

    assert results[0].created_at >= results[1].created_at


# ----------------------------------------------------------------------
# Resume version tests
# ----------------------------------------------------------------------


def test_create_and_get_version(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """A resume version should be persisted and retrievable."""

    user = create_user(
        db_session,
        full_name="Version Candidate",
    )

    resume = build_resume(
        user.id,
        name="Versioned Resume",
    )

    repository.create_resume(
        resume
    )

    version = build_version(
        resume.id,
        version_number=1,
        filename="candidate_resume.pdf",
        storage_path="resumes/candidate/v1.pdf",
        file_hash="b" * 64,
        file_size_bytes=204800,
    )

    persisted = repository.create_version(
        version
    )

    assert persisted.id == version.id
    assert persisted.resume_id == resume.id
    assert persisted.version_number == 1
    assert persisted.filename == "candidate_resume.pdf"
    assert persisted.file_extension == "pdf"
    assert persisted.storage_path == (
        "resumes/candidate/v1.pdf"
    )
    assert persisted.file_hash == "b" * 64
    assert persisted.file_size_bytes == 204800
    assert persisted.is_active is False

    fetched = repository.get_version_by_id(
        version.id
    )

    assert fetched is not None
    assert fetched.id == version.id
    assert fetched.resume_id == resume.id
    assert fetched.file_hash == version.file_hash


def test_get_version_returns_none_when_missing(
    repository: SQLAlchemyResumeRepository,
) -> None:
    """An unknown version ID should return None."""

    result = repository.get_version_by_id(
        uuid4()
    )

    assert result is None


def test_get_active_version_returns_none_when_no_active_version(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """A resume without an active version should return None."""

    user = create_user(
        db_session,
        full_name="No Active Version Candidate",
    )

    resume = build_resume(
        user.id
    )

    repository.create_resume(
        resume
    )

    version = build_version(
        resume.id,
        version_number=1,
        is_active=False,
    )

    repository.create_version(
        version
    )

    result = repository.get_active_version(
        resume.id
    )

    assert result is None


def test_get_active_version(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """The active resume version should be returned."""

    user = create_user(
        db_session,
        full_name="Active Version Candidate",
    )

    resume = build_resume(
        user.id
    )

    repository.create_resume(
        resume
    )

    version = build_version(
        resume.id,
        version_number=1,
        is_active=True,
        file_hash="c" * 64,
    )

    repository.create_version(
        version
    )

    active = repository.get_active_version(
        resume.id
    )

    assert active is not None
    assert active.id == version.id
    assert active.version_number == 1
    assert active.is_active is True


def test_get_version_by_hash(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """A version should be retrievable using its SHA-256 hash."""

    user = create_user(
        db_session,
        full_name="Hash Candidate",
    )

    resume = build_resume(
        user.id
    )

    repository.create_resume(
        resume
    )

    file_hash = "d" * 64

    version = build_version(
        resume.id,
        version_number=1,
        file_hash=file_hash,
    )

    repository.create_version(
        version
    )

    fetched = repository.get_version_by_hash(
        resume.id,
        file_hash,
    )

    assert fetched is not None
    assert fetched.id == version.id
    assert fetched.file_hash == file_hash


def test_get_version_by_hash_returns_none_when_missing(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """An unknown hash should return None."""

    user = create_user(
        db_session,
        full_name="Missing Hash Candidate",
    )

    resume = build_resume(
        user.id
    )

    repository.create_resume(
        resume
    )

    version = build_version(
        resume.id,
        version_number=1,
        file_hash="e" * 64,
    )

    repository.create_version(
        version
    )

    result = repository.get_version_by_hash(
        resume.id,
        "f" * 64,
    )

    assert result is None


def test_list_versions(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """All versions should be returned in ascending version order."""

    user = create_user(
        db_session,
        full_name="Version List Candidate",
    )

    resume = build_resume(
        user.id
    )

    repository.create_resume(
        resume
    )

    version_one = build_version(
        resume.id,
        version_number=1,
        filename="resume_v1.pdf",
        storage_path="resumes/test/v1.pdf",
        file_hash="1" * 64,
    )

    version_two = build_version(
        resume.id,
        version_number=2,
        filename="resume_v2.pdf",
        storage_path="resumes/test/v2.pdf",
        file_hash="2" * 64,
    )

    version_three = build_version(
        resume.id,
        version_number=3,
        filename="resume_v3.pdf",
        storage_path="resumes/test/v3.pdf",
        file_hash="3" * 64,
    )

    repository.create_version(
        version_two
    )

    repository.create_version(
        version_one
    )

    repository.create_version(
        version_three
    )

    versions = repository.list_versions(
        resume.id
    )

    assert len(versions) == 3

    assert [
        version.version_number
        for version in versions
    ] == [1, 2, 3]


def test_list_versions_isolated_by_resume(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """Versions belonging to another resume must not appear."""

    user = create_user(
        db_session,
        full_name="Isolation Candidate",
    )

    first_resume = build_resume(
        user.id,
        name="First Resume",
    )

    second_resume = build_resume(
        user.id,
        name="Second Resume",
    )

    repository.create_resume(
        first_resume
    )

    repository.create_resume(
        second_resume
    )

    first_version = build_version(
        first_resume.id,
        version_number=1,
        file_hash="4" * 64,
    )

    second_version = build_version(
        second_resume.id,
        version_number=1,
        file_hash="5" * 64,
    )

    repository.create_version(
        first_version
    )

    repository.create_version(
        second_version
    )

    versions = repository.list_versions(
        first_resume.id
    )

    assert len(versions) == 1
    assert versions[0].id == first_version.id
    assert versions[0].resume_id == first_resume.id


# ----------------------------------------------------------------------
# Activation tests
# ----------------------------------------------------------------------


def test_activate_version(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """Activating a version should make it the active version."""

    user = create_user(
        db_session,
        full_name="Activation Candidate",
    )

    resume = build_resume(
        user.id
    )

    repository.create_resume(
        resume
    )

    version = build_version(
        resume.id,
        version_number=1,
        is_active=False,
        file_hash="6" * 64,
    )

    repository.create_version(
        version
    )

    activated = repository.activate_version(
        version.id
    )

    assert activated.id == version.id
    assert activated.is_active is True

    active = repository.get_active_version(
        resume.id
    )

    assert active is not None
    assert active.id == version.id
    assert active.is_active is True


def test_activate_new_version_deactivates_previous_version(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """Only one version should remain active after activation."""

    user = create_user(
        db_session,
        full_name="Version Switch Candidate",
    )

    resume = build_resume(
        user.id
    )

    repository.create_resume(
        resume
    )

    first = build_version(
        resume.id,
        version_number=1,
        is_active=True,
        file_hash="7" * 64,
    )

    second = build_version(
        resume.id,
        version_number=2,
        is_active=False,
        file_hash="8" * 64,
    )

    repository.create_version(
        first
    )

    repository.create_version(
        second
    )

    activated = repository.activate_version(
        second.id
    )

    assert activated.id == second.id
    assert activated.is_active is True

    first_fetched = repository.get_version_by_id(
        first.id
    )

    second_fetched = repository.get_version_by_id(
        second.id
    )

    assert first_fetched is not None
    assert second_fetched is not None

    assert first_fetched.is_active is False
    assert second_fetched.is_active is True

    active = repository.get_active_version(
        resume.id
    )

    assert active is not None
    assert active.id == second.id


def test_activate_missing_version_raises(
    repository: SQLAlchemyResumeRepository,
) -> None:
    """Activating an unknown version should raise ValueError."""

    with pytest.raises(
        ValueError,
        match="Resume version",
    ):
        repository.activate_version(
            uuid4()
        )


# ----------------------------------------------------------------------
# Archive tests
# ----------------------------------------------------------------------


def test_archive_resume(
    repository: SQLAlchemyResumeRepository,
    db_session: Session,
) -> None:
    """Archiving should change the resume lifecycle status."""

    user = create_user(
        db_session,
        full_name="Archive Candidate",
    )

    resume = build_resume(
        user.id,
        name="Resume To Archive",
    )

    repository.create_resume(
        resume
    )

    archived = repository.archive_resume(
        resume.id
    )

    assert archived.id == resume.id
    assert archived.status == ResumeStatus.ARCHIVED

    fetched = repository.get_resume_by_id(
        resume.id
    )

    assert fetched is not None
    assert fetched.status == ResumeStatus.ARCHIVED


def test_archive_missing_resume_raises(
    repository: SQLAlchemyResumeRepository,
) -> None:
    """Archiving an unknown resume should raise ValueError."""

    with pytest.raises(
        ValueError,
        match="Resume",
    ):
        repository.archive_resume(
            uuid4()
        )


# ----------------------------------------------------------------------
# Contract test
# ----------------------------------------------------------------------


def test_repository_implements_domain_contract(
    repository: SQLAlchemyResumeRepository,
) -> None:
    """The SQLAlchemy implementation must satisfy the domain contract."""

    assert isinstance(
        repository,
        ResumeRepository,
    )