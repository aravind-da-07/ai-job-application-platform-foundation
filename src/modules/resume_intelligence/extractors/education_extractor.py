"""
Education Extractor.

Extracts structured education entries from the detected education
section of a resume.
"""

from __future__ import annotations

import re

from src.modules.resume_intelligence.domain.value_objects.education import (
    Education,
)
from src.modules.resume_intelligence.extractors.base_extractor import (
    BaseExtractor,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class EducationExtractor(
    BaseExtractor[ExtractedSections, list[Education]]
):
    """
    Extracts educational qualifications from resume text.

    The implementation supports common resume formats such as:

        MBA | Business Analytics | Amrita University | 2024

        Bachelor of Business Administration
        St Joseph's Degree and PG College
        2019 - 2022
        CGPA: 7.77/10
    """

    _YEAR_RANGE_PATTERN = re.compile(
        r"""
        (?P<start>\d{4})
        \s*(?:-|–|—|to)\s*
        (?P<end>\d{4})
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _YEAR_PATTERN = re.compile(
        r"\b(?:19|20)\d{2}\b"
    )

    _GRADE_PATTERN = re.compile(
        r"""
        (?:
            CGPA
            |
            GPA
            |
            Grade
            |
            Percentage
            |
            Percent
            |
            %
        )
        \s*[:\-]?\s*
        (?P<value>[A-Za-z0-9./%+-]+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _DEGREE_KEYWORDS = (
        "bachelor",
        "master",
        "mba",
        "bba",
        "b.tech",
        "btech",
        "m.tech",
        "mtech",
        "b.sc",
        "bsc",
        "m.sc",
        "msc",
        "b.com",
        "bcom",
        "m.com",
        "mcom",
        "phd",
        "doctorate",
        "diploma",
        "associate",
        "degree",
        "undergraduate",
        "postgraduate",
        "secondary",
        "intermediate",
        "ssc",
    )

    def extract(
        self,
        data: ExtractedSections,
    ) -> list[Education]:
        """
        Extract structured education entries.
        """

        text = data.education.strip()

        if not text:
            return []

        blocks = self._split_blocks(text)

        education_entries: list[Education] = []

        for block in blocks:
            education = self._parse_block(block)

            if education is not None:
                education_entries.append(education)

        return education_entries

    def _split_blocks(
        self,
        text: str,
    ) -> list[str]:
        """
        Split education text into logical qualification blocks.
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
            if current and self._looks_like_new_entry(line):
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

    def _looks_like_new_entry(
        self,
        line: str,
    ) -> bool:
        """
        Detect whether a line likely starts a new education entry.
        """

        normalized = line.casefold()

        if any(
            keyword in normalized
            for keyword in self._DEGREE_KEYWORDS
        ):
            return True

        return bool(
            re.search(
                r"\b(?:19|20)\d{2}\s*(?:-|–|—|to)\s*(?:19|20)\d{2}\b",
                line,
                re.IGNORECASE,
            )
        )

    def _parse_block(
        self,
        block: str,
    ) -> Education | None:
        """
        Parse one education block.
        """

        lines = [
            self._clean_line(line)
            for line in block.splitlines()
            if self._clean_line(line)
        ]

        if not lines:
            return None

        combined = " ".join(lines)

        start_year: str | None = None
        end_year: str | None = None

        range_match = self._YEAR_RANGE_PATTERN.search(
            combined
        )

        if range_match:
            start_year = range_match.group("start")
            end_year = range_match.group("end")
        else:
            years = self._YEAR_PATTERN.findall(combined)

            if len(years) >= 2:
                start_year = years[0]
                end_year = years[1]
            elif len(years) == 1:
                end_year = years[0]

        grade: str | None = None

        grade_match = self._GRADE_PATTERN.search(
            combined
        )

        if grade_match:
            grade = grade_match.group("value").strip()

        degree_index: int | None = None

        for index, line in enumerate(lines):
            if self._looks_like_degree(line):
                degree_index = index
                break

        if degree_index is not None:
            degree = lines[degree_index]
        else:
            degree = lines[0]

        institution: str = ""

        for index, line in enumerate(lines):
            if index == degree_index:
                continue

            if self._is_year_line(line):
                continue

            if self._GRADE_PATTERN.search(line):
                continue

            if self._looks_like_institution(line):
                institution = line
                break

        if not institution:
            for index, line in enumerate(lines):
                if index != degree_index:
                    if not self._is_year_line(line):
                        institution = line
                        break

        field_of_study = self._extract_field_of_study(
            degree
        )

        if not degree and not institution:
            return None

        return Education(
            institution=institution,
            degree=degree,
            field_of_study=field_of_study,
            start_year=start_year,
            end_year=end_year,
            grade=grade,
        )

    def _extract_field_of_study(
        self,
        degree: str,
    ) -> str | None:
        """
        Extract a field of study when expressed using common
        separators such as 'in' or '-'.
        """

        match = re.search(
            r"\b(?:in|with\s+specialization\s+in)\s+(.+)$",
            degree,
            re.IGNORECASE,
        )

        if match:
            value = match.group(1).strip()

            if value:
                return value

        return None

    def _looks_like_degree(
        self,
        value: str,
    ) -> bool:
        normalized = value.casefold()

        return any(
            keyword in normalized
            for keyword in self._DEGREE_KEYWORDS
        )

    @staticmethod
    def _looks_like_institution(
        value: str,
    ) -> bool:
        normalized = value.casefold()

        institution_keywords = (
            "university",
            "college",
            "school",
            "institute",
            "academy",
            "institution",
        )

        return any(
            keyword in normalized
            for keyword in institution_keywords
        )

    @staticmethod
    def _is_year_line(
        value: str,
    ) -> bool:
        return bool(
            re.fullmatch(
                r"""
                \s*
                (?:19|20)\d{2}
                (?:
                    \s*(?:-|–|—|to)\s*
                    (?:19|20)\d{2}
                )?
                \s*
                """,
                value,
                re.IGNORECASE | re.VERBOSE,
            )
        )

    @staticmethod
    def _clean_line(
        value: str,
    ) -> str:
        return re.sub(
            r"^\s*(?:[-*•●▪◦]+)\s*",
            "",
            value.strip(),
        ).strip()


__all__ = ["EducationExtractor"]