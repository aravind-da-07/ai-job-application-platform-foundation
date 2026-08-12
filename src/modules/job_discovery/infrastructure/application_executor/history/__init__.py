"""
Application execution history infrastructure.
"""

from src.modules.job_discovery.infrastructure.application_executor.history.in_memory_history_repository import (
    InMemoryApplicationExecutionHistoryRepository,
)

__all__ = [
    "InMemoryApplicationExecutionHistoryRepository",
]