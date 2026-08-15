"""
Candidate Builder.

Builds a complete Candidate entity from extracted resume sections.
"""

from __future__ import annotations

from src.modules.resume_intelligence.domain.entities.candidate import (
    Candidate,
)
from src.modules.resume_intelligence.extractors.certification_extractor import (
    CertificationExtractor,
)
from src.modules.resume_intelligence.extractors.contact_extractor import (
    ContactExtractor,
)
from src.modules.resume_intelligence.extractors.education_extractor import (
    EducationExtractor,
)
from src.modules.resume_intelligence.extractors.experience_extractor import (
    ExperienceExtractor,
)
from src.modules.resume_intelligence.extractors.project_extractor import (
    ProjectExtractor,
)
from src.modules.resume_intelligence.extractors.skills_extractor import (
    SkillsExtractor,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class CandidateBuilder:
    """
    Builds a complete Candidate from extracted resume sections.

    The builder coordinates deterministic extractors and keeps
    extraction logic outside the Candidate domain entity.
    """

    def __init__(self) -> None:
        """
        Initialize all required extractors.
        """

        self._contact_extractor = ContactExtractor()
        self._skills_extractor = SkillsExtractor()
        self._experience_extractor = ExperienceExtractor()
        self._education_extractor = EducationExtractor()
        self._project_extractor = ProjectExtractor()
        self._certification_extractor = CertificationExtractor()

    def build(
        self,
        sections: ExtractedSections,
    ) -> Candidate:
        """
        Build a complete Candidate from extracted resume sections.
        """

        contact = self._contact_extractor.extract(
            sections
        )

        skills = self._skills_extractor.extract(
            sections
        )

        experience = self._experience_extractor.extract(
            sections
        )

        education = self._education_extractor.extract(
            sections
        )

        projects = self._project_extractor.extract(
            sections
        )

        certifications = (
            self._certification_extractor.extract(
                sections
            )
        )

        return Candidate(
            contact=contact,
            skills=skills,
            education=education,
            experience=experience,
            projects=projects,
            certifications=certifications,
        )


__all__ = ["CandidateBuilder"]