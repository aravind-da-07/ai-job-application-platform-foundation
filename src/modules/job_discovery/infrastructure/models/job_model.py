"""
SQLAlchemy models for persistent job discovery data.

JobModel stores the normalized representation of a job discovered
from an external job portal.

JobMatchModel stores the result of matching a discovered job against
a user's active candidate/resume profile.

These models intentionally remain separate from the domain entities.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.config.constants import JobSourceType
from src.shared.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class JobModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    PostgreSQL representation of a normalized discovered job.
    """

    __tablename__ = "jobs"

    # --------------------------------------------------------------
    # External identity
    # --------------------------------------------------------------

    external_job_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source: Mapped[JobSourceType] = mapped_column(
        String(50),
        nullable=False,
    )

    # --------------------------------------------------------------
    # Core job information
    # --------------------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    remote: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    employment_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # --------------------------------------------------------------
    # Job content
    # --------------------------------------------------------------

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------------
    # Posting information
    # --------------------------------------------------------------

    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --------------------------------------------------------------
    # Compensation
    # --------------------------------------------------------------

    salary_min: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    salary_max: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    salary_currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # --------------------------------------------------------------
    # Lifecycle
    # --------------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # --------------------------------------------------------------
    # Flexible portal-specific data
    # --------------------------------------------------------------

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # --------------------------------------------------------------
    # Relationships
    # --------------------------------------------------------------

    matches: Mapped[list["JobMatchModel"]] = relationship(
        "JobMatchModel",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobMatchModel.created_at",
    )

    # --------------------------------------------------------------
    # Constraints / indexes
    # --------------------------------------------------------------

    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_job_id",
            name="uq_jobs_source_external_job_id",
        ),
        Index(
            "ix_jobs_source",
            "source",
        ),
        Index(
            "ix_jobs_company_name",
            "company_name",
        ),
        Index(
            "ix_jobs_is_active",
            "is_active",
        ),
        Index(
            "ix_jobs_posted_at",
            "posted_at",
        ),
        Index(
            "ix_jobs_source_active",
            "source",
            "is_active",
        ),
    )


class JobMatchModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    PostgreSQL representation of a job matching result.

    Stores the complete transparent matching breakdown so that
    the dashboard can explain why a job was recommended or rejected.
    """

    __tablename__ = "job_matches"

    # --------------------------------------------------------------
    # Relationships / ownership
    # --------------------------------------------------------------

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
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

    # --------------------------------------------------------------
    # Matching result
    # --------------------------------------------------------------

    overall_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    decision: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )

    # --------------------------------------------------------------
    # Detailed scoring
    # --------------------------------------------------------------

    title_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0,
        server_default="0",
    )

    skill_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0,
        server_default="0",
    )

    location_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0,
        server_default="0",
    )

    remote_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0,
        server_default="0",
    )

    experience_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0,
        server_default="0",
    )

    # --------------------------------------------------------------
    # Matching explanation
    # --------------------------------------------------------------

    matched_skills: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )

    missing_required_skills: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )

    matched_roles: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )

    excluded_reasons: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # --------------------------------------------------------------
    # Relationships
    # --------------------------------------------------------------

    job: Mapped["JobModel"] = relationship(
        "JobModel",
        back_populates="matches",
    )

    # --------------------------------------------------------------
    # Constraints / indexes
    # --------------------------------------------------------------

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "user_id",
            "resume_id",
            name="uq_job_matches_job_user_resume",
        ),
        Index(
            "ix_job_matches_user_created_at",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_job_matches_decision",
            "decision",
        ),
        Index(
            "ix_job_matches_overall_score",
            "overall_score",
        ),
        Index(
            "ix_job_matches_user_decision",
            "user_id",
            "decision",
        ),
    )