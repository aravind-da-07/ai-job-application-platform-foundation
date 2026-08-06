from pathlib import Path

from src.modules.resume_intelligence.schemas.resume_document import ResumeDocument


def test_create_resume_document_from_file() -> None:
    """
    ResumeDocument should correctly populate metadata from a file.
    """

    resume_path = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Aravind_Reddy_DataAnalyst_Resume.pdf"
    )

    document = ResumeDocument.from_file(resume_path)

    assert document.file_name == "Aravind_Reddy_DataAnalyst_Resume.pdf"
    assert document.extension == "pdf"
    assert document.file_size > 0
    assert document.mime_type == "application/pdf"