"""
Automation domain entities.

These models represent automation runs and persistent automation
audit logs at the business/domain level.

They are intentionally independent of SQLAlchemy and database concerns.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AutomationRunStatus(str, Enum):
    """Lifecycle status of an automation run."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AutomationLogLevel(str, Enum):
    """Severity level of a persistent automation log."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AutomationRun(BaseModel):
    """
    Domain representation of one automation execution.

    A run tracks the complete lifecycle of an automated workflow,
    including processing counters and failures.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique automation run identifier.",
    )

    user_id: UUID | None = Field(
        default=None,
        description="User associated with the automation run.",
    )

    run_type: str = Field(
        min_length=1,
        max_length=100,
        description="Type of automation workflow being executed.",
    )

    status: AutomationRunStatus = Field(
        default=AutomationRunStatus.QUEUED,
        description="Current lifecycle status of the automation run.",
    )

    started_at: datetime | None = Field(
        default=None,
        description="Timestamp when the automation run started.",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the automation run completed.",
    )

    items_processed: int = Field(
        default=0,
        ge=0,
        description="Total number of items processed.",
    )

    items_succeeded: int = Field(
        default=0,
        ge=0,
        description="Number of successfully processed items.",
    )

    items_failed: int = Field(
        default=0,
        ge=0,
        description="Number of failed items.",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message when the automation run fails.",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured automation metadata.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the automation run was created.",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the automation run was last updated.",
    )


class AutomationLog(BaseModel):
    """
    Domain representation of a persistent automation audit event.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique automation log identifier.",
    )

    run_id: UUID = Field(
        description="Automation run that generated this log.",
    )

    level: AutomationLogLevel = Field(
        default=AutomationLogLevel.INFO,
        description="Severity level of the log.",
    )

    event_type: str = Field(
        min_length=1,
        max_length=100,
        description="Automation event type.",
    )

    entity_type: str | None = Field(
        default=None,
        max_length=100,
        description="Type of business entity associated with the event.",
    )

    entity_id: UUID | None = Field(
        default=None,
        description="Identifier of the associated business entity.",
    )

    status: str | None = Field(
        default=None,
        max_length=50,
        description="Status associated with the event.",
    )

    message: str = Field(
        min_length=1,
        description="Human-readable audit message.",
    )

    error_code: str | None = Field(
        default=None,
        max_length=100,
        description="Application-specific error code.",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured event metadata.",
    )

    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the event occurred.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the log record was created.",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the log record was last updated.",
    )