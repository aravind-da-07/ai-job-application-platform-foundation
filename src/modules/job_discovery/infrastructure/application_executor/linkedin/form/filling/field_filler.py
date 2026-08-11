"""
LinkedIn application field filler contract.

Defines the browser-facing contract for filling approved application
answers.

This component must only receive answers that have already passed
answer resolution and execution planning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
)


@dataclass(frozen=True)
class FieldFillResult:
    """Result of attempting to fill one application field."""

    field_id: str
    success: bool
    filled_value: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


class ApplicationFieldFiller(Protocol):
    """
    Browser-independent contract for application field filling.

    Implementations may use Playwright or another browser mechanism.
    """

    async def fill_field(
        self,
        answer: ApplicationAnswer,
    ) -> FieldFillResult:
        """Fill one approved application answer."""
        ...