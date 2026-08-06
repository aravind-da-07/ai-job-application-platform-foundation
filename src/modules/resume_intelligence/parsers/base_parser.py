"""
Abstract Resume Parser

Defines the contract that every resume parser implementation
(PDF, DOCX, TXT, etc.) must follow.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.modules.resume_intelligence.schemas.resume_document import ResumeDocument
from src.modules.resume_intelligence.schemas.resume_parse_result import (
    ResumeParseResult,
)


class ResumeParser(ABC):
    """
    Abstract base class for all resume parsers.
    """

    @abstractmethod
    def supports(self, document: ResumeDocument) -> bool:
        """
        Returns True if this parser supports the supplied document.
        """
        raise NotImplementedError

    @abstractmethod
    def validate(self, document: ResumeDocument) -> None:
        """
        Validates the input document before parsing.

        Raises:
            ValueError
                If the document is invalid.
        """
        raise NotImplementedError

    @abstractmethod
    def parse(self, document: ResumeDocument) -> ResumeParseResult:
        """
        Parses the supplied resume document.

        Returns:
            ResumeParseResult
        """
        raise NotImplementedError


__all__ = ["ResumeParser"]