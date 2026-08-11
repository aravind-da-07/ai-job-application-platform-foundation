"""
Integration test for automatic resume-folder ingestion.

Uses:
- Real Supabase PostgreSQL
- Temporary local resume folder
- ResumeService
- ResumeIngestionService
- EventBus

Tests:
1. Create test user.
2. Create logical resume.
3. Create temporary resume folder.
4. Add first resume.
5. Scan folder.
6. Verify Version 1.
7. Scan again without changes.
8. Verify no duplicate version is created.
9. Modify resume.
10. Scan again.
11. Verify Version 2.
12. Verify RESUME_UPLOADED events.
13. Clean up.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from src.modules.resumes.infrastructure.repositories.resume_repository_impl import (
    SQLAlchemyResumeRepository,
)
from src.modules.resumes.services.resume_ingestion_service import (
    ResumeIngestionService,
)
from src.modules.resumes.services.resume_service import ResumeService
from src.modules.users.domain.entities.user import User
from src.modules.users.infrastructure.models.user_model import UserModel
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.shared.config.constants import EventType
from src.shared.database.session import session_scope
from src.shared.events.event_bus import EventBus


def main() -> None:
    print("=" * 70)
    print("RESUME INGESTION INTEGRATION TEST")
    print("=" * 70)

    test_user_id = None
    temp_directory: Path | None = None

    with session_scope() as session:
        user_repository = SQLAlchemyUserRepository(session)
        resume_repository = SQLAlchemyResumeRepository(session)

        resume_service = ResumeService(
            resume_repository
        )

        event_bus = EventBus()

        received_events: list[dict] = []

        def handle_resume_uploaded(event) -> None:
            received_events.append(event.payload)

        event_bus.subscribe(
            EventType.RESUME_UPLOADED,
            handle_resume_uploaded,
        )

        # --------------------------------------------------------------
        # 1. Create test user
        # --------------------------------------------------------------

        print("\n[1/13] Creating test user...")

        user = User(
            full_name="Resume Ingestion Test User",
            email=(
                f"resume-ingestion-test-"
                f"{uuid.uuid4().hex[:12]}"
                "@example.com"
            ),
        )

        created_user = user_repository.create(user)
        test_user_id = created_user.id

        print("CREATE USER successful")
        print(f"User ID: {created_user.id}")

        # --------------------------------------------------------------
        # 2. Create logical resume
        # --------------------------------------------------------------

        print("\n[2/13] Creating logical resume...")

        resume = resume_service.create_resume(
            user_id=created_user.id,
            name="Automatic Resume",
        )

        print("CREATE RESUME successful")
        print(f"Resume ID: {resume.id}")

        # --------------------------------------------------------------
        # 3. Create temporary folder
        # --------------------------------------------------------------

        print("\n[3/13] Creating temporary resume folder...")

        temp_directory = Path(
            tempfile.mkdtemp(
                prefix="resume_ingestion_test_"
            )
        )

        print(f"Folder: {temp_directory}")

        # --------------------------------------------------------------
        # 4. Create first resume
        # --------------------------------------------------------------

        print("\n[4/13] Creating first resume file...")

        resume_file = temp_directory / "resume.pdf"

        resume_file.write_bytes(
            b"Resume Version 1 - "
            b"Data Analyst - Excel SQL Python"
        )

        print(f"File: {resume_file}")

        # --------------------------------------------------------------
        # 5. First scan
        # --------------------------------------------------------------

        print("\n[5/13] Running first folder scan...")

        ingestion_service = ResumeIngestionService(
            resume_service=resume_service,
            event_bus=event_bus,
            resume_folder=temp_directory,
            user_id=created_user.id,
            resume_id=resume.id,
        )

        processed = ingestion_service.scan()

        assert processed == 1

        print("FIRST SCAN successful")
        print(f"New versions processed: {processed}")

        # --------------------------------------------------------------
        # 6. Verify Version 1
        # --------------------------------------------------------------

        print("\n[6/13] Verifying Version 1...")

        versions = resume_service.list_versions(
            resume.id
        )

        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].is_active is True

        print("VERSION 1 successful")
        print(f"Active: {versions[0].is_active}")

        # --------------------------------------------------------------
        # 7. Scan without changes
        # --------------------------------------------------------------

        print("\n[7/13] Running second scan without changes...")

        processed = ingestion_service.scan()

        assert processed == 0

        versions = resume_service.list_versions(
            resume.id
        )

        assert len(versions) == 1

        print("UNCHANGED FILE correctly ignored")
        print("New versions processed: 0")

        # --------------------------------------------------------------
        # 8. Verify event
        # --------------------------------------------------------------

        print("\n[8/13] Verifying RESUME_UPLOADED event...")

        assert len(received_events) == 1

        first_event = received_events[0]

        assert first_event["resume_id"] == str(resume.id)
        assert first_event["version_number"] == 1

        print("EVENT successful")
        print("Event: RESUME_UPLOADED")
        print("Version: 1")

        # --------------------------------------------------------------
        # 9. Modify resume
        # --------------------------------------------------------------

        print("\n[9/13] Modifying resume file...")

        resume_file.write_bytes(
            b"Resume Version 2 - "
            b"Data Analyst - Excel SQL Python Power BI"
        )

        # --------------------------------------------------------------
        # 10. Scan modified file
        # --------------------------------------------------------------

        print("\n[10/13] Scanning modified resume...")

        processed = ingestion_service.scan()

        assert processed == 1

        print("MODIFIED FILE detected")
        print(f"New versions processed: {processed}")

        # --------------------------------------------------------------
        # 11. Verify Version 2
        # --------------------------------------------------------------

        print("\n[11/13] Verifying Version 2...")

        versions = resume_service.list_versions(
            resume.id
        )

        assert len(versions) == 2

        version_1 = next(
            version
            for version in versions
            if version.version_number == 1
        )

        version_2 = next(
            version
            for version in versions
            if version.version_number == 2
        )

        assert version_1.is_active is False
        assert version_2.is_active is True

        print("VERSION 2 successful")
        print("Version 1: inactive")
        print("Version 2: active")

        # --------------------------------------------------------------
        # 12. Verify second event
        # --------------------------------------------------------------

        print("\n[12/13] Verifying second event...")

        assert len(received_events) == 2
        assert received_events[1]["version_number"] == 2

        print("SECOND EVENT successful")
        print("Total RESUME_UPLOADED events: 2")

        # --------------------------------------------------------------
        # 13. Cleanup
        # --------------------------------------------------------------

        print("\n[13/13] Cleaning up...")

        test_user_model = session.get(
            UserModel,
            test_user_id,
        )

        if test_user_model is None:
            raise RuntimeError(
                "Test user could not be found during cleanup."
            )

        session.delete(test_user_model)
        session.flush()

        if temp_directory is not None:
            for file in temp_directory.iterdir():
                file.unlink()

            temp_directory.rmdir()

        print("Cleanup successful")

    print("\n" + "=" * 70)
    print("✅ RESUME INGESTION INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()