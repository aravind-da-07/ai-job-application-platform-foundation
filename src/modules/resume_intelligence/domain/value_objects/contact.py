"""
Contact Value Object.

Represents a candidate's contact information.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Contact(BaseModel):
    """
    Immutable contact information for a candidate.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    full_name: str = Field(
        default="",
        description="Candidate's full name.",
    )

    email: EmailStr | None = Field(
        default=None,
        description="Primary email address.",
    )

    phone: str | None = Field(
        default=None,
        description="Primary phone number.",
    )

    location: str | None = Field(
        default=None,
        description="Current city or location.",
    )

    linkedin: str | None = Field(
        default=None,
        description="LinkedIn profile URL.",
    )

    github: str | None = Field(
        default=None,
        description="GitHub profile URL.",
    )

    portfolio: str | None = Field(
        default=None,
        description="Portfolio or personal website.",
    )


__all__ = ["Contact"]