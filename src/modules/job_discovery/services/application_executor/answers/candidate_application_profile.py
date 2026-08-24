"""
Candidate application profile.

Builds application-ready candidate data from the existing
Resume Intelligence Candidate entity plus explicit application
preferences.

This module does not interact with Playwright or any portal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.modules.resume_intelligence.domain.entities.candidate import (
    Candidate,
)


@dataclass(frozen=True)
class CandidateApplicationProfile:
    """
    Verified candidate data and explicit application preferences.

    Resume-derived facts come from Candidate.
    Application preferences are supplied explicitly.
    """

    candidate: Candidate

    experience_years: float

    salary_expectation: str = "₹7–9 LPA"

    notice_period: str = "0 days"

    immediate_joiner: bool = True

    target_roles: tuple[str, ...] = (
        "Data Analyst",
        "Business Analyst",
    )

    preferred_locations: tuple[str, ...] = (
        "Hyderabad",
        "Bengaluru",
        "Pune",
        "Mumbai",
        "Chennai",
        "Noida",
        "Gurugram",
    )

    preferred_work_modes: tuple[str, ...] = (
        "onsite",
        "hybrid",
        "remote",
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.experience_years < 0:
            raise ValueError(
                "experience_years cannot be negative."
            )

        if not self.target_roles:
            raise ValueError(
                "At least one target role is required."
            )

        if not self.preferred_locations:
            raise ValueError(
                "At least one preferred location is required."
            )

    @property
    def skills(self) -> tuple[str, ...]:
        """
        Return normalized candidate skills.
        """

        return tuple(
            skill.name
            for skill in self.candidate.skills
        )

    @property
    def certifications(self) -> tuple[str, ...]:
        """
        Return candidate certifications.

        Certification object structure is intentionally accessed
        defensively because the resolver only needs a textual
        representation.
        """

        values: list[str] = []

        for certification in self.candidate.certifications:
            value = getattr(
                certification,
                "name",
                None,
            )

            if value:
                values.append(
                    str(value).strip()
                )

        return tuple(
            value
            for value in values
            if value
        )

    def to_candidate_data(self) -> dict[str, Any]:
        """
        Convert the profile into the generic mapping consumed
        by AnswerResolverService.
        """

        full_name = (
            self.candidate.contact.full_name
            or ""
        ).strip()

        first_name = ""
        last_name = ""

        if full_name:
            name_parts = full_name.split()

            first_name = name_parts[0]

            if len(name_parts) > 1:
                last_name = " ".join(
                    name_parts[1:]
                )

        return {
            # ------------------------------------------------------
            # Identity
            # ------------------------------------------------------

            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,

            # ------------------------------------------------------
            # Contact
            # ------------------------------------------------------

            "email": (
                str(self.candidate.contact.email)
                if self.candidate.contact.email
                else None
            ),

            "phone": (
                self.candidate.contact.phone
            ),

            "location": (
                self.candidate.contact.location
            ),

            "linkedin_url": (
                self.candidate.contact.linkedin
            ),

            "github_url": (
                self.candidate.contact.github
            ),

            "portfolio_url": (
                self.candidate.contact.portfolio
            ),

            # ------------------------------------------------------
            # Candidate facts
            # ------------------------------------------------------

            "experience_years": (
                self.experience_years
            ),

            "skills": list(self.skills),

            "certifications": list(
                self.certifications
            ),

            # ------------------------------------------------------
            # Application preferences
            # ------------------------------------------------------

            "salary": (
                self.salary_expectation
            ),

            "notice_period": (
                self.notice_period
            ),

            "immediate_joiner": (
                self.immediate_joiner
            ),

            "target_roles": list(
                self.target_roles
            ),

            "preferred_locations": list(
                self.preferred_locations
            ),

            "preferred_work_modes": list(
                self.preferred_work_modes
            ),

            # ------------------------------------------------------
            # Additional context
            # ------------------------------------------------------

            "metadata": dict(
                self.metadata
            ),
        }


__all__ = [
    "CandidateApplicationProfile",
]