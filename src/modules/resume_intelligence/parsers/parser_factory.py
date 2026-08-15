"""
Resume Parser Factory.

Responsible for selecting the correct parser implementation
based on the supplied resume document.
"""

from __future__ import annotations

from src.modules.resume_intelligence.domain.exceptions.parsing import (
    UnsupportedFileTypeError,
)
from src.modules.resume_intelligence.parsers.base_parser import ResumeParser
from src.modules.resume_intelligence.parsers.docx_parser import DOCXParser
from src.modules.resume_intelligence.parsers.pdf_parser import PDFParser
from src.modules.resume_intelligence.parsers.txt_parser import TXTParser
from src.modules.resume_intelligence.schemas.resume_document import (
    ResumeDocument,
)


class ParserFactory:
    """
    Factory responsible for selecting the correct parser.
    """

    _parsers: tuple[type[ResumeParser], ...] = (
        PDFParser,
        DOCXParser,
        TXTParser,
    )

    @classmethod
    def create(
        cls,
        document: ResumeDocument,
    ) -> ResumeParser:
        """
        Return the appropriate parser for the supplied document.
        """

        for parser_class in cls._parsers:
            parser = parser_class()

            if parser.supports(document):
                return parser

        raise UnsupportedFileTypeError(
            f"No parser available for '{document.extension}' files."
        )


__all__ = ["ParserFactory"]