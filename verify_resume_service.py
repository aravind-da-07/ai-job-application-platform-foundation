"""
Integration test for ResumeService.

Uses the real Supabase PostgreSQL database and a temporary local
resume file to verify the complete resume-version workflow.

Tests:
1. Create a test user.
2. Create a logical resume.
3. Add the first resume file.
4. Verify Version 1 becomes active.
5. Add a changed resume file.
6. Verify Version 2 becomes active.
7. Verify Version 1 remains in history.
8. Verify duplicate file detection.
9. Clean up database records and temporary files.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from src.modules.resumes.domain.entities.resume import Resume
from src.modules.resumes.infrastructure.repositories.resume_repository_impl import (
    SQLAlchemyResumeRepository,
)
from src.modules.resumes.services.resume_service import ResumeService
from src.modules.users.domain.entities.user import User
from src.modules.users.infrastructure.models.user_model import UserModel
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.shared.database.session import session_scope


def main() -> None:
    print("=" * 70)
    print("RESUME SERVICE INTEGRATION TEST")
    print("=" * 70)

    test_user_id = None
    temp_directory: Path | None = None

    with session_scope() as session:
        user_repository = SQLAlchemyUserRepository(session)
        resume_repository = SQLAlchemyResumeRepository(session)
        resume_service = ResumeService(resume_repository)

        # --------------------------------------------------------------
        # 1. Create test user
        # --------------------------------------------------------------

        print("\n[1/9] Creating test user...")

        test_email = (
            f"resume-service-test-{uuid.uuid4().hex[:12]}"
            "@example.com"
        )

        user = User(
            full_name="Resume Service Test User",
            email=test_email,
        )

        created_user = user_repository.create(user)
        test_user_id = created_user.id

        print("CREATE USER successful")
        print(f"User ID: {created_user.id}")

        # --------------------------------------------------------------
        # 2. Create logical resume
        # --------------------------------------------------------------

        print("\n[2/9] Creating logical resume...")

        resume = resume_service.create_resume(
            user_id=created_user.id,
            name="Automated Resume",
        )

        print("CREATE RESUME successful")
        print(f"Resume ID: {resume.id}")

        # --------------------------------------------------------------
        # 3. Create temporary resume file
        # --------------------------------------------------------------

        print("\n[3/9] Creating temporary resume file...")

        temp_directory = Path(
            tempfile.mkdtemp(prefix="resume_service_test_")
        )

        resume_file = temp_directory / "resume.pdf"

        resume_file.write_bytes(
            b"Resume Version 1 - "
            b"Associate Data Analyst - Excel SQL Python"
        )

        print(f"Test file: {resume_file}")
        print(f"File size: {resume_file.stat().st_size} bytes")

        # --------------------------------------------------------------
        # 4. Add Version 1
        # --------------------------------------------------------------

        print("\n[4/9] Adding Resume Version 1...")

        version_1 = resume_service.add_resume_version(
            resume_id=resume.id,
            file_path=resume_file,
            storage_path="resumes/test/resume_v1.pdf",
        )

        assert version_1.version_number == 1
        assert version_1.is_active is True

        print("VERSION 1 successful")
        print(f"Version: {version_1.version_number}")
        print(f"Hash: {version_1.file_hash}")
        print(f"Active: {version_1.is_active}")

        # --------------------------------------------------------------
        # 5. Modify the same resume file
        # --------------------------------------------------------------

        print("\n[5/9] Updating resume file...")

        resume_file.write_bytes(
            b"Resume Version 2 - "
            b"Associate Data Analyst - Excel SQL Python Power BI"
        )

        version_2 = resume_service.add_resume_version(
            resume_id=resume.id,
            file_path=resume_file,
            storage_path="resumes/test/resume_v2.pdf",
        )

        assert version_2.version_number == 2
        assert version_2.is_active is True

        print("VERSION 2 successful")
        print(f"Version: {version_2.version_number}")
        print(f"Hash: {version_2.file_hash}")
        print(f"Active: {version_2.is_active}")

        # --------------------------------------------------------------
        # 6. Verify active-version switching
        # --------------------------------------------------------------

        print("\n[6/9] Verifying active-version switching...")

        active_version = resume_service.get_active_version(
            resume.id
        )

        assert active_version is not None
        assert active_version.id == version_2.id
        assert active_version.is_active is True

        print("ACTIVE VERSION successful")
        print(f"Current active version: {active_version.version_number}")

        # --------------------------------------------------------------
        # 7. Verify historical versions
        # --------------------------------------------------------------

        print("\n[7/9] Verifying version history...")

        versions = resume_service.list_versions(resume.id)

        assert len(versions) == 2

        version_1_from_db = next(
            version
            for version in versions
            if version.version_number == 1
        )

        version_2_from_db = next(
            version
            for version in versions
            if version.version_number == 2
        )

        assert version_1_from_db.is_active is False
        assert version_2_from_db.is_active is True

        print("VERSION HISTORY successful")
        print(f"Total versions: {len(versions)}")
        print(
            f"Version 1 active: {version_1_from_db.is_active}"
        )
        print(
            f"Version 2 active: {version_2_from_db.is_active}"
        )

        # --------------------------------------------------------------
        # 8. Verify duplicate detection
        # --------------------------------------------------------------

        print("\n[8/9] Testing duplicate resume detection...")

        try:
            resume_service.add_resume_version(
                resume_id=resume.id,
                file_path=resume_file,
                storage_path="resumes/test/duplicate.pdf",
            )
        except ValueError as exc:
            assert "already exists" in str(exc)

            print("DUPLICATE DETECTION successful")
            print(f"Expected error: {exc}")
        else:
            raise AssertionError(
                "Duplicate resume file was accepted unexpectedly."
            )

        # --------------------------------------------------------------
        # 9. Cleanup
        # --------------------------------------------------------------

        print("\n[9/9] Cleaning up test data...")

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

        if temp_directory is not None:
            for file in temp_directory.iterdir():
                file.unlink()

            temp_directory.rmdir()

        print("Cleanup successful")

    print("\n" + "=" * 70)
    print("✅ RESUME SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()