"""
SQLAlchemy models for resumes and resume versions.

A Resume represents the logical resume owned by a user.
A ResumeVersion represents a specific uploaded version of that resume.

The database enforces:
- Resume ownership through the users table.
- Unique version numbers per resume.
- Duplicate file protection through SHA-256 hash.
- Only one active version per resume.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResumeModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Database representation of a logical resume belonging to a user.

    One user can have multiple logical resumes.
    Each logical resume can contain multiple versions.
    """

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    versions: Mapped[list["ResumeVersionModel"]] = relationship(
        "ResumeVersionModel",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeVersionModel.version_number",
    )


class ResumeVersionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Database representation of a specific resume file version.

    Every time the user updates their resume, a new version can be
    created while preserving all previous versions for historical
    application tracking.
    """

    __tablename__ = "resume_versions"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_extension: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    resume: Mapped["ResumeModel"] = relationship(
        "ResumeModel",
        back_populates="versions",
    )

    __table_args__ = (
        # Prevent duplicate version numbers for the same resume.
        UniqueConstraint(
            "resume_id",
            "version_number",
            name="uq_resume_versions_resume_version",
        ),

        # Prevent storing the exact same resume file twice
        # for the same logical resume.
        UniqueConstraint(
            "resume_id",
            "file_hash",
            name="uq_resume_versions_resume_hash",
        ),

        # PostgreSQL partial unique index:
        # only one version can have is_active = TRUE
        # for a particular resume.
        Index(
            "uq_resume_versions_one_active",
            "resume_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
    )