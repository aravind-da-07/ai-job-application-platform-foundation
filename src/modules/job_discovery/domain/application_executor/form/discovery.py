"""
Portal-independent application form discovery models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApplicationFormType(str, Enum):
    """
    Identifies the detected application flow.
    """

    UNKNOWN = "unknown"
    EASY_APPLY = "easy_apply"
    EXTERNAL_APPLICATION = "external_application"
    AUTHENTICATION_REQUIRED = "authentication_required"
    CAPTCHA_DETECTED = "captcha_detected"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True)
class ApplicationFormField:
    """
    Normalized application form field.
    """

    field_id: str
    label: str
    field_type: str
    required: bool = False
    options: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class ApplicationFormSnapshot:
    """
    Snapshot of a discovered application form.
    """

    form_type: ApplicationFormType
    url: str
    fields: tuple[ApplicationFormField, ...] = ()
    title: str | None = None
    company_name: str | None = None
    detected: bool = False
    requires_authentication: bool = False
    captcha_detected: bool = False
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def field_count(self) -> int:
        """Return the number of discovered fields."""

        return len(self.fields)