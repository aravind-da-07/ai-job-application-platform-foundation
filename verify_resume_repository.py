"""
Integration test for the ResumeRepository.

This test uses the real Supabase PostgreSQL database and verifies:

1. Create a logical resume.
2. Create Version 1.
3. Activate Version 1.
4. Create Version 2.
5. Activate Version 2.
6. Verify Version 1 becomes inactive.
7. Verify Version 2 becomes active.
8. Verify both versions remain in history.
9. Verify duplicate file-hash protection.
10. Clean up all test records.
"""

from __future__ import annotations

import hashlib
import uuid

from src.modules.resumes.domain.entities.resume import (
    Resume,
    ResumeVersion,
)
from src.modules.resumes.infrastructure.repositories.resume_repository_impl import (
    SQLAlchemyResumeRepository,
)
from src.modules.users.domain.entities.user import User
from src.modules.users.infrastructure.models.user_model import UserModel
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.shared.database.session import session_scope


def make_hash(content: str) -> str:
    """Create a deterministic SHA-256 hash for test data."""

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def main() -> None:
    print("=" * 70)
    print("RESUME REPOSITORY INTEGRATION TEST")
    print("=" * 70)

    test_user_id = None

    with session_scope() as session:
        user_repository = SQLAlchemyUserRepository(session)
        resume_repository = SQLAlchemyResumeRepository(session)

        # --------------------------------------------------------------
        # 1. Create test user
        # --------------------------------------------------------------

        print("\n[1/10] Creating test user...")

        test_email = (
            f"resume-test-{uuid.uuid4().hex[:12]}"
            "@example.com"
        )

        user = User(
            full_name="Resume Repository Test User",
            email=test_email,
        )

        created_user = user_repository.create(user)
        test_user_id = created_user.id

        print("CREATE USER successful")
        print(f"User ID: {created_user.id}")
        print(f"Email: {created_user.email}")

        # --------------------------------------------------------------
        # 2. Create logical resume
        # --------------------------------------------------------------

        print("\n[2/10] Creating logical resume...")

        resume = Resume(
            user_id=created_user.id,
            name="Primary Resume",
        )

        created_resume = resume_repository.create_resume(resume)

        print("CREATE RESUME successful")
        print(f"Resume ID: {created_resume.id}")
        print(f"Resume name: {created_resume.name}")

        # --------------------------------------------------------------
        # 3. Create Version 1
        # --------------------------------------------------------------

        print("\n[3/10] Creating resume Version 1...")

        version_1 = ResumeVersion(
            resume_id=created_resume.id,
            version_number=1,
            filename="resume_v1.pdf",
            file_extension=".pdf",
            storage_path="resumes/test/resume_v1.pdf",
            file_hash=make_hash("resume version one"),
            file_size_bytes=1024,
            is_active=False,
        )

        created_version_1 = resume_repository.create_version(
            version_1
        )

        print("CREATE VERSION 1 successful")
        print(f"Version ID: {created_version_1.id}")

        # --------------------------------------------------------------
        # 4. Activate Version 1
        # --------------------------------------------------------------

        print("\n[4/10] Activating Version 1...")

        active_version_1 = resume_repository.activate_version(
            created_version_1.id
        )

        print("ACTIVATE VERSION 1 successful")
        print(f"Active: {active_version_1.is_active}")

        assert active_version_1.is_active is True

        # --------------------------------------------------------------
        # 5. Create Version 2
        # --------------------------------------------------------------

        print("\n[5/10] Creating resume Version 2...")

        version_2 = ResumeVersion(
            resume_id=created_resume.id,
            version_number=2,
            filename="resume_v2.pdf",
            file_extension=".pdf",
            storage_path="resumes/test/resume_v2.pdf",
            file_hash=make_hash("resume version two"),
            file_size_bytes=2048,
            is_active=False,
        )

        created_version_2 = resume_repository.create_version(
            version_2
        )

        print("CREATE VERSION 2 successful")
        print(f"Version ID: {created_version_2.id}")

        # --------------------------------------------------------------
        # 6. Activate Version 2
        # --------------------------------------------------------------

        print("\n[6/10] Activating Version 2...")

        active_version_2 = resume_repository.activate_version(
            created_version_2.id
        )

        print("ACTIVATE VERSION 2 successful")
        print(f"Active: {active_version_2.is_active}")

        assert active_version_2.is_active is True

        # --------------------------------------------------------------
        # 7. Verify Version 1 became inactive
        # --------------------------------------------------------------

        print("\n[7/10] Verifying Version 1 is inactive...")

        refreshed_version_1 = resume_repository.get_version_by_id(
            created_version_1.id
        )

        assert refreshed_version_1 is not None
        assert refreshed_version_1.is_active is False

        print("VERSION SWITCH successful")
        print("Version 1: inactive")
        print("Version 2: active")

        # --------------------------------------------------------------
        # 8. Verify version history
        # --------------------------------------------------------------

        print("\n[8/10] Verifying version history...")

        versions = resume_repository.list_versions(
            created_resume.id
        )

        assert len(versions) == 2

        print("VERSION HISTORY successful")
        print(f"Total versions: {len(versions)}")

        for version in versions:
            print(
                f"- Version {version.version_number}: "
                f"{version.filename}, "
                f"active={version.is_active}"
            )

        # --------------------------------------------------------------
        # 9. Verify duplicate hash protection
        # --------------------------------------------------------------

        print("\n[9/10] Testing duplicate file-hash protection...")

        duplicate_detected = (
            resume_repository.get_version_by_hash(
                created_resume.id,
                created_version_2.file_hash,
            )
        )

        assert duplicate_detected is not None
        assert duplicate_detected.id == created_version_2.id

        print("DUPLICATE HASH DETECTION successful")
        print(
            f"Existing version: "
            f"{duplicate_detected.version_number}"
        )

        # --------------------------------------------------------------
        # 10. Verify active version
        # --------------------------------------------------------------

        print("\n[10/10] Verifying active version...")

        current_active = resume_repository.get_active_version(
            created_resume.id
        )

        assert current_active is not None
        assert current_active.id == created_version_2.id
        assert current_active.is_active is True

        print("ACTIVE VERSION lookup successful")
        print(
            f"Current active version: "
            f"{current_active.version_number}"
        )

        # --------------------------------------------------------------
        # Cleanup
        # --------------------------------------------------------------

        print("\nCleaning up test data...")

        # We must delete the SQLAlchemy ORM model, not the
        # Pydantic domain entity returned by UserRepository.
        #
        # Database CASCADE rules then remove:
        #
        # User
        #   └── Resume
        #         └── Resume Versions

        test_user_model = session.get(
            UserModel,
            test_user_id,
        )

        if test_user_model is None:
            raise RuntimeError(
                f"Test user '{test_user_id}' "
                "could not be found during cleanup."
            )

        session.delete(test_user_model)
        session.flush()

        print("Cleanup successful")

    print("\n" + "=" * 70)
    print("✅ RESUME REPOSITORY INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()