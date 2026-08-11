"""
SQLAlchemy implementation of the automation repository.

This module translates between domain entities and SQLAlchemy
automation persistence models.

The domain layer exposes the field as `metadata`.

The SQLAlchemy models use `run_metadata` as the Python attribute name
because `metadata` is reserved by SQLAlchemy's Declarative API.

The database column remains `metadata`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.automation.domain.entities.automation import (
    AutomationLog,
    AutomationLogLevel,
    AutomationRun,
    AutomationRunStatus,
)
from src.modules.automation.domain.repositories.automation_repository import (
    AutomationRepository,
)
from src.modules.automation.infrastructure.models.automation_model import (
    AutomationLogModel,
    AutomationRunModel,
)


class SQLAlchemyAutomationRepository(AutomationRepository):
    """
    SQLAlchemy implementation of AutomationRepository.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Domain -> ORM conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _run_to_model(
        run: AutomationRun,
    ) -> AutomationRunModel:
        """
        Convert an AutomationRun domain entity into its SQLAlchemy model.

        Domain:
            metadata

        SQLAlchemy:
            run_metadata

        Database column:
            metadata
        """

        return AutomationRunModel(
            id=run.id,
            user_id=run.user_id,
            run_type=run.run_type,
            status=run.status.value,
            started_at=run.started_at,
            completed_at=run.completed_at,
            items_processed=run.items_processed,
            items_succeeded=run.items_succeeded,
            items_failed=run.items_failed,
            error_message=run.error_message,
            run_metadata=run.metadata,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _log_to_model(
        log: AutomationLog,
    ) -> AutomationLogModel:
        """
        Convert an AutomationLog domain entity into its SQLAlchemy model.

        Domain:
            metadata

        SQLAlchemy:
            run_metadata

        Database column:
            metadata
        """

        return AutomationLogModel(
            id=log.id,
            run_id=log.run_id,
            level=log.level.value,
            event_type=log.event_type,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            status=log.status,
            message=log.message,
            error_code=log.error_code,
            run_metadata=log.metadata,
            occurred_at=log.occurred_at,
            created_at=log.created_at,
            updated_at=log.updated_at,
        )

    # ------------------------------------------------------------------
    # ORM -> Domain conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_run(
        model: AutomationRunModel,
    ) -> AutomationRun:
        """
        Convert an AutomationRun SQLAlchemy model into its domain entity.
        """

        return AutomationRun(
            id=model.id,
            user_id=model.user_id,
            run_type=model.run_type,
            status=AutomationRunStatus(model.status),
            started_at=model.started_at,
            completed_at=model.completed_at,
            items_processed=model.items_processed,
            items_succeeded=model.items_succeeded,
            items_failed=model.items_failed,
            error_message=model.error_message,
            metadata=model.run_metadata or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _model_to_log(
        model: AutomationLogModel,
    ) -> AutomationLog:
        """
        Convert an AutomationLog SQLAlchemy model into its domain entity.
        """

        return AutomationLog(
            id=model.id,
            run_id=model.run_id,
            level=AutomationLogLevel(model.level),
            event_type=model.event_type,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            status=model.status,
            message=model.message,
            error_code=model.error_code,
            metadata=model.run_metadata or {},
            occurred_at=model.occurred_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ------------------------------------------------------------------
    # Automation runs
    # ------------------------------------------------------------------

    def create_run(
        self,
        run: AutomationRun,
    ) -> AutomationRun:
        """
        Create and persist an automation run.
        """

        model = self._run_to_model(run)

        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)

        return self._model_to_run(model)

    def get_run_by_id(
        self,
        run_id: UUID,
    ) -> AutomationRun | None:
        """
        Retrieve an automation run by ID.
        """

        model = self.session.get(
            AutomationRunModel,
            run_id,
        )

        if model is None:
            return None

        return self._model_to_run(model)

    def update_run(
        self,
        run: AutomationRun,
    ) -> AutomationRun:
        """
        Update an existing automation run.
        """

        model = self.session.get(
            AutomationRunModel,
            run.id,
        )

        if model is None:
            raise ValueError(
                f"Automation run '{run.id}' was not found."
            )

        model.user_id = run.user_id
        model.run_type = run.run_type
        model.status = run.status.value
        model.started_at = run.started_at
        model.completed_at = run.completed_at
        model.items_processed = run.items_processed
        model.items_succeeded = run.items_succeeded
        model.items_failed = run.items_failed
        model.error_message = run.error_message

        # Domain `metadata` -> SQLAlchemy `run_metadata`.
        model.run_metadata = run.metadata

        model.updated_at = datetime.now(timezone.utc)

        self.session.flush()
        self.session.refresh(model)

        return self._model_to_run(model)

    def update_run_status(
        self,
        run_id: UUID,
        status: AutomationRunStatus,
    ) -> AutomationRun:
        """
        Update only the lifecycle status of an automation run.
        """

        model = self.session.get(
            AutomationRunModel,
            run_id,
        )

        if model is None:
            raise ValueError(
                f"Automation run '{run_id}' was not found."
            )

        model.status = status.value
        model.updated_at = datetime.now(timezone.utc)

        if status == AutomationRunStatus.IN_PROGRESS:
            if model.started_at is None:
                model.started_at = datetime.now(timezone.utc)

        elif status in (
            AutomationRunStatus.COMPLETED,
            AutomationRunStatus.FAILED,
        ):
            model.completed_at = datetime.now(timezone.utc)

        self.session.flush()
        self.session.refresh(model)

        return self._model_to_run(model)

    # ------------------------------------------------------------------
    # Automation logs
    # ------------------------------------------------------------------

    def create_log(
        self,
        log: AutomationLog,
    ) -> AutomationLog:
        """
        Create and persist an automation audit log.
        """

        model = self._log_to_model(log)

        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)

        return self._model_to_log(model)

    def get_log_by_id(
        self,
        log_id: UUID,
    ) -> AutomationLog | None:
        """
        Retrieve an automation log by ID.
        """

        model = self.session.get(
            AutomationLogModel,
            log_id,
        )

        if model is None:
            return None

        return self._model_to_log(model)

    def list_logs(
        self,
        run_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AutomationLog]:
        """
        List automation logs for a specific automation run.
        """

        if limit < 1:
            raise ValueError(
                "limit must be greater than zero."
            )

        if offset < 0:
            raise ValueError(
                "offset cannot be negative."
            )

        statement = (
            select(AutomationLogModel)
            .where(
                AutomationLogModel.run_id == run_id
            )
            .order_by(
                AutomationLogModel.occurred_at.asc(),
                AutomationLogModel.created_at.asc(),
            )
            .offset(offset)
            .limit(limit)
        )

        models = self.session.scalars(
            statement
        ).all()

        return [
            self._model_to_log(model)
            for model in models
        ]

    # ------------------------------------------------------------------
    # Automation run queries
    # ------------------------------------------------------------------

    def list_runs(
        self,
        *,
        user_id: UUID | None = None,
        status: AutomationRunStatus | None = None,
        run_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AutomationRun]:
        """
        List automation runs with optional filters.
        """

        if limit < 1:
            raise ValueError(
                "limit must be greater than zero."
            )

        if offset < 0:
            raise ValueError(
                "offset cannot be negative."
            )

        statement = select(
            AutomationRunModel
        )

        if user_id is not None:
            statement = statement.where(
                AutomationRunModel.user_id == user_id
            )

        if status is not None:
            statement = statement.where(
                AutomationRunModel.status == status.value
            )

        if run_type is not None:
            statement = statement.where(
                AutomationRunModel.run_type == run_type
            )

        statement = (
            statement
            .order_by(
                AutomationRunModel.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        models = self.session.scalars(
            statement
        ).all()

        return [
            self._model_to_run(model)
            for model in models
        ]

    def count_logs(
        self,
        run_id: UUID,
    ) -> int:
        """
        Count automation logs belonging to a run.
        """

        statement = (
            select(func.count())
            .select_from(AutomationLogModel)
            .where(
                AutomationLogModel.run_id == run_id
            )
        )

        return int(
            self.session.scalar(statement) or 0
        )

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete_run(
        self,
        run_id: UUID,
    ) -> None:
        """
        Delete an automation run.

        Database cascade removes its associated automation logs.
        """

        model = self.session.get(
            AutomationRunModel,
            run_id,
        )

        if model is None:
            return

        self.session.delete(model)
        self.session.flush()