"""
LinkedIn application field normalization.

Converts varying application-question wording into stable internal
field identifiers.

This module performs classification only.
It does not submit answers or interact with authentication/CAPTCHA.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormField,
)


@dataclass(frozen=True)
class MappedApplicationField:
    """Normalized application field."""

    field_id: str
    normalized_name: str
    original_label: str
    confidence: float

    @property
    def source_field_id(self) -> str:
        """
        Backward-compatible alias for older callers.

        The canonical identifier is now `field_id`, which matches
        the AnswerResolverService contract.
        """
        return self.field_id


class LinkedInApplicationFieldMapper:
    """Maps LinkedIn application fields to normalized names."""

    _ALIASES: dict[str, tuple[str, ...]] = {
        "first_name": (
            "first name",
            "given name",
            "candidate first name",
            "forename",
        ),
        "last_name": (
            "last name",
            "surname",
            "family name",
            "candidate last name",
        ),
        "full_name": (
            "full name",
            "candidate name",
            "complete name",
        ),
        "email": (
            "email",
            "email address",
            "contact email",
            "e-mail",
        ),
        "phone": (
            "phone",
            "phone number",
            "mobile",
            "mobile number",
            "contact number",
        ),
        "location": (
            "location",
            "current location",
            "city",
            "current city",
            "address",
        ),
        "experience_years": (
            "years of experience",
            "total experience",
            "experience",
            "years experience",
            "professional experience",
        ),
        "linkedin_url": (
            "linkedin profile",
            "linkedin url",
            "linkedin profile url",
            "linkedin",
        ),
        "resume": (
            "resume",
            "cv",
            "curriculum vitae",
        ),
        "cover_letter": (
            "cover letter",
            "covering letter",
            "covering statement",
        ),
        "salary": (
            "salary",
            "expected salary",
            "salary expectation",
            "desired salary",
            "compensation",
        ),
        "notice_period": (
            "notice period",
            "availability",
            "joining period",
            "time to join",
        ),
        "work_authorization": (
            "work authorization",
            "work permit",
            "authorized to work",
            "legally authorized",
        ),
        "sponsorship": (
            "visa sponsorship",
            "require sponsorship",
            "sponsorship",
            "visa support",
        ),
    }

    def map_field(
        self,
        field: ApplicationFormField,
    ) -> MappedApplicationField:
        """
        Normalize one application field.

        Exact aliases receive high confidence.
        Partial semantic matches receive a lower confidence score.
        Unknown questions remain unknown rather than being guessed.
        """

        normalized_label = self._normalize(field.label)

        normalized_aliases = {
            normalized_name: tuple(
                self._normalize(alias)
                for alias in aliases
            )
            for normalized_name, aliases in self._ALIASES.items()
        }

        # ----------------------------------------------------------
        # Exact alias match
        # ----------------------------------------------------------

        for normalized_name, aliases in normalized_aliases.items():
            if normalized_label in aliases:
                return MappedApplicationField(
                    field_id=field.field_id,
                    normalized_name=normalized_name,
                    original_label=field.label,
                    confidence=1.0,
                )

        # ----------------------------------------------------------
        # Partial alias match
        # ----------------------------------------------------------

        for normalized_name, aliases in normalized_aliases.items():
            for alias in aliases:
                if alias and alias in normalized_label:
                    return MappedApplicationField(
                        field_id=field.field_id,
                        normalized_name=normalized_name,
                        original_label=field.label,
                        confidence=0.85,
                    )

        # ----------------------------------------------------------
        # Unknown field
        # ----------------------------------------------------------

        return MappedApplicationField(
            field_id=field.field_id,
            normalized_name="unknown",
            original_label=field.label,
            confidence=0.0,
        )

    def map_fields(
        self,
        fields: tuple[ApplicationFormField, ...],
    ) -> tuple[MappedApplicationField, ...]:
        """Normalize multiple application fields."""

        return tuple(
            self.map_field(field)
            for field in fields
        )

    @staticmethod
    def _normalize(value: str) -> str:
        """
        Normalize text before comparison.

        The normalization:
        1. Converts text to lowercase.
        2. Removes punctuation.
        3. Converts punctuation into spaces.
        4. Collapses repeated whitespace.
        """

        value = value.lower().strip()

        value = re.sub(
            r"[^a-z0-9\s]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value