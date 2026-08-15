"""
SQLAlchemy implementation of JobRepository.

This repository persists normalized discovered jobs in PostgreSQL/Supabase.
Domain logic remains in the domain layer.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.domain.repositories.job.job_repository import (
    JobRepository,
)
from src.modules.job_discovery.infrastructure.models.job_model import (
    JobModel,
)
from src.shared.config.constants import JobSourceType


class SQLAlchemyJobRepository(JobRepository):
    """SQLAlchemy/PostgreSQL implementation of JobRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(self, job: DiscoveredJob) -> DiscoveredJob:
        """Persist a newly discovered job."""

        existing = self.get_by_external_id(
            source=job.source,
            external_job_id=job.external_id,
        )

        if existing is not None:
            raise ValueError(
                "Job already exists for this source and external job ID."
            )

        model = self._to_model(job)

        self._session.add(model)
        self._session.flush()

        return self._to_domain(model)

    # ------------------------------------------------------------------
    # Get by internal ID
    # ------------------------------------------------------------------

    def get_by_id(self, job_id: UUID) -> DiscoveredJob | None:
        """Retrieve a job by internal UUID."""

        model = self._session.get(JobModel, job_id)

        if model is None:
            return None

        return self._to_domain(model)

    # ------------------------------------------------------------------
    # Get by external identity
    # ------------------------------------------------------------------

    def get_by_external_id(
        self,
        *,
        source: JobSourceType,
        external_job_id: str,
    ) -> DiscoveredJob | None:
        """Retrieve a job by portal source and external ID."""

        statement = select(JobModel).where(
            JobModel.source == source,
            JobModel.external_job_id == external_job_id,
        )

        model = self._session.scalar(statement)

        if model is None:
            return None

        return self._to_domain(model)

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def upsert(self, job: DiscoveredJob) -> DiscoveredJob:
        """
        Create a job if it does not exist.

        Otherwise update the existing job identified by
        source + external_job_id.
        """

        statement = select(JobModel).where(
            JobModel.source == job.source,
            JobModel.external_job_id == job.external_id,
        )

        model = self._session.scalar(statement)

        if model is None:
            model = self._to_model(job)

            self._session.add(model)
            self._session.flush()

            return self._to_domain(model)

        self._apply_domain_to_model(model, job)

        self._session.flush()

        return self._to_domain(model)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        job_id: UUID,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """Update an existing discovered job."""

        model = self._session.get(JobModel, job_id)

        if model is None:
            raise ValueError(
                f"Job with id {job_id} was not found."
            )

        # Prevent accidentally changing the identity of a job.
        if model.source != job.source:
            raise ValueError(
                "Job source cannot be changed during update."
            )

        if model.external_job_id != job.external_id:
            raise ValueError(
                "External job ID cannot be changed during update."
            )

        self._apply_domain_to_model(model, job)

        self._session.flush()

        return self._to_domain(model)

    # ------------------------------------------------------------------
    # List active
    # ------------------------------------------------------------------

    def list_active(
        self,
        *,
        source: JobSourceType | None = None,
        limit: int = 100,
    ) -> list[DiscoveredJob]:
        """Return active jobs newest first."""

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        statement = (
            select(JobModel)
            .where(JobModel.is_active.is_(True))
            .order_by(
                JobModel.posted_at.desc().nullslast(),
                JobModel.created_at.desc(),
            )
            .limit(limit)
        )

        if source is not None:
            statement = statement.where(
                JobModel.source == source
            )

        models = self._session.scalars(statement).all()

        return [
            self._to_domain(model)
            for model in models
        ]

    # ------------------------------------------------------------------
    # Deactivate
    # ------------------------------------------------------------------

    def deactivate(self, job_id: UUID) -> None:
        """Mark a job inactive."""

        model = self._session.get(JobModel, job_id)

        if model is None:
            raise ValueError(
                f"Job with id {job_id} was not found."
            )

        model.is_active = False

        self._session.flush()

    # ------------------------------------------------------------------
    # Count active
    # ------------------------------------------------------------------

    def count_active(
        self,
        *,
        source: JobSourceType | None = None,
    ) -> int:
        """Return the number of active jobs."""

        statement = select(
            func.count(JobModel.id)
        ).where(
            JobModel.is_active.is_(True)
        )

        if source is not None:
            statement = statement.where(
                JobModel.source == source
            )

        return int(
            self._session.scalar(statement) or 0
        )

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_model(job: DiscoveredJob) -> JobModel:
        """Convert a domain job into an ORM model."""

        return JobModel(
            external_job_id=job.external_id,
            source=job.source,
            title=job.title,
            company_name=job.company_name,
            url=job.url,
            location=job.location,
            remote=SQLAlchemyJobRepository._remote_status_to_bool(
                job.remote_status
            ),
            employment_type=(
                job.employment_type.value
                if job.employment_type is not None
                else None
            ),
            description=job.description,
            posted_at=SQLAlchemyJobRepository._posted_at_to_datetime(
                job.posted_at
            ),
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            is_active=True,
            metadata_json=dict(job.metadata),
        )

    @staticmethod
    def _apply_domain_to_model(
        model: JobModel,
        job: DiscoveredJob,
    ) -> None:
        """Copy domain values into an existing ORM model."""

        model.title = job.title
        model.company_name = job.company_name
        model.url = job.url
        model.location = job.location

        model.remote = (
            SQLAlchemyJobRepository._remote_status_to_bool(
                job.remote_status
            )
        )

        model.employment_type = (
            job.employment_type.value
            if job.employment_type is not None
            else None
        )

        model.description = job.description

        model.posted_at = (
            SQLAlchemyJobRepository._posted_at_to_datetime(
                job.posted_at
            )
        )

        model.salary_min = job.salary_min
        model.salary_max = job.salary_max
        model.salary_currency = job.salary_currency

        model.metadata_json = dict(job.metadata)

        model.is_active = True

    @staticmethod
    def _posted_at_to_datetime(
        value: str | None,
    ) -> datetime | None:
        """Convert the domain ISO timestamp into datetime."""

        if not value:
            return None

        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid posted_at timestamp: {value}"
            ) from exc

    @staticmethod
    def _remote_status_to_bool(
        remote_status: object | None,
    ) -> bool | None:
        """
        Convert RemoteStatus into the database boolean.

        The database intentionally stores the normalized value as:
            True  = remote
            False = non-remote
            None  = unknown

        Enum names/values are handled defensively so this mapping
        remains compatible with the project's RemoteStatus definition.
        """

        if remote_status is None:
            return None

        value = getattr(
            remote_status,
            "value",
            remote_status,
        )

        normalized = str(value).strip().lower()

        if normalized in {
            "remote",
            "fully_remote",
            "remote_only",
            "true",
        }:
            return True

        if normalized in {
            "onsite",
            "on_site",
            "office",
            "hybrid",
            "not_remote",
            "false",
        }:
            return False

        raise ValueError(
            f"Unsupported RemoteStatus value: {remote_status}"
        )

    @staticmethod
    def _to_domain(model: JobModel) -> DiscoveredJob:
        """Convert ORM model into the domain entity."""

        from src.shared.config.constants import (
            EmploymentType,
            RemoteStatus,
        )

        remote_status = (
            SQLAlchemyJobRepository._bool_to_remote_status(
                model.remote,
                RemoteStatus,
            )
        )

        employment_type = None

        if model.employment_type:
            try:
                employment_type = EmploymentType(
                    model.employment_type
                )
            except ValueError:
                employment_type = None

        return DiscoveredJob(
            external_id=model.external_job_id,
            title=model.title,
            company_name=model.company_name,
            source=model.source,
            url=model.url,
            location=model.location,
            remote_status=remote_status,
            employment_type=employment_type,
            description=model.description,
            posted_at=(
                model.posted_at.isoformat()
                if model.posted_at is not None
                else None
            ),
            salary_min=(
                float(model.salary_min)
                if model.salary_min is not None
                else None
            ),
            salary_max=(
                float(model.salary_max)
                if model.salary_max is not None
                else None
            ),
            salary_currency=model.salary_currency,
            metadata=dict(model.metadata_json or {}),
        )

    @staticmethod
    def _bool_to_remote_status(
        value: bool | None,
        remote_status_enum: type,
    ) -> object | None:
        """Convert database boolean into RemoteStatus."""

        if value is None:
            return None

        preferred_names = (
            ("REMOTE", "FULLY_REMOTE", "REMOTE_ONLY")
            if value
            else (
                "ONSITE",
                "ON_SITE",
                "OFFICE",
                "HYBRID",
                "NOT_REMOTE",
            )
        )

        for name in preferred_names:
            member = getattr(
                remote_status_enum,
                name,
                None,
            )

            if member is not None:
                return member

        # Fallback by enum value.
        for member in remote_status_enum:
            normalized = str(
                getattr(member, "value", member)
            ).lower()

            if value and "remote" in normalized:
                return member

            if not value and (
                "onsite" in normalized
                or "on_site" in normalized
                or "office" in normalized
                or "hybrid" in normalized
            ):
                return member

        raise ValueError(
            f"Unable to map database remote={value} "
            "to RemoteStatus."
        )