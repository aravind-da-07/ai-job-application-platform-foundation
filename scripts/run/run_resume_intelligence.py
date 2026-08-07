"""
Resume Intelligence Demo.

Runs the complete Resume Intelligence pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing the project when running this script directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.modules.resume_intelligence.builders.candidate_builder import (
    CandidateBuilder,
)
from src.modules.resume_intelligence.parsers.parser_factory import ParserFactory
from src.modules.resume_intelligence.schemas.resume_document import ResumeDocument
from src.modules.resume_intelligence.section_detection.section_detector import (
    SectionDetector,
)


def main() -> None:
    """
    Executes the complete Resume Intelligence pipeline.
    """

    print("=" * 70)
    print("AI Job Application Platform")
    print("Resume Intelligence Demo")
    print("=" * 70)

    resume_path = (
        PROJECT_ROOT
        / "sample_data"
        / "Aravind_Reddy_DataAnalyst_Resume.pdf"
    )

    if not resume_path.exists():
        print(f"\nResume not found:\n{resume_path}")
        return

    try:
        # ------------------------------------------------------------------
        # STEP 1 - Create ResumeDocument
        # ------------------------------------------------------------------
        print("\n[1/5] Creating ResumeDocument...")

        document = ResumeDocument.from_file(resume_path)

        print(f"File : {document.file_name}")
        print(f"Type : {document.extension}")
        print(f"Size : {document.file_size} bytes")

        # ------------------------------------------------------------------
        # STEP 2 - Parse Resume
        # ------------------------------------------------------------------
        print("\n[2/5] Parsing Resume...")

        parser = ParserFactory.create(document)

        parse_result = parser.parse(document)

        print("Parsing completed successfully.")

        print("\n" + "=" * 70)
        print("RAW PARSED TEXT (First 1000 Characters)")
        print("=" * 70)
        print(parse_result.text[:1000])
        print("=" * 70)

        # ------------------------------------------------------------------
        # STEP 3 - Detect Sections
        # ------------------------------------------------------------------
        print("\n[3/5] Detecting Resume Sections...")

        detector = SectionDetector()

        sections = detector.detect(parse_result)

        print("Section detection completed.")

        print("\n" + "=" * 70)
        print("HEADER SECTION")
        print("=" * 70)
        print(repr(sections.header))
        print("=" * 70)

        # ------------------------------------------------------------------
        # STEP 4 - Build Candidate
        # ------------------------------------------------------------------
        print("\n[4/5] Building Candidate...")

        builder = CandidateBuilder()

        candidate = builder.build(sections)

        print("Candidate created successfully.")

        print("\n" + "=" * 70)
        print("CONTACT OBJECT")
        print("=" * 70)
        print(candidate.contact)
        print("=" * 70)

        # ------------------------------------------------------------------
        # STEP 5 - Display Candidate
        # ------------------------------------------------------------------
        print("\n[5/5] Candidate Profile")

        print("-" * 70)
        print(f"Name      : {candidate.contact.full_name}")
        print(f"Email     : {candidate.contact.email}")
        print(f"Phone     : {candidate.contact.phone}")
        print(f"Location  : {candidate.contact.location}")
        print(f"LinkedIn  : {candidate.contact.linkedin}")
        print(f"GitHub    : {candidate.contact.github}")
        print(f"Portfolio : {candidate.contact.portfolio}")
        print("-" * 70)

        print("\n" + "=" * 70)
        print("Resume Intelligence Completed Successfully")
        print("=" * 70)

    except Exception as exc:
        print("\n" + "=" * 70)
        print("Resume Intelligence Failed")
        print("=" * 70)
        print(type(exc).__name__)
        print(exc)
        print("=" * 70)
        raise


if __name__ == "__main__":
    main()