"""
SQLAlchemy implementation of JobMatchRepository.

Persists transparent job-matching results in PostgreSQL/Supabase.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.job_discovery.domain.matching.job_matching import (
    JobMatchBreakdown,
    JobMatchResult,
)
from src.modules.job_discovery.domain.repositories.job.job_match_repository import (
    JobMatchRepository,
)
from src.modules.job_discovery.infrastructure.models.job_model import (
    JobMatchModel,
    JobModel,
)


class SQLAlchemyJobMatchRepository(JobMatchRepository):
    """
    SQLAlchemy/PostgreSQL implementation of JobMatchRepository.

    The repository translates between:
        - domain JobMatchResult objects
        - SQLAlchemy JobMatchModel records

    Job metadata such as external_job_id is resolved through
    the related JobModel.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        resume_id: UUID | None,
        result: JobMatchResult,
    ) -> UUID:
        """
        Persist a new job-match result.

        Duplicate protection is performed before insertion.
        """

        existing = self.get_for_job(
            job_id=job_id,
            user_id=user_id,
            resume_id=resume_id,
        )

        if existing is not None:
            raise ValueError(
                "A job match already exists for this "
                "job/user/resume combination."
            )

        breakdown = result.breakdown

        model = JobMatchModel(
            job_id=job_id,
            user_id=user_id,
            resume_id=resume_id,
            overall_score=result.overall_score,
            decision=result.decision,
            reason=result.reason,
            title_score=breakdown.title_score,
            skill_score=breakdown.skill_score,
            location_score=breakdown.location_score,
            remote_score=breakdown.remote_score,
            experience_score=breakdown.experience_score,
            matched_skills=list(
                breakdown.matched_skills
            ),
            missing_required_skills=list(
                breakdown.missing_required_skills
            ),
            matched_roles=list(
                breakdown.matched_roles
            ),
            excluded_reasons=list(
                breakdown.excluded_reasons
            ),
            metadata_json={
                **breakdown.metadata,
                **result.metadata,
            },
        )

        self._session.add(model)
        self._session.flush()

        return model.id

    # ------------------------------------------------------------------
    # Get by ID
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        match_id: UUID,
    ) -> JobMatchResult | None:
        """
        Retrieve a persisted job-match result by match UUID.
        """

        statement = (
            select(JobMatchModel, JobModel)
            .join(
                JobModel,
                JobModel.id == JobMatchModel.job_id,
            )
            .where(
                JobMatchModel.id == match_id
            )
        )

        row = self._session.execute(statement).first()

        if row is None:
            return None

        match_model, job_model = row

        return self._to_domain(
            match_model,
            job_model,
        )

    # ------------------------------------------------------------------
    # Get for job
    # ------------------------------------------------------------------

    def get_for_job(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        resume_id: UUID | None = None,
    ) -> JobMatchResult | None:
        """
        Retrieve the persisted match for a
        job/user/resume combination.
        """

        statement = (
            select(JobMatchModel, JobModel)
            .join(
                JobModel,
                JobModel.id == JobMatchModel.job_id,
            )
            .where(
                JobMatchModel.job_id == job_id,
                JobMatchModel.user_id == user_id,
            )
        )

        if resume_id is None:
            statement = statement.where(
                JobMatchModel.resume_id.is_(None)
            )
        else:
            statement = statement.where(
                JobMatchModel.resume_id == resume_id
            )

        row = self._session.execute(statement).first()

        if row is None:
            return None

        match_model, job_model = row

        return self._to_domain(
            match_model,
            job_model,
        )

    # ------------------------------------------------------------------
    # List for user
    # ------------------------------------------------------------------

    def list_for_user(
        self,
        *,
        user_id: UUID,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[JobMatchResult]:
        """
        Retrieve persisted matching results for a user.
        """

        if limit < 1:
            raise ValueError(
                "limit must be greater than zero."
            )

        statement = (
            select(JobMatchModel, JobModel)
            .join(
                JobModel,
                JobModel.id == JobMatchModel.job_id,
            )
            .where(
                JobMatchModel.user_id == user_id
            )
            .order_by(
                JobMatchModel.created_at.desc()
            )
            .limit(limit)
        )

        if decision is not None:
            statement = statement.where(
                JobMatchModel.decision == decision
            )

        rows = self._session.execute(statement).all()

        return [
            self._to_domain(
                match_model,
                job_model,
            )
            for match_model, job_model in rows
        ]

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(
        model: JobMatchModel,
        job_model: JobModel,
    ) -> JobMatchResult:
        """
        Convert SQLAlchemy ORM models into a domain result.

        IMPORTANT:
        external_job_id comes from jobs.external_job_id,
        not from jobs.id.
        """

        breakdown = JobMatchBreakdown(
            title_score=float(
                model.title_score
            ),
            skill_score=float(
                model.skill_score
            ),
            location_score=float(
                model.location_score
            ),
            remote_score=float(
                model.remote_score
            ),
            experience_score=float(
                model.experience_score
            ),
            matched_skills=tuple(
                model.matched_skills or []
            ),
            missing_required_skills=tuple(
                model.missing_required_skills or []
            ),
            matched_roles=tuple(
                model.matched_roles or []
            ),
            excluded_reasons=tuple(
                model.excluded_reasons or []
            ),
            metadata=dict(
                model.metadata_json or {}
            ),
        )

        return JobMatchResult(
            external_job_id=job_model.external_job_id,
            overall_score=float(
                model.overall_score
            ),
            decision=model.decision,
            breakdown=breakdown,
            reason=model.reason,
            metadata=dict(
                model.metadata_json or {}
            ),
        )