"""
Candidate Builder.

Builds a Candidate entity from extracted resume sections.
"""

from __future__ import annotations

from src.modules.resume_intelligence.domain.entities.candidate import Candidate
from src.modules.resume_intelligence.extractors.contact_extractor import (
    ContactExtractor,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class CandidateBuilder:
    """
    Builds a Candidate entity from extracted resume sections.
    """

    def __init__(self) -> None:
        """
        Initialize required extractors.
        """

        self._contact_extractor = ContactExtractor()

    def build(
        self,
        sections: ExtractedSections,
    ) -> Candidate:
        """
        Build a Candidate from extracted resume sections.
        """

        contact = self._contact_extractor.extract(sections)

        return Candidate(
            contact=contact,
        )


__all__ = ["CandidateBuilder"]