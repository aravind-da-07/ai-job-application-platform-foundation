"""
Experience Extractor.

Extracts structured professional experience entries from the
detected experience section of a resume.
"""

from __future__ import annotations

import re

from src.modules.resume_intelligence.domain.value_objects.experience import (
    Experience,
)
from src.modules.resume_intelligence.extractors.base_extractor import (
    BaseExtractor,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class ExperienceExtractor(
    BaseExtractor[ExtractedSections, list[Experience]]
):
    """
    Extracts structured work experience from resume text.

    The extractor recognizes common resume patterns while keeping
    deterministic extraction separate from the AI/ML layer.
    """

    _DATE_RANGE_PATTERN = re.compile(
        r"""
        (?P<start>
            (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|
            May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|
            Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)
            \s+\d{4}
            |
            \d{4}
        )
        \s*(?:-|–|—|to)\s*
        (?P<end>
            (?:Present|Current|Now)
            |
            (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|
            May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|
            Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)
            \s+\d{4}
            |
            \d{4}
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _COMPANY_TITLE_PATTERN = re.compile(
        r"^\s*(?P<title>[^|@]+?)\s+(?:at|@)\s+(?P<company>.+?)\s*$",
        re.IGNORECASE,
    )

    _BULLET_PATTERN = re.compile(
        r"^\s*(?:[-*•●▪◦]+)\s*"
    )

    def extract(
        self,
        data: ExtractedSections,
    ) -> list[Experience]:
        """
        Extract work experience entries.
        """

        text = data.experience.strip()

        if not text:
            return []

        blocks = self._split_blocks(text)

        experiences: list[Experience] = []

        for block in blocks:
            experience = self._parse_block(block)

            if experience is not None:
                experiences.append(experience)

        return experiences

    def _split_blocks(
        self,
        text: str,
    ) -> list[str]:
        """
        Split the experience section into logical entries.

        A date line is metadata belonging to the current experience;
        it must NOT start a new experience block.
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
            cleaned = self._clean_bullet(line)

            # A bullet is always part of the current experience.
            if self._is_bullet(line):
                current.append(cleaned)
                continue

            # Date ranges belong to the current experience.
            if self._DATE_RANGE_PATTERN.search(cleaned):
                current.append(cleaned)
                continue

            # Location lines generally belong to the current
            # experience and should not create a new block.
            if current and self._looks_like_location(cleaned):
                current.append(cleaned)
                continue

            # A "Title at Company" pattern strongly indicates a
            # new experience entry.
            if current and self._is_new_experience_header(cleaned):
                blocks.append(current)
                current = [cleaned]
                continue

            # If the current block is empty, start it.
            if not current:
                current.append(cleaned)
                continue

            # Otherwise treat the line as metadata/description
            # belonging to the current experience.
            current.append(cleaned)

        if current:
            blocks.append(current)

        return [
            "\n".join(block)
            for block in blocks
            if block
        ]

    def _is_new_experience_header(
        self,
        line: str,
    ) -> bool:
        """
        Determine whether a line looks like a new experience header.
        """

        if self._COMPANY_TITLE_PATTERN.match(line):
            return True

        # Common format:
        #
        # Senior Analyst | ABC Company
        #
        parts = [
            part.strip()
            for part in re.split(
                r"\s*\|\s*",
                line,
            )
            if part.strip()
        ]

        if len(parts) == 2:
            return True

        return False

    def _parse_block(
        self,
        block: str,
    ) -> Experience | None:
        """
        Convert one text block into an Experience object.
        """

        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]

        if not lines:
            return None

        first_line = self._clean_bullet(lines[0])

        date_match = self._DATE_RANGE_PATTERN.search(block)

        start_date: str | None = None
        end_date: str | None = None
        currently_working = False

        if date_match:
            start_date = date_match.group("start").strip()
            end_date = date_match.group("end").strip()

            currently_working = (
                end_date.casefold()
                in {"present", "current", "now"}
            )

        title = ""
        company = ""
        location: str | None = None

        title_company_match = (
            self._COMPANY_TITLE_PATTERN.match(first_line)
        )

        if title_company_match:
            title = title_company_match.group("title").strip()
            company = title_company_match.group("company").strip()

        else:
            parts = [
                part.strip()
                for part in re.split(
                    r"\s*\|\s*|\s+[-–—]\s+",
                    first_line,
                )
                if part.strip()
            ]

            if len(parts) >= 2:
                title = parts[0]
                company = parts[1]
            else:
                title = first_line

        description_lines: list[str] = []

        for line in lines[1:]:
            cleaned = self._clean_bullet(line)

            if not cleaned:
                continue

            if self._DATE_RANGE_PATTERN.search(cleaned):
                continue

            if self._looks_like_location(cleaned):
                if location is None:
                    location = cleaned
                    continue

            description_lines.append(cleaned)

        description = (
            "\n".join(description_lines)
            if description_lines
            else None
        )

        if not title and not company:
            return None

        return Experience(
            company=company,
            title=title,
            location=location,
            start_date=start_date,
            end_date=end_date,
            currently_working=currently_working,
            description=description,
        )

    @staticmethod
    def _is_bullet(
        value: str,
    ) -> bool:
        return bool(
            re.match(
                r"^\s*(?:[-*•●▪◦]+)\s*",
                value,
            )
        )

    @staticmethod
    def _clean_bullet(
        value: str,
    ) -> str:
        return re.sub(
            r"^\s*(?:[-*•●▪◦]+)\s*",
            "",
            value.strip(),
        ).strip()

    @staticmethod
    def _looks_like_location(
        value: str,
    ) -> bool:
        """
        Conservative location heuristic.
        """

        if len(value) > 80:
            return False

        if re.search(
            r"\b(?:india|usa|united states|uk|canada|"
            r"hyderabad|bangalore|bengaluru|chennai|"
            r"mumbai|delhi|pune|remote)\b",
            value,
            re.IGNORECASE,
        ):
            return True

        return bool(
            re.search(
                r",\s*[A-Za-z]{2,}$",
                value,
            )
        )


__all__ = ["ExperienceExtractor"]