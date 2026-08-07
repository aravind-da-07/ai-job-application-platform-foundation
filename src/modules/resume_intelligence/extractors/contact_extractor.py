"""
Contact Extractor.

Extracts candidate contact information from the resume header.
"""

from __future__ import annotations

import inspect
import re

from src.modules.resume_intelligence.domain.value_objects.contact import Contact
from src.modules.resume_intelligence.extractors.base_extractor import BaseExtractor
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class ContactExtractor(BaseExtractor[ExtractedSections, Contact]):
    """
    Extracts contact information from the resume header.
    """

    EMAIL_PATTERN = re.compile(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    )

    PHONE_PATTERN = re.compile(
        r"(?:\+\d{1,3}\s?)?(?:\d[\s-]?){10,12}"
    )

    LINKEDIN_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s|]+",
        re.IGNORECASE,
    )

    GITHUB_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?github\.com/[^\s|]+",
        re.IGNORECASE,
    )

    PORTFOLIO_PATTERN = re.compile(
        r"(?:https?://|www\.)[^\s|]+",
        re.IGNORECASE,
    )

    def extract(self, data: ExtractedSections) -> Contact:
        """
        Extract contact information from the resume header.
        """

        header = data.header

        lines = [
            line.strip()
            for line in header.splitlines()
            if line.strip()
        ]

        full_name = lines[0] if lines else ""

        email_match = self.EMAIL_PATTERN.search(header)
        phone_match = self.PHONE_PATTERN.search(header)
        linkedin_match = self.LINKEDIN_PATTERN.search(header)
        github_match = self.GITHUB_PATTERN.search(header)

        portfolio = None

        for match in self.PORTFOLIO_PATTERN.finditer(header):
            url = match.group(0)
            lower = url.lower()

            if "linkedin.com" in lower:
                continue

            if "github.com" in lower:
                continue

            portfolio = url
            break

        # ---------------- DEBUG ----------------

        print("\n" + "=" * 80)
        print("CONTACT EXTRACTOR DEBUG")
        print("=" * 80)

        print("Running file:")
        print(inspect.getfile(self.__class__))

        print("\nRegex pattern:")
        print(self.EMAIL_PATTERN.pattern)

        print("\nHeader:")
        print(repr(header))

        print("\nEMAIL DEBUG")
        print("-" * 40)

        if email_match:
            print("repr(group0):", repr(email_match.group(0)))
            print("len(group0) :", len(email_match.group(0)))
            print("span        :", email_match.span())

            start, end = email_match.span()

            print("slice       :", repr(header[start:end]))
            print("len(slice)  :", len(header[start:end]))
            print("equal?      :", email_match.group(0) == header[start:end])
        else:
            print("No email match")

        print("\nPhone:")
        print(phone_match.group(0) if phone_match else None)

        print("\nLinkedIn:")
        print(linkedin_match.group(0) if linkedin_match else None)

        print("=" * 80)

        return Contact(
            full_name=full_name,
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(0).strip() if phone_match else None,
            location=None,
            linkedin=linkedin_match.group(0) if linkedin_match else None,
            github=github_match.group(0) if github_match else None,
            portfolio=portfolio,
        )


__all__ = ["ContactExtractor"]