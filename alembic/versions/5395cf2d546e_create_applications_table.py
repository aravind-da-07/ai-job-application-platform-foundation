"""create applications table

Revision ID: 5395cf2d546e
Revises: 351be0dff288
Create Date: 2026-08-18 00:01:26.270342

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5395cf2d546e"
down_revision: Union[str, Sequence[str], None] = "351be0dff288"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the persistent applications table."""

    op.create_table(
        "applications",

        # --------------------------------------------------------------
        # Ownership
        # --------------------------------------------------------------

        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),

        # --------------------------------------------------------------
        # Job / resume references
        # --------------------------------------------------------------

        sa.Column(
            "job_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "resume_id",
            sa.UUID(),
            nullable=True,
        ),

        sa.Column(
            "resume_version_id",
            sa.UUID(),
            nullable=True,
        ),

        # --------------------------------------------------------------
        # External job information
        # --------------------------------------------------------------

        sa.Column(
            "external_job_id",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "job_url",
            sa.String(length=1000),
            nullable=False,
        ),

        sa.Column(
            "job_title",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "company_name",
            sa.String(length=255),
            nullable=False,
        ),

        # --------------------------------------------------------------
        # Matching
        # --------------------------------------------------------------

        sa.Column(
            "match_score",
            sa.Numeric(precision=5, scale=4),
            nullable=False,
        ),

        # --------------------------------------------------------------
        # Queue / lifecycle
        # --------------------------------------------------------------

        sa.Column(
            "status",
            sa.String(length=50),
            server_default="queued",
            nullable=False,
        ),

        sa.Column(
            "priority",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),

        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),

        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),

        # --------------------------------------------------------------
        # Lifecycle timestamps
        # --------------------------------------------------------------

        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        # --------------------------------------------------------------
        # Submission result
        # --------------------------------------------------------------

        sa.Column(
            "confirmation_id",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "error_code",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),

        # --------------------------------------------------------------
        # Flexible metadata
        # --------------------------------------------------------------

        sa.Column(
            "metadata",
            postgresql.JSON(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),

        # --------------------------------------------------------------
        # Standard shared model fields
        # --------------------------------------------------------------

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        # --------------------------------------------------------------
        # Foreign keys
        # --------------------------------------------------------------

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            ondelete="SET NULL",
        ),

        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
        ),

        # --------------------------------------------------------------
        # Primary key
        # --------------------------------------------------------------

        sa.PrimaryKeyConstraint("id"),

        # --------------------------------------------------------------
        # Duplicate application protection
        # --------------------------------------------------------------

        sa.UniqueConstraint(
            "user_id",
            "job_id",
            "resume_id",
            name="uq_applications_user_job_resume",
        ),
    )

    # --------------------------------------------------------------
    # Indexes
    # --------------------------------------------------------------

    op.create_index(
        "ix_applications_user_id",
        "applications",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_applications_job_id",
        "applications",
        ["job_id"],
        unique=False,
    )

    op.create_index(
        "ix_applications_resume_id",
        "applications",
        ["resume_id"],
        unique=False,
    )

    op.create_index(
        "ix_applications_resume_version_id",
        "applications",
        ["resume_version_id"],
        unique=False,
    )

    op.create_index(
        "ix_applications_external_job_id",
        "applications",
        ["external_job_id"],
        unique=False,
    )

    op.create_index(
        "ix_applications_source",
        "applications",
        ["source"],
        unique=False,
    )

    op.create_index(
        "ix_applications_match_score",
        "applications",
        ["match_score"],
        unique=False,
    )

    op.create_index(
        "ix_applications_status",
        "applications",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_applications_priority",
        "applications",
        ["priority"],
        unique=False,
    )

    op.create_index(
        "ix_applications_queued_at",
        "applications",
        ["queued_at"],
        unique=False,
    )

    op.create_index(
        "ix_applications_submitted_at",
        "applications",
        ["submitted_at"],
        unique=False,
    )

    op.create_index(
        "ix_applications_error_code",
        "applications",
        ["error_code"],
        unique=False,
    )

    op.create_index(
        "ix_applications_status_priority",
        "applications",
        ["status", "priority"],
        unique=False,
    )

    op.create_index(
        "ix_applications_queue_order",
        "applications",
        [
            "status",
            "priority",
            "match_score",
            "queued_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_applications_user_status",
        "applications",
        ["user_id", "status"],
        unique=False,
    )

    op.create_index(
        "ix_applications_external_job",
        "applications",
        ["source", "external_job_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the persistent applications table."""

    op.drop_index(
        "ix_applications_external_job",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_user_status",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_queue_order",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_status_priority",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_error_code",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_submitted_at",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_queued_at",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_priority",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_status",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_match_score",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_source",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_external_job_id",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_resume_version_id",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_resume_id",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_job_id",
        table_name="applications",
    )

    op.drop_index(
        "ix_applications_user_id",
        table_name="applications",
    )

    op.drop_table("applications")