"""
PDF Resume Parser.

Parses PDF resumes using pdfplumber and returns a ResumeParseResult.
"""

from __future__ import annotations

import logging

import pdfplumber

from src.modules.resume_intelligence.domain.exceptions.parsing import (
    InvalidResumeDocumentError,
)
from src.modules.resume_intelligence.parsers.base_parser import ResumeParser
from src.modules.resume_intelligence.schemas.resume_document import ResumeDocument
from src.modules.resume_intelligence.schemas.resume_parse_result import (
    ResumeParseResult,
)
from src.modules.resume_intelligence.utils.text_normalizer import (
    TextNormalizer,
)

logger = logging.getLogger(__name__)


class PDFParser(ResumeParser):
    """
    Concrete parser implementation for PDF resumes.
    """

    def supports(self, document: ResumeDocument) -> bool:
        """
        Returns True if this parser supports the supplied document.
        """
        return document.extension.lower() == "pdf"

    def validate(self, document: ResumeDocument) -> None:
        """
        Validates the supplied PDF document before parsing.
        """

        if not self.supports(document):
            raise InvalidResumeDocumentError(
                f"Unsupported file extension: {document.extension}"
            )

        if not document.file_path.exists():
            raise InvalidResumeDocumentError(
                f"File does not exist: {document.file_path}"
            )

        if document.file_size <= 0:
            raise InvalidResumeDocumentError(
                "Resume file is empty."
            )

    def parse(self, document: ResumeDocument) -> ResumeParseResult:
        """
        Parses the supplied PDF resume and returns the extracted content.
        """

        self.validate(document)

        logger.info("Parsing PDF '%s'.", document.file_name)

        extracted_pages: list[str] = []

        try:
            with pdfplumber.open(document.file_path) as pdf:

                page_count = len(pdf.pages)

                for page in pdf.pages:
                    page_text = page.extract_text()

                    if page_text:
                        extracted_pages.append(page_text)

                extracted_text = "\n".join(extracted_pages).strip()

                # Normalize extracted text before it enters the pipeline.
                extracted_text = TextNormalizer.normalize(extracted_text)

                # ---------------------------------------------------------
                # TEMPORARY DEBUG
                # ---------------------------------------------------------
                print("\n" + "=" * 80)
                print("NORMALIZED TEXT (FIRST 250 CHARACTERS)")
                print("=" * 80)
                print(repr(extracted_text[:250]))
                print("=" * 80)

                logger.info(
                    "Successfully extracted %s pages from '%s'.",
                    page_count,
                    document.file_name,
                )

                return ResumeParseResult(
                    success=True,
                    text=extracted_text,
                    file_name=document.file_name,
                    file_size=document.file_size,
                    page_count=page_count,
                    parser_name=self.__class__.__name__,
                )

        except Exception as exc:
            logger.exception(
                "Failed to parse PDF '%s'.",
                document.file_name,
            )

            raise InvalidResumeDocumentError(
                f"Unable to parse PDF: {document.file_name}"
            ) from exc


__all__ = ["PDFParser"]