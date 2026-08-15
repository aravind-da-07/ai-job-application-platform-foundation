"""
TXT Resume Parser.

Parses plain-text resumes and returns a ResumeParseResult.
"""

from __future__ import annotations

import logging

from src.modules.resume_intelligence.domain.exceptions.parsing import (
    InvalidResumeDocumentError,
)
from src.modules.resume_intelligence.parsers.base_parser import ResumeParser
from src.modules.resume_intelligence.schemas.resume_document import (
    ResumeDocument,
)
from src.modules.resume_intelligence.schemas.resume_parse_result import (
    ResumeParseResult,
)
from src.modules.resume_intelligence.utils.text_normalizer import (
    TextNormalizer,
)

logger = logging.getLogger(__name__)


class TXTParser(ResumeParser):
    """
    Concrete parser implementation for TXT resumes.
    """

    def supports(self, document: ResumeDocument) -> bool:
        """
        Return True when the document is a TXT file.
        """

        return document.extension.lower() == "txt"

    def validate(self, document: ResumeDocument) -> None:
        """
        Validate the supplied TXT document before parsing.
        """

        if not self.supports(document):
            raise InvalidResumeDocumentError(
                f"Unsupported file extension: {document.extension}"
            )

        if not document.file_path.exists():
            raise InvalidResumeDocumentError(
                f"File does not exist: {document.file_path}"
            )

        if not document.file_path.is_file():
            raise InvalidResumeDocumentError(
                f"Resume path is not a file: {document.file_path}"
            )

        if document.file_size <= 0:
            raise InvalidResumeDocumentError(
                "Resume file is empty."
            )

    def parse(
        self,
        document: ResumeDocument,
    ) -> ResumeParseResult:
        """
        Parse the supplied TXT resume.
        """

        self.validate(document)

        logger.info(
            "Parsing TXT '%s'.",
            document.file_name,
        )

        try:
            raw_text = document.file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            extracted_text = TextNormalizer.normalize(
                raw_text
            )

            warnings: list[str] = []

            if not extracted_text:
                warnings.append(
                    "No text could be extracted from the TXT document."
                )

            return ResumeParseResult(
                success=True,
                text=extracted_text,
                file_name=document.file_name,
                file_size=document.file_size,
                page_count=1,
                parser_name=self.__class__.__name__,
                warnings=warnings,
            )

        except Exception as exc:
            logger.exception(
                "Failed to parse TXT '%s'.",
                document.file_name,
            )

            raise InvalidResumeDocumentError(
                f"Unable to parse TXT: {document.file_name}"
            ) from exc


__all__ = ["TXTParser"]