"""File handling utilities: extension checks, safe filenames, size checks."""

from __future__ import annotations

import re
from pathlib import Path

from src.shared.config.constants import SUPPORTED_RESUME_FORMATS
from src.shared.core.exceptions import UnsupportedFileFormatError

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def validate_resume_extension(filename: str) -> str:
    """Returns the lowercase extension if supported, else raises."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_RESUME_FORMATS:
        raise UnsupportedFileFormatError(
            f"Unsupported resume format '{ext}'. Supported formats: {SUPPORTED_RESUME_FORMATS}"
        )
    return ext


def safe_filename(original_filename: str) -> str:
    """Strips characters that are unsafe for storage keys/paths."""
    stem = Path(original_filename).stem
    ext = Path(original_filename).suffix
    return f"{_SAFE_FILENAME_RE.sub('_', stem)}{ext.lower()}"
