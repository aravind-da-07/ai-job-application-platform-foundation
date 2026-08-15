"""
JOB REPOSITORY INTEGRATION TEST

Tests the SQLAlchemy JobRepository implementation against
the real Supabase PostgreSQL database.

This test creates temporary records and cleans them up.
"""

from __future__ import annotations

import uuid

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.infrastructure.repositories.job.job_repository_impl import (
    SQLAlchemyJobRepository,
)
from src.shared.config.constants import (
    EmploymentType,
    JobSourceType,
    RemoteStatus,
)
from src.shared.database.session import session_scope


def main() -> None:
    print("=" * 70)
    print("JOB REPOSITORY SUPABASE INTEGRATION TEST")
    print("=" * 70)

    created_job_ids: list[uuid.UUID] = []

    with session_scope() as session:
        repository = SQLAlchemyJobRepository(session)

        # --------------------------------------------------------------
        # 1. Create test job
        # --------------------------------------------------------------

        print("\n[1/10] Creating test job...")

        external_job_id = (
            f"repository-test-{uuid.uuid4().hex[:12]}"
        )

        job = DiscoveredJob(
            external_id=external_job_id,
            title="Data Analyst - Integration Test",
            company_name="AI Platform Test Company",
            source=JobSourceType.LINKEDIN,
            url=(
                "https://example.com/"
                f"jobs/{external_job_id}"
            ),
            location="Hyderabad",
            remote_status=RemoteStatus.REMOTE,
            employment_type=EmploymentType.FULL_TIME,
            description=(
                "Temporary integration-test job."
            ),
            posted_at="2026-08-12T10:00:00+00:00",
            salary_min=600000,
            salary_max=900000,
            salary_currency="INR",
            metadata={
                "test": True,
                "source_test": "job_repository",
            },
        )

        created = repository.create(job)

        created_job = repository.get_by_external_id(
            source=JobSourceType.LINKEDIN,
            external_job_id=external_job_id,
        )

        assert created_job is not None

        # The repository returns a domain object rather than
        # exposing SQLAlchemy internals.
        print("CREATE successful")
        print(f"External Job ID: {created.external_id}")
        print(f"Title: {created.title}")
        print(f"Company: {created.company_name}")

        # --------------------------------------------------------------
        # 2. Get by UUID
        # --------------------------------------------------------------

        print("\n[2/10] Testing get_by_id...")

        # Locate the internal ID through the ORM-backed repository.
        # We deliberately use the database model only for obtaining
        # the generated UUID for this integration test.
        from sqlalchemy import select

        from src.modules.job_discovery.infrastructure.models.job_model import (
            JobModel,
        )

        model = session.scalar(
            select(JobModel).where(
                JobModel.external_job_id
                == external_job_id,
                JobModel.source
                == JobSourceType.LINKEDIN,
            )
        )

        assert model is not None

        job_id = model.id
        created_job_ids.append(job_id)

        fetched = repository.get_by_id(job_id)

        assert fetched is not None
        assert fetched.external_id == external_job_id

        print("GET BY ID successful")
        print(f"Job ID: {job_id}")
        print(f"External Job ID: {fetched.external_id}")

        # --------------------------------------------------------------
        # 3. Get by external ID
        # --------------------------------------------------------------

        print("\n[3/10] Testing get_by_external_id...")

        fetched_external = repository.get_by_external_id(
            source=JobSourceType.LINKEDIN,
            external_job_id=external_job_id,
        )

        assert fetched_external is not None
        assert fetched_external.title == (
            "Data Analyst - Integration Test"
        )

        print("EXTERNAL ID lookup successful")
        print(f"Source: {fetched_external.source}")
        print(f"Title: {fetched_external.title}")

        # --------------------------------------------------------------
        # 4. Test duplicate protection
        # --------------------------------------------------------------

        print("\n[4/10] Testing duplicate protection...")

        duplicate_rejected = False

        try:
            repository.create(job)
        except ValueError as exc:
            duplicate_rejected = True
            print("DUPLICATE protection successful")
            print(f"Reason: {exc}")

        assert duplicate_rejected is True

        # --------------------------------------------------------------
        # 5. Test upsert/update
        # --------------------------------------------------------------

        print("\n[5/10] Testing upsert update...")

        updated_job = DiscoveredJob(
            external_id=external_job_id,
            title="Senior Data Analyst - Updated",
            company_name="AI Platform Test Company",
            source=JobSourceType.LINKEDIN,
            url=job.url,
            location="Hyderabad",
            remote_status=RemoteStatus.REMOTE,
            employment_type=EmploymentType.FULL_TIME,
            description=(
                "Updated integration-test description."
            ),
            posted_at="2026-08-12T11:00:00+00:00",
            salary_min=700000,
            salary_max=1000000,
            salary_currency="INR",
            metadata={
                "test": True,
                "updated": True,
            },
        )

        upserted = repository.upsert(updated_job)

        assert upserted.title == (
            "Senior Data Analyst - Updated"
        )

        verified = repository.get_by_id(job_id)

        assert verified is not None
        assert verified.title == (
            "Senior Data Analyst - Updated"
        )

        print("UPSERT successful")
        print(f"Updated title: {verified.title}")
        print(f"Salary max: {verified.salary_max}")

        # --------------------------------------------------------------
        # 6. Test list_active
        # --------------------------------------------------------------

        print("\n[6/10] Testing list_active...")

        active_jobs = repository.list_active(
            source=JobSourceType.LINKEDIN,
            limit=100,
        )

        assert any(
            item.external_id == external_job_id
            for item in active_jobs
        )

        print("LIST ACTIVE successful")
        print(f"Active LinkedIn jobs returned: {len(active_jobs)}")

        # --------------------------------------------------------------
        # 7. Test count_active
        # --------------------------------------------------------------

        print("\n[7/10] Testing count_active...")

        active_count = repository.count_active(
            source=JobSourceType.LINKEDIN,
        )

        assert active_count >= 1

        print("COUNT ACTIVE successful")
        print(f"Active LinkedIn jobs: {active_count}")

        # --------------------------------------------------------------
        # 8. Test deactivate
        # --------------------------------------------------------------

        print("\n[8/10] Testing deactivate...")

        repository.deactivate(job_id)

        deactivated = repository.get_by_id(job_id)

        assert deactivated is not None

        active_after_deactivation = repository.list_active(
            source=JobSourceType.LINKEDIN,
            limit=100,
        )

        assert not any(
            item.external_id == external_job_id
            for item in active_after_deactivation
        )

        print("DEACTIVATE successful")
        print("Job no longer appears in active jobs")

        # --------------------------------------------------------------
        # 9. Verify database persistence
        # --------------------------------------------------------------

        print("\n[9/10] Verifying Supabase persistence...")

        persisted_model = session.get(
            JobModel,
            job_id,
        )

        assert persisted_model is not None
        assert persisted_model.is_active is False
        assert persisted_model.title == (
            "Senior Data Analyst - Updated"
        )

        print("SUPABASE persistence successful")
        print(f"Database Job ID: {persisted_model.id}")
        print(f"Database status: inactive")

        # --------------------------------------------------------------
        # 10. Cleanup
        # --------------------------------------------------------------

        print("\n[10/10] Cleaning up test data...")

        for created_id in created_job_ids:
            model = session.get(
                JobModel,
                created_id,
            )

            if model is not None:
                session.delete(model)

        session.flush()

        remaining = session.get(
            JobModel,
            job_id,
        )

        assert remaining is None

        print("CLEANUP successful")
        print("Test job removed from Supabase")

    print("\n" + "=" * 70)
    print("JOB REPOSITORY INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()