from pathlib import Path

import pytest

from src.modules.resume_intelligence.domain.exceptions.parsing import (
    UnsupportedFileTypeError,
)
from src.modules.resume_intelligence.parsers.parser_factory import ParserFactory
from src.modules.resume_intelligence.parsers.pdf_parser import PDFParser
from src.modules.resume_intelligence.schemas.resume_document import ResumeDocument


def test_parser_factory_returns_pdf_parser() -> None:
    """
    ParserFactory should return PDFParser for PDF documents.
    """

    # Arrange
    resume_path = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Aravind_Reddy_DataAnalyst_Resume.pdf"
    )

    document = ResumeDocument.from_file(resume_path)

    # Act
    parser = ParserFactory.create(document)

    # Assert
    assert isinstance(parser, PDFParser)


def test_parser_factory_unsupported_file() -> None:
    """
    ParserFactory should reject unsupported file types.
    """

    # Arrange
    document = ResumeDocument(
        file_path=Path("resume.xyz"),
        file_name="resume.xyz",
        extension="xyz",
        file_size=100,
        mime_type="application/octet-stream",
    )

    # Act / Assert
    with pytest.raises(UnsupportedFileTypeError):
        ParserFactory.create(document)