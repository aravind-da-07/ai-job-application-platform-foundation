"""
Resume Intelligence Orchestration Service.

Coordinates the complete resume intelligence pipeline:

    Resume file
        ↓
    ResumeDocument
        ↓
    ParserFactory
        ↓
    ResumeParser
        ↓
    ResumeParseResult
        ↓
    SectionDetector
        ↓
    ExtractedSections
        ↓
    CandidateBuilder
        ↓
    Candidate

This service is intentionally independent of:
- FastAPI
- SQLAlchemy
- Supabase
- background schedulers
- AI/ML matching

Those concerns will consume this service later.
"""

from __future__ import annotations

from pathlib import Path

from src.modules.resume_intelligence.builders.candidate_builder import (
    CandidateBuilder,
)
from src.modules.resume_intelligence.domain.entities.candidate import (
    Candidate,
)
from src.modules.resume_intelligence.parsers.parser_factory import (
    ParserFactory,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)
from src.modules.resume_intelligence.schemas.resume_document import (
    ResumeDocument,
)
from src.modules.resume_intelligence.schemas.resume_parse_result import (
    ResumeParseResult,
)
from src.modules.resume_intelligence.section_detection.section_detector import (
    SectionDetector,
)


class ResumeIntelligenceResult:
    """
    Complete output of the Resume Intelligence pipeline.

    Contains both intermediate parsing information and the final
    structured candidate profile.
    """

    def __init__(
        self,
        *,
        document: ResumeDocument,
        parse_result: ResumeParseResult,
        sections: ExtractedSections,
        candidate: Candidate,
    ) -> None:
        self.document = document
        self.parse_result = parse_result
        self.sections = sections
        self.candidate = candidate


class ResumeIntelligenceService:
    """
    Orchestrates the complete deterministic resume intelligence flow.
    """

    def __init__(
        self,
        *,
        parser_factory: type[ParserFactory] = ParserFactory,
        section_detector: SectionDetector | None = None,
        candidate_builder: CandidateBuilder | None = None,
    ) -> None:
        self._parser_factory = parser_factory
        self._section_detector = (
            section_detector
            if section_detector is not None
            else SectionDetector()
        )
        self._candidate_builder = (
            candidate_builder
            if candidate_builder is not None
            else CandidateBuilder()
        )

    def process_file(
        self,
        file_path: str | Path,
        *,
        source: str = "local",
    ) -> ResumeIntelligenceResult:
        """
        Process a resume file through the complete pipeline.

        Args:
            file_path:
                Path to the resume file.

            source:
                Origin of the resume document, for example:
                "local", "upload", or "storage".

        Returns:
            ResumeIntelligenceResult containing:
                - ResumeDocument
                - ResumeParseResult
                - ExtractedSections
                - Candidate

        Raises:
            FileNotFoundError:
                If the supplied file does not exist.

            ValueError:
                If the supplied path is not a file.

            UnsupportedFileTypeError:
                If no parser supports the document.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Resume file does not exist: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Resume path is not a file: {path}"
            )

        # --------------------------------------------------------------
        # Step 1: Build the normalized document representation.
        # --------------------------------------------------------------

        document = ResumeDocument.from_file(
            path,
            source=source,
        )

        # --------------------------------------------------------------
        # Step 2: Select the appropriate parser.
        # --------------------------------------------------------------

        parser = self._parser_factory.create(
            document
        )

        # --------------------------------------------------------------
        # Step 3: Parse the resume.
        # --------------------------------------------------------------

        parse_result = parser.parse(
            document
        )

        # --------------------------------------------------------------
        # Step 4: Detect logical resume sections.
        # --------------------------------------------------------------

        sections = self._section_detector.detect(
            parse_result
        )

        # --------------------------------------------------------------
        # Step 5: Build the structured candidate profile.
        # --------------------------------------------------------------

        candidate = self._candidate_builder.build(
            sections
        )

        return ResumeIntelligenceResult(
            document=document,
            parse_result=parse_result,
            sections=sections,
            candidate=candidate,
        )

    def parse_file(
        self,
        file_path: str | Path,
        *,
        source: str = "local",
    ) -> ResumeIntelligenceResult:
        """
        Alias for process_file().

        Useful for callers that naturally think in terms of parsing.
        """

        return self.process_file(
            file_path,
            source=source,
        )


__all__ = [
    "ResumeIntelligenceResult",
    "ResumeIntelligenceService",
]