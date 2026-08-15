"""
JOB MATCH REPOSITORY SUPABASE INTEGRATION TEST

Verifies:

    1. Test user creation
    2. Test job creation
    3. Job match creation
    4. Match retrieval by ID
    5. Correct external_job_id mapping
    6. Job/user/resume lookup
    7. Duplicate protection
    8. Decision filtering
    9. Score and breakdown persistence
    10. Supabase PostgreSQL persistence and cleanup

Important:

JobMatchModel.resume_id references resumes.id.

ResumeModel and ResumeVersionModel are explicitly imported below so
SQLAlchemy registers the complete ORM dependency graph in Base.metadata
before a JobMatchModel is flushed.
"""

from __future__ import annotations

import uuid

from src.modules.job_discovery.domain.matching.job_matching import (
    JobMatchBreakdown,
    JobMatchResult,
)
from src.modules.job_discovery.infrastructure.models.job_model import (
    JobMatchModel,
    JobModel,
)

# ----------------------------------------------------------------------
# IMPORTANT ORM REGISTRATION
# ----------------------------------------------------------------------
# JobMatchModel.resume_id -> resumes.id.
#
# These imports ensure the resumes and resume_versions tables are
# registered in SQLAlchemy Base.metadata before the session flush.
# ----------------------------------------------------------------------

from src.modules.resumes.infrastructure.models.resume_model import (
    ResumeModel,
    ResumeVersionModel,
)

from src.modules.users.infrastructure.models.user_model import UserModel

from src.shared.config.constants import JobSourceType
from src.shared.database.session import session_scope


