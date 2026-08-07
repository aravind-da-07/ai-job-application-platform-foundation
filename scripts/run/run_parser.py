"""
Resume Parser Demo.

Runs the Resume Intelligence parser against a sample resume.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running the script directly from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.modules.resume_intelligence.parsers.parser_factory import ParserFactory
from src.modules.resume_intelligence.schemas.resume_document import ResumeDocument


def main() -> None:
    """
    Executes the Resume Intelligence parser demo.
    """

    resume_path = (
        PROJECT_ROOT
        / "sample_data"
        / "Aravind_Reddy_DataAnalyst_Resume.pdf"
    )

    print("=" * 60)
    print("AI Job Application Platform")
    print("Resume Parser Demo")
    print("=" * 60)

    if not resume_path.exists():
        print(f"\nResume not found:\n{resume_path}")
        return

    try:
        document = ResumeDocument.from_file(resume_path)

        parser = ParserFactory.create(document)

        result = parser.parse(document)

        print(f"\nFile Name   : {result.file_name}")
        print(f"Parser      : {result.parser_name}")
        print(f"Pages       : {result.page_count}")
        print(f"Characters  : {len(result.text)}")
        print(f"Words       : {len(result.text.split())}")
        print(f"Status      : {'SUCCESS' if result.success else 'FAILED'}")

        print("=" * 60)
        print("Resume parsing completed successfully.")
        print("=" * 60)

    except Exception as exc:
        print("=" * 60)
        print("Resume parsing failed.")
        print(f"Reason: {exc}")
        print("=" * 60)


if __name__ == "__main__":
    main()