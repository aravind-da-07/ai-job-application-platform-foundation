"""
Certification Extractor.

Extracts structured certification entries from the detected
certifications section of a resume.
"""

from __future__ import annotations

import re

from src.modules.resume_intelligence.domain.value_objects.certification import (
    Certification,
)
from src.modules.resume_intelligence.extractors.base_extractor import (
    BaseExtractor,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class CertificationExtractor(
    BaseExtractor[ExtractedSections, list[Certification]]
):
    """
    Extracts professional certifications from resume text.

    The extractor treats certification title, issuer, dates,
    credential identifiers, and URLs as metadata belonging to
    the same certification entry.
    """

    _URL_PATTERN = re.compile(
        r"https?://[^\s|,)]+",
        re.IGNORECASE,
    )

    _CREDENTIAL_ID_PATTERN = re.compile(
        r"""
        (?:
            credential\s*(?:id|identifier)?
            |
            certificate\s*(?:id|number)
            |
            certification\s*(?:id|number)
        )
        \s*[:#\-]?\s*
        (?P<value>[A-Za-z0-9./_-]+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _DATE_PATTERN = re.compile(
        r"""
        (?:
            (?P<month>
                Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|
                Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|
                Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|
                Nov(?:ember)?|Dec(?:ember)?
            )
            \s*
        )?
        (?P<year>(?:19|20)\d{2})
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _ISSUER_PATTERN = re.compile(
        r"""
        (?:
            issued\s+by
            |
            issuer
            |
            issuing\s+organization
            |
            organization
            |
            provider
        )
        \s*[:\-]\s*
        (?P<value>.+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _ISSUER_KEYWORDS = (
        "cisco",
        "microsoft",
        "google",
        "amazon",
        "aws",
        "ibm",
        "meta",
        "coursera",
        "udemy",
        "linkedin",
        "internshala",
        "accenture",
        "tcs",
        "infosys",
        "nptel",
        "simplilearn",
    )

    _METADATA_KEYWORDS = (
        "issued",
        "issuer",
        "organization",
        "provider",
        "credential",
        "certificate",
        "certification",
        "expiry",
        "expiration",
        "expires",
        "issued on",
    )

    def extract(
        self,
        data: ExtractedSections,
    ) -> list[Certification]:
        """
        Extract structured certifications.
        """

        text = data.certifications.strip()

        if not text:
            return []

        blocks = self._split_blocks(text)

        certifications: list[Certification] = []

        for block in blocks:
            certification = self._parse_block(block)

            if certification is not None:
                certifications.append(certification)

        return certifications

    def _split_blocks(
        self,
        text: str,
    ) -> list[str]:
        """
        Split certification text into logical entries.

        Important:
        Issuer, year, credential ID, URL, and metadata lines belong
        to the preceding certification. They must not become new
        certification entries.
        """

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if not lines:
            return []

        blocks: list[list[str]] = []
        current: list[str] = []

        for line in lines:
            cleaned = self._clean_line(line)

            if not current:
                current.append(cleaned)
                continue

            if self._looks_like_metadata(cleaned):
                current.append(cleaned)
                continue

            if self._is_year_line(cleaned):
                current.append(cleaned)
                continue

            if self._URL_PATTERN.search(cleaned):
                current.append(cleaned)
                continue

            if self._CREDENTIAL_ID_PATTERN.search(cleaned):
                current.append(cleaned)
                continue

            if self._looks_like_issuer(cleaned):
                current.append(cleaned)
                continue

            # A normal non-metadata line after an existing title
            # represents a new certification.
            blocks.append(current)
            current = [cleaned]

        if current:
            blocks.append(current)

        return [
            "\n".join(block)
            for block in blocks
            if block
        ]

    def _parse_block(
        self,
        block: str,
    ) -> Certification | None:
        """
        Parse one certification block.
        """

        lines = [
            self._clean_line(line)
            for line in block.splitlines()
            if self._clean_line(line)
        ]

        if not lines:
            return None

        # The first line is the certification name.
        name = self._clean_name(lines[0])

        if not name:
            return None

        issuer: str | None = None
        issue_date: str | None = None
        expiration_date: str | None = None
        credential_id: str | None = None
        credential_url: str | None = None

        combined = " ".join(lines)

        # ----------------------------------------------------------
        # URL
        # ----------------------------------------------------------

        url_match = self._URL_PATTERN.search(combined)

        if url_match:
            credential_url = (
                url_match.group(0).rstrip(".")
            )

        # ----------------------------------------------------------
        # Credential ID
        # ----------------------------------------------------------

        credential_match = (
            self._CREDENTIAL_ID_PATTERN.search(combined)
        )

        if credential_match:
            credential_id = (
                credential_match.group("value").strip()
            )

        # ----------------------------------------------------------
        # Issuer
        # ----------------------------------------------------------

        issuer_match = self._ISSUER_PATTERN.search(
            combined
        )

        if issuer_match:
            issuer = (
                issuer_match.group("value").strip()
            )
        else:
            issuer = self._infer_issuer(lines)

        # ----------------------------------------------------------
        # Dates
        # ----------------------------------------------------------

        dates = self._extract_dates(combined)

        if dates:
            issue_date = dates[0]

            if len(dates) > 1:
                expiration_date = dates[1]

        return Certification(
            name=name,
            issuer=issuer,
            issue_date=issue_date,
            expiration_date=expiration_date,
            credential_id=credential_id,
            credential_url=credential_url,
        )

    def _extract_dates(
        self,
        text: str,
    ) -> list[str]:
        """
        Extract unique month/year or year values.
        """

        dates: list[str] = []

        for match in self._DATE_PATTERN.finditer(text):
            month = match.group("month")
            year = match.group("year")

            value = (
                f"{month} {year}"
                if month
                else year
            )

            value = value.strip()

            if value not in dates:
                dates.append(value)

        return dates

    def _infer_issuer(
        self,
        lines: list[str],
    ) -> str | None:
        """
        Infer issuer from a line such as 'Cisco' or 'Microsoft'.
        """

        for line in lines[1:]:
            if self._is_year_line(line):
                continue

            if self._CREDENTIAL_ID_PATTERN.search(line):
                continue

            if self._URL_PATTERN.search(line):
                continue

            normalized = line.casefold()

            if any(
                keyword in normalized
                for keyword in self._ISSUER_KEYWORDS
            ):
                return line

        return None

    def _looks_like_issuer(
        self,
        value: str,
    ) -> bool:
        """
        Determine whether a line looks like an issuer.
        """

        normalized = value.casefold()

        if any(
            keyword in normalized
            for keyword in self._ISSUER_KEYWORDS
        ):
            return True

        return bool(
            re.search(
                r"\b(?:university|college|institute|"
                r"organization|academy|certification)\b",
                normalized,
            )
        )

    def _looks_like_metadata(
        self,
        value: str,
    ) -> bool:
        """
        Determine whether a line is certification metadata.
        """

        normalized = value.casefold()

        return any(
            keyword in normalized
            for keyword in self._METADATA_KEYWORDS
        )

    @staticmethod
    def _is_year_line(
        value: str,
    ) -> bool:
        """
        Return True for a line containing only a year.
        """

        return bool(
            re.fullmatch(
                r"(?:19|20)\d{2}",
                value.strip(),
            )
        )

    @staticmethod
    def _clean_name(
        value: str,
    ) -> str:
        """
        Clean the certification title.
        """

        value = re.sub(
            r"^\s*(?:[-*•●▪◦]+)\s*",
            "",
            value.strip(),
        )

        value = re.split(
            r"\s+\|\s+",
            value,
            maxsplit=1,
        )[0]

        return value.strip()

    @staticmethod
    def _clean_line(
        value: str,
    ) -> str:
        return re.sub(
            r"^\s*(?:[-*•●▪◦]+)\s*",
            "",
            value.strip(),
        ).strip()


__all__ = ["CertificationExtractor"]