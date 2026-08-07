"""
Unit tests for the Resume Section Detector.
"""

from pathlib import Path

from src.modules.resume_intelligence.parsers.parser_factory import ParserFactory
from src.modules.resume_intelligence.schemas.resume_document import ResumeDocument
from src.modules.resume_intelligence.section_detection.section_detector import (
    SectionDetector,
)


def test_section_detector_extracts_sections() -> None:
    """
    SectionDetector should detect logical resume sections.
    """

    # Arrange
    resume_path = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Aravind_Reddy_DataAnalyst_Resume.pdf"
    )

    document = ResumeDocument.from_file(resume_path)

    parser = ParserFactory.create(document)

    parse_result = parser.parse(document)

    detector = SectionDetector()

    # Act
    sections = detector.detect(parse_result)

    # Assert

    assert sections.header != ""

    assert isinstance(sections.skills, str)

    assert isinstance(sections.experience, str)

    assert isinstance(sections.education, str)