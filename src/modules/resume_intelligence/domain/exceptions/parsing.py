"""
Exceptions related to resume parsing.
"""


class ResumeParsingError(Exception):
    """Base exception for all resume parsing errors."""


class UnsupportedFileTypeError(ResumeParsingError):
    """Raised when the document format is not supported."""


class InvalidResumeDocumentError(ResumeParsingError):
    """Raised when the supplied document is invalid."""