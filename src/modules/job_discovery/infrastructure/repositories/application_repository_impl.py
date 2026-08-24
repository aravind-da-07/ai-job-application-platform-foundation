"""
SQLAlchemy implementation of the application repository.

Provides persistent storage for application queue items and their
lifecycle state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.job_discovery.domain.application_queue import (
    ApplicationQueueItem,
)
from src.modules.job_discovery.domain.repositories.application_repository import (
    ApplicationRepository,
)
from src.modules.job_discovery.infrastructure.models.application_model import (
    ApplicationModel,
)
from src.shared.config.constants import (
    ApplicationStatus,
    JobSourceType,
)


class SQLAlchemyApplicationRepository(ApplicationRepository):
    """
    PostgreSQL-backed application repository.

    The repository converts between the domain queue item and the
    SQLAlchemy persistence model.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        item: ApplicationQueueItem,
        *,
        user_id: UUID,
        job_id: UUID,
        resume_id: UUID | None = None,
        resume_version_id: UUID | None = None,
        queued_at: datetime | None = None,
    ) -> ApplicationQueueItem:
        """
        Persist a new application.
        """

        queued_at = (
            queued_at
            or datetime.now(timezone.utc)
        )

        model = ApplicationModel(
            id=uuid.UUID(
                item.application_id.replace(
                    "app-",
                    "",
                )
            ),
            user_id=user_id,
            job_id=job_id,
            resume_id=resume_id,
            resume_version_id=resume_version_id,
            external_job_id=item.external_job_id,
            source=item.source.value,
            job_url=item.job_url,
            job_title=item.job_title,
            company_name=item.company_name,
            match_score=Decimal(
                str(item.match_score)
            ),
            status=item.status,
            priority=item.priority,
            attempt_count=item.attempt_count,
            max_attempts=item.max_attempts,
            queued_at=queued_at,
            metadata_json=dict(
                item.metadata
            ),
        )

        self.session.add(model)
        self.session.flush()

        return self._to_domain(model)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        application_id: str,
    ) -> ApplicationQueueItem | None:
        """
        Return an application by its application ID.
        """

        try:
            model_id = uuid.UUID(
                application_id.replace(
                    "app-",
                    "",
                )
            )
        except ValueError:
            return None

        model = self.session.get(
            ApplicationModel,
            model_id,
        )

        if model is None:
            return None

        return self._to_domain(model)

    def get_by_job(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        resume_id: UUID | None = None,
    ) -> ApplicationQueueItem | None:
        """
        Return an application for the given user/job/resume.
        """

        statement = (
            select(ApplicationModel)
            .where(
                ApplicationModel.user_id == user_id,
                ApplicationModel.job_id == job_id,
                ApplicationModel.resume_id == resume_id,
            )
            .limit(1)
        )

        model = self.session.execute(
            statement
        ).scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------

    def list_queued(
        self,
        *,
        user_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ApplicationQueueItem]:
        """
        Return queued applications in execution order.

        Ordering:

        1. Highest priority
        2. Highest match score
        3. Earliest queued time
        """

        if limit < 1:
            raise ValueError(
                "limit must be greater than zero."
            )

        statement = (
            select(ApplicationModel)
            .where(
                ApplicationModel.status
                == ApplicationStatus.QUEUED
            )
            .order_by(
                ApplicationModel.priority.desc(),
                ApplicationModel.match_score.desc(),
                ApplicationModel.queued_at.asc(),
            )
            .limit(limit)
        )

        if user_id is not None:
            statement = statement.where(
                ApplicationModel.user_id == user_id
            )

        models = self.session.execute(
            statement
        ).scalars().all()

        return [
            self._to_domain(model)
            for model in models
        ]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        item: ApplicationQueueItem,
    ) -> ApplicationQueueItem:
        """
        Persist application state changes.
        """

        try:
            model_id = uuid.UUID(
                item.application_id.replace(
                    "app-",
                    "",
                )
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid application ID."
            ) from exc

        model = self.session.get(
            ApplicationModel,
            model_id,
        )

        if model is None:
            raise ValueError(
                f"Application not found: "
                f"{item.application_id}"
            )

        model.status = item.status
        model.priority = item.priority
        model.attempt_count = item.attempt_count
        model.max_attempts = item.max_attempts
        model.metadata_json = dict(
            item.metadata
        )

        self.session.flush()

        return self._to_domain(model)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(
        self,
        application_id: str,
    ) -> None:
        """
        Delete an application.
        """

        try:
            model_id = uuid.UUID(
                application_id.replace(
                    "app-",
                    "",
                )
            )
        except ValueError:
            return

        model = self.session.get(
            ApplicationModel,
            model_id,
        )

        if model is None:
            return

        self.session.delete(model)
        self.session.flush()

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(
        model: ApplicationModel,
    ) -> ApplicationQueueItem:
        """
        Convert a persistence model into a domain queue item.

        Database values are explicitly converted back into their
        domain enums.
        """

        application_id = (
            f"app-{model.id.hex}"
        )

        return ApplicationQueueItem(
            application_id=application_id,
            external_job_id=model.external_job_id,
            job_title=model.job_title,
            company_name=model.company_name,
            job_url=model.job_url,
            source=JobSourceType(
                model.source
            ),
            match_score=float(
                model.match_score
            ),
            priority=model.priority,
            status=ApplicationStatus(
                model.status
            ),
            attempt_count=model.attempt_count,
            max_attempts=model.max_attempts,
            metadata=dict(
                model.metadata_json or {}
            ),
            created_at=(
                model.queued_at
                or model.created_at
            ),
        )