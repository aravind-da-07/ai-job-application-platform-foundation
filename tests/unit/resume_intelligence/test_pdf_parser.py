from pathlib import Path

from src.modules.resume_intelligence.parsers.pdf_parser import PDFParser
from src.modules.resume_intelligence.schemas.resume_document import ResumeDocument


def test_pdf_parser_supports_pdf() -> None:
    """
    PDFParser should support PDF documents.
    """

    resume_path = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Aravind_Reddy_DataAnalyst_Resume.pdf"
    )

    document = ResumeDocument.from_file(resume_path)

    parser = PDFParser()

    assert parser.supports(document) is True


def test_pdf_parser_parse_resume() -> None:
    """
    PDFParser should successfully parse a valid PDF resume.
    """

    resume_path = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Aravind_Reddy_DataAnalyst_Resume.pdf"
    )

    document = ResumeDocument.from_file(resume_path)

    parser = PDFParser()

    result = parser.parse(document)

    assert result.success is True
    assert result.page_count >= 1
    assert len(result.text) > 0
    assert result.parser_name == "PDFParser"