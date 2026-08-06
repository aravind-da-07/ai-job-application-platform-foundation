"""Hashing utilities: primarily used for job-duplicate detection."""

from __future__ import annotations

import hashlib


def sha256_of_text(text: str) -> str:
    """Deterministic hash used to fingerprint job postings for dedup."""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def fingerprint_job(*, company: str, role: str, location: str) -> str:
    """
    Builds a stable duplicate-detection fingerprint from the fields most
    likely to identify "the same job" across sources, independent of
    incidental formatting differences.
    """
    normalized = "|".join(
        part.strip().lower() for part in (company, role, location)
    )
    return sha256_of_text(normalized)
