"""
Candidate Entity.

Represents the structured candidate profile produced by the
Resume Intelligence pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.modules.resume_intelligence.domain.value_objects.certification import (
    Certification,
)
from src.modules.resume_intelligence.domain.value_objects.contact import Contact
from src.modules.resume_intelligence.domain.value_objects.education import (
    Education,
)
from src.modules.resume_intelligence.domain.value_objects.experience import (
    Experience,
)
from src.modules.resume_intelligence.domain.value_objects.project import (
    Project,
)
from src.modules.resume_intelligence.domain.value_objects.skill import Skill


class Candidate(BaseModel):
    """
    Complete candidate profile.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    contact: Contact = Field(
        description="Candidate contact information.",
    )

    skills: list[Skill] = Field(
        default_factory=list,
        description="Candidate skills.",
    )

    education: list[Education] = Field(
        default_factory=list,
        description="Education history.",
    )

    experience: list[Experience] = Field(
        default_factory=list,
        description="Professional experience.",
    )

    projects: list[Project] = Field(
        default_factory=list,
        description="Projects.",
    )

    certifications: list[Certification] = Field(
        default_factory=list,
        description="Professional certifications.",
    )


__all__ = ["Candidate"]