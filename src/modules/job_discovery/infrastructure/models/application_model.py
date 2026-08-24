"""
SQLAlchemy model for persistent job applications.

An application record also acts as the persistent application queue.
The status determines where the application is in its lifecycle.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.config.constants import ApplicationStatus
from src.shared.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ApplicationModel(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """
    Persistent representation of one job application.

    The row remains throughout the application lifecycle:

        queued
            -> in_progress
            -> submitted

    or:

        queued
            -> in_progress
            -> failed
            -> retry / terminal state
    """

    __tablename__ = "applications"

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Job / resume references
    # ------------------------------------------------------------------

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "resumes.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "resume_versions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # External job information
    # ------------------------------------------------------------------

    external_job_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    job_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    job_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    match_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Queue / lifecycle
    # ------------------------------------------------------------------

    status: Mapped[ApplicationStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ApplicationStatus.QUEUED,
        server_default=ApplicationStatus.QUEUED.value,
        index=True,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
    )

    # ------------------------------------------------------------------
    # Lifecycle timestamps
    # ------------------------------------------------------------------

    queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Result information
    # ------------------------------------------------------------------

    confirmation_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Flexible metadata
    # ------------------------------------------------------------------

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # ------------------------------------------------------------------
    # Constraints / indexes
    # ------------------------------------------------------------------

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "job_id",
            "resume_id",
            name="uq_applications_user_job_resume",
        ),
        Index(
            "ix_applications_status_priority",
            "status",
            "priority",
        ),
        Index(
            "ix_applications_queue_order",
            "status",
            "priority",
            "match_score",
            "queued_at",
        ),
        Index(
            "ix_applications_user_status",
            "user_id",
            "status",
        ),
        Index(
            "ix_applications_external_job",
            "source",
            "external_job_id",
        ),
    )