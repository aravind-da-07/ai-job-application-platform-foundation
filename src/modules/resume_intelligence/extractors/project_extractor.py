"""
Project Extractor.

Extracts structured project entries from the detected projects
section of a resume.
"""

from __future__ import annotations

import re

from src.modules.resume_intelligence.domain.value_objects.project import (
    Project,
)
from src.modules.resume_intelligence.extractors.base_extractor import (
    BaseExtractor,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class ProjectExtractor(
    BaseExtractor[ExtractedSections, list[Project]]
):
    """
    Extracts projects from resume text.

    Supports common resume formats containing project names,
    descriptions, technologies, dates, and URLs.
    """

    _URL_PATTERN = re.compile(
        r"https?://[^\s|,)]+",
        re.IGNORECASE,
    )

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

    _TECHNOLOGY_PATTERN = re.compile(
        r"""
        (?:
            technologies?
            |
            tech\s*stack
            |
            tools?
            |
            built\s+with
            |
            stack
        )
        \s*[:\-]\s*
        (?P<value>.+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def extract(
        self,
        data: ExtractedSections,
    ) -> list[Project]:
        """
        Extract structured projects.
        """

        text = data.projects.strip()

        if not text:
            return []

        blocks = self._split_blocks(text)

        projects: list[Project] = []

        for block in blocks:
            project = self._parse_block(block)

            if project is not None:
                projects.append(project)

        return projects

    def _split_blocks(
        self,
        text: str,
    ) -> list[str]:
        """
        Split the project section into logical project blocks.
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
            if current and self._looks_like_project_start(line):
                blocks.append(current)
                current = []

            current.append(line)

        if current:
            blocks.append(current)

        return [
            "\n".join(block)
            for block in blocks
            if block
        ]

    def _looks_like_project_start(
        self,
        line: str,
    ) -> bool:
        """
        Detect likely project-name boundaries.
        """

        cleaned = self._clean_line(line)

        if not cleaned:
            return False

        if self._URL_PATTERN.search(cleaned):
            return False

        if self._TECHNOLOGY_PATTERN.search(cleaned):
            return False

        if self._DATE_RANGE_PATTERN.search(cleaned):
            return False

        # A short title-like line is generally a new project.
        words = cleaned.split()

        return (
            1 <= len(words) <= 8
            and len(cleaned) <= 100
            and not cleaned.endswith(".")
        )

    def _parse_block(
        self,
        block: str,
    ) -> Project | None:
        """
        Parse one project block.
        """

        lines = [
            self._clean_line(line)
            for line in block.splitlines()
            if self._clean_line(line)
        ]

        if not lines:
            return None

        name = lines[0]

        description_lines: list[str] = []
        technologies: list[str] = []
        url: str | None = None
        start_date: str | None = None
        end_date: str | None = None

        combined = " ".join(lines)

        date_match = self._DATE_RANGE_PATTERN.search(
            combined
        )

        if date_match:
            start_date = date_match.group("start").strip()
            end_date = date_match.group("end").strip()

        url_match = self._URL_PATTERN.search(combined)

        if url_match:
            url = url_match.group(0).rstrip(".")

        for line in lines[1:]:
            technology_match = (
                self._TECHNOLOGY_PATTERN.search(line)
            )

            if technology_match:
                technologies.extend(
                    self._parse_technology_list(
                        technology_match.group("value")
                    )
                )
                continue

            if self._URL_PATTERN.search(line):
                continue

            if self._DATE_RANGE_PATTERN.search(line):
                continue

            description_lines.append(line)

        description = (
            "\n".join(description_lines)
            if description_lines
            else None
        )

        if not name:
            return None

        return Project(
            name=name,
            description=description,
            technologies=self._deduplicate(
                technologies
            ),
            start_date=start_date,
            end_date=end_date,
            url=url,
        )

    @staticmethod
    def _parse_technology_list(
        value: str,
    ) -> list[str]:
        """
        Parse a technology list such as:

            Python, SQL, Power BI

        or:

            Python | SQL | Power BI
        """

        values = re.split(
            r"[,;|•●▪◦]+",
            value,
        )

        result: list[str] = []

        for item in values:
            normalized = re.sub(
                r"\s+",
                " ",
                item.strip(),
            )

            if normalized:
                result.append(normalized)

        return result

    @staticmethod
    def _deduplicate(
        values: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            key = value.casefold()

            if key in seen:
                continue

            seen.add(key)
            result.append(value)

        return result

    @staticmethod
    def _clean_line(
        value: str,
    ) -> str:
        return re.sub(
            r"^\s*(?:[-*•●▪◦]+)\s*",
            "",
            value.strip(),
        ).strip()


__all__ = ["ProjectExtractor"]