def main() -> None:
    print()
    print("=" * 70)
    print("JOB MATCH REPOSITORY SUPABASE INTEGRATION TEST")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Test identifiers
    # ------------------------------------------------------------------

    test_user_id = uuid.uuid4()
    test_job_id = uuid.uuid4()

    created_match_id = None

    external_job_id = (
        f"job-match-repository-test-{uuid.uuid4().hex[:12]}"
    )

    email = (
        f"job-match-test-{uuid.uuid4().hex[:12]}"
        "@example.com"
    )

    try:
        with session_scope() as session:

            # ==========================================================
            # 1. CREATE TEST USER
            # ==========================================================

            print()
            print("[1/10] Creating test user...")

            user = UserModel(
                id=test_user_id,
                full_name="Job Match Repository Test User",
                email=email,
                phone=None,
                auth_provider="local",
                is_active=True,
                email_verified=True,
            )

            session.add(user)
            session.flush()

            print("CREATE USER successful")
            print(f"User ID: {test_user_id}")

            # ==========================================================
            # 2. CREATE TEST JOB
            # ==========================================================

            print()
            print("[2/10] Creating test job...")

            job = JobModel(
                id=test_job_id,
                external_job_id=external_job_id,
                source=JobSourceType.LINKEDIN,
                title="Data Analyst - Match Repository Test",
                company_name="AI Job Platform Test Company",
                url="https://example.com/test-job",
                location="Hyderabad",
                remote=True,
                employment_type="full_time",
                description=(
                    "Test Data Analyst position requiring "
                    "SQL, Excel and Python."
                ),
                salary_min=600000,
                salary_max=1000000,
                salary_currency="INR",
                is_active=True,
                metadata_json={
                    "source_test": True,
                },
            )

            session.add(job)
            session.flush()

            print("CREATE JOB successful")
            print(f"Job ID: {job.id}")
            print(f"External Job ID: {job.external_job_id}")

            # ==========================================================
            # 3. CREATE JOB MATCH
            # ==========================================================

            print()
            print("[3/10] Creating job match...")

            result = JobMatchResult(
                external_job_id=external_job_id,
                overall_score=0.92,
                decision="apply",
                reason=(
                    "Strong match based on target role, "
                    "skills and location."
                ),
                breakdown=JobMatchBreakdown(
                    title_score=0.95,
                    skill_score=0.94,
                    location_score=0.90,
                    remote_score=0.88,
                    experience_score=0.85,
                    matched_skills=(
                        "SQL",
                        "Excel",
                        "Python",
                    ),
                    missing_required_skills=(),
                    matched_roles=(
                        "Data Analyst",
                    ),
                    excluded_reasons=(),
                    metadata={
                        "matching_engine": "integration_test",
                    },
                ),
                metadata={
                    "test": True,
                    "source": "job_match_repository_test",
                },
            )

            from src.modules.job_discovery.infrastructure.repositories.job.job_match_repository_impl import (
                SQLAlchemyJobMatchRepository,
            )

            repository = SQLAlchemyJobMatchRepository(
                session
            )

            created_match_id = repository.create(
                job_id=test_job_id,
                user_id=test_user_id,
                resume_id=None,
                result=result,
            )

            print("CREATE MATCH successful")
            print(f"Match ID: {created_match_id}")
            print("Decision: apply")
            print("Overall score: 92%")

            # ==========================================================
            # 4. GET BY ID
            # ==========================================================

            print()
            print("[4/10] Testing get_by_id...")

            retrieved = repository.get_by_id(
                created_match_id
            )

            assert retrieved is not None

            assert (
                retrieved.external_job_id
                == external_job_id
            )

            assert retrieved.decision == "apply"

            assert (
                abs(
                    retrieved.overall_score - 0.92
                )
                < 0.0001
            )

            print("GET BY ID successful")
            print(
                "External Job ID: "
                f"{retrieved.external_job_id}"
            )
            print(
                "Score: "
                f"{retrieved.overall_score:.0%}"
            )

            # ==========================================================
            # 5. VERIFY EXTERNAL JOB ID MAPPING
            # ==========================================================

            print()
            print(
                "[5/10] Testing external_job_id mapping..."
            )

            assert (
                retrieved.external_job_id
                == external_job_id
            )

            # Critical regression check:
            # external_job_id must NOT be the internal job UUID.

            assert (
                retrieved.external_job_id
                != str(test_job_id)
            )

            print(
                "EXTERNAL JOB ID mapping successful"
            )

            print(
                "Domain external_job_id correctly "
                "comes from jobs.external_job_id"
            )

            # ==========================================================
            # 6. GET FOR JOB
            # ==========================================================

            print()
            print(
                "[6/10] Testing get_for_job..."
            )

            lookup = repository.get_for_job(
                job_id=test_job_id,
                user_id=test_user_id,
                resume_id=None,
            )

            assert lookup is not None

            assert (
                lookup.external_job_id
                == external_job_id
            )

            assert lookup.decision == "apply"

            print("JOB MATCH LOOKUP successful")
            print(
                f"Decision: {lookup.decision}"
            )
            print(
                f"Score: {lookup.overall_score:.0%}"
            )

            # ==========================================================
            # 7. DUPLICATE PROTECTION
            # ==========================================================

            print()
            print(
                "[7/10] Testing duplicate protection..."
            )

            duplicate_blocked = False

            try:
                repository.create(
                    job_id=test_job_id,
                    user_id=test_user_id,
                    resume_id=None,
                    result=result,
                )

            except ValueError as exc:
                duplicate_blocked = True

                print(
                    f"Reason: {exc}"
                )

            assert duplicate_blocked

            print(
                "DUPLICATE protection successful"
            )

            # ==========================================================
            # 8. DECISION FILTERING
            # ==========================================================

            print()
            print(
                "[8/10] Testing decision filtering..."
            )

            apply_results = repository.list_for_user(
                user_id=test_user_id,
                decision="apply",
                limit=100,
            )

            skip_results = repository.list_for_user(
                user_id=test_user_id,
                decision="skip",
                limit=100,
            )

            assert len(apply_results) == 1
            assert len(skip_results) == 0

            print(
                "DECISION filtering successful"
            )

            print(
                f"Apply results: {len(apply_results)}"
            )

            print(
                f"Skip results: {len(skip_results)}"
            )

            # ==========================================================
            # 9. VERIFY COMPLETE BREAKDOWN
            # ==========================================================

            print()
            print(
                "[9/10] Verifying score and breakdown..."
            )

            assert (
                abs(
                    retrieved.breakdown.title_score
                    - 0.95
                )
                < 0.0001
            )

            assert (
                abs(
                    retrieved.breakdown.skill_score
                    - 0.94
                )
                < 0.0001
            )

            assert (
                abs(
                    retrieved.breakdown.location_score
                    - 0.90
                )
                < 0.0001
            )

            assert (
                abs(
                    retrieved.breakdown.remote_score
                    - 0.88
                )
                < 0.0001
            )

            assert (
                abs(
                    retrieved.breakdown.experience_score
                    - 0.85
                )
                < 0.0001
            )

            assert (
                retrieved.breakdown.matched_skills
                == (
                    "SQL",
                    "Excel",
                    "Python",
                )
            )

            assert (
                retrieved.breakdown.matched_roles
                == (
                    "Data Analyst",
                )
            )

            assert (
                retrieved.breakdown.missing_required_skills
                == ()
            )

            assert (
                retrieved.breakdown.excluded_reasons
                == ()
            )

            assert (
                retrieved.metadata["test"]
                is True
            )

            print(
                "BREAKDOWN persistence successful"
            )

            print("Title score: 95%")
            print("Skill score: 94%")
            print("Location score: 90%")
            print("Remote score: 88%")
            print("Experience score: 85%")

            print(
                "Matched skills: "
                f"{retrieved.breakdown.matched_skills}"
            )

            print(
                "Matched roles: "
                f"{retrieved.breakdown.matched_roles}"
            )

            # ==========================================================
            # 10. SUPABASE PERSISTENCE + CLEANUP
            # ==========================================================

            print()
            print(
                "[10/10] Verifying Supabase persistence "
                "and cleanup..."
            )

            persisted = session.get(
                JobMatchModel,
                created_match_id,
            )

            assert persisted is not None

            assert (
                persisted.job_id
                == test_job_id
            )

            assert (
                persisted.user_id
                == test_user_id
            )

            assert (
                float(
                    persisted.overall_score
                )
                == 0.92
            )

            assert (
                persisted.decision
                == "apply"
            )

            print(
                "SUPABASE persistence successful"
            )

            print(
                "Database Match ID: "
                f"{persisted.id}"
            )

            print(
                "Database Job ID: "
                f"{persisted.job_id}"
            )

            print(
                "Database Decision: "
                f"{persisted.decision}"
            )

            # ----------------------------------------------------------
            # Cleanup
            # ----------------------------------------------------------
            #
            # JobMatch references Job, so delete match first.
            # User/job are then removed explicitly.
            # ----------------------------------------------------------

            session.delete(persisted)
            session.flush()

            session.delete(job)
            session.delete(user)

            session.flush()

            remaining_match = session.get(
                JobMatchModel,
                created_match_id,
            )

            remaining_job = session.get(
                JobModel,
                test_job_id,
            )

            remaining_user = session.get(
                UserModel,
                test_user_id,
            )

            assert remaining_match is None
            assert remaining_job is None
            assert remaining_user is None

            print(
                "CLEANUP successful"
            )

        # ==============================================================
        # FINAL RESULT
        # ==============================================================

        print()
        print("=" * 70)
        print(
            "JOB MATCH REPOSITORY INTEGRATION TEST PASSED"
        )
        print("=" * 70)
        print()

    except Exception:
        print()
        print("=" * 70)
        print(
            "JOB MATCH REPOSITORY INTEGRATION TEST FAILED"
        )
        print("=" * 70)
        print()
        raise


if __name__ == "__main__":
    main()