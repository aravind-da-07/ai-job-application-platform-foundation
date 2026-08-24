import uuid

from src.shared.database.session import session_scope
from src.modules.job_discovery.infrastructure.models.job_model import JobModel
from src.shared.config.constants import JobSourceType


TEST_EXTERNAL_ID = "test-data-analyst-001"


with session_scope() as db:

    existing = (
        db.query(JobModel)
        .filter(
            JobModel.source == JobSourceType.LINKEDIN,
            JobModel.external_job_id == TEST_EXTERNAL_ID,
        )
        .first()
    )

    if existing:
        print("TEST JOB ALREADY EXISTS")
        print(f"id={existing.id}")
        print(f"title={existing.title}")
        print(f"company={existing.company_name}")
    else:
        job = JobModel(
            id=uuid.uuid4(),
            external_job_id=TEST_EXTERNAL_ID,
            source=JobSourceType.LINKEDIN,
            title="Data Analyst",
            company_name="Test Analytics Company",
            url="https://example.com/jobs/test-data-analyst-001",
            location="Hyderabad, Telangana, India",
            remote=True,
            employment_type="full_time",
            description=(
                "Test Data Analyst role for validating the "
                "application matching and queue pipeline."
            ),
            salary_min=600000,
            salary_max=900000,
            salary_currency="INR",
            is_active=True,
            metadata_json={
                "test_job": True,
                "created_for": "application_pipeline_test",
            },
        )

        db.add(job)
        db.flush()

        print("TEST JOB CREATED")
        print(f"id={job.id}")
        print(f"title={job.title}")
        print(f"company={job.company_name}")
        print(f"source={job.source}")
        print(f"external_job_id={job.external_job_id}")
