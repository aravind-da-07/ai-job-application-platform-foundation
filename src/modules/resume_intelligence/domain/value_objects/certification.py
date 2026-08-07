"""
Certification Value Object.

Represents a professional certification earned by the candidate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Certification(BaseModel):
    """
    Immutable certification value object.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    name: str = Field(
        default="",
        description="Certification name.",
    )

    issuer: str | None = Field(
        default=None,
        description="Issuing organization.",
    )

    issue_date: str | None = Field(
        default=None,
        description="Issue date.",
    )

    expiration_date: str | None = Field(
        default=None,
        description="Expiration date.",
    )

    credential_id: str | None = Field(
        default=None,
        description="Credential identifier.",
    )

    credential_url: str | None = Field(
        default=None,
        description="Credential verification URL.",
    )


__all__ = ["Certification"]