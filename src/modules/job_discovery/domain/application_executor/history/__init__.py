"""
Application execution history domain models.

This package contains normalized domain objects used to record
application execution attempts and their final outcomes.

The history model is portal-agnostic and does not depend on
Playwright, LinkedIn, or any infrastructure implementation.
"""

from src.modules.job_discovery.domain.application_executor.history.execution_history import (
    ApplicationExecutionHistory,
    ApplicationExecutionHistoryStatus,
)

__all__ = [
    "ApplicationExecutionHistory",
    "ApplicationExecutionHistoryStatus",
]