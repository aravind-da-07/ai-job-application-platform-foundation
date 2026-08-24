"""
LinkedIn application field normalization.

Converts varying application-question wording into stable internal
field identifiers.

This module performs classification only.
It does not submit answers or interact with authentication/CAPTCHA.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormField,
)


@dataclass(frozen=True)
class MappedApplicationField:
    """Normalized application field."""

    field_id: str
    normalized_name: str
    original_label: str
    confidence: float

    @property
    def source_field_id(self) -> str:
        """Backward-compatible alias for older callers."""

        return self.field_id


class LinkedInApplicationFieldMapper:
    """
    Maps LinkedIn application fields to normalized names.

    Matching strategy:

    1. Exact alias match.
    2. Most-specific partial alias match.
    3. Unknown when no reliable mapping exists.

    More specific aliases always take precedence over shorter aliases.
    This prevents cases such as "GitHub experience" being incorrectly
    classified as "github_url".
    """

    _ALIASES: dict[str, tuple[str, ...]] = {

        # ----------------------------------------------------------
        # Identity / contact
        # ----------------------------------------------------------

        "first_name": (
            "candidate first name",
            "first name",
            "given name",
            "forename",
        ),

        "last_name": (
            "candidate last name",
            "last name",
            "surname",
            "family name",
        ),

        "full_name": (
            "candidate full name",
            "candidate name",
            "full name",
            "complete name",
        ),

        "email": (
            "contact email",
            "email address",
            "e-mail",
            "email",
        ),

        "phone": (
            "phone number",
            "mobile number",
            "contact number",
            "mobile",
            "phone",
        ),

        "location": (
            "current location",
            "current city",
            "current address",
            "location",
            "city",
            "address",
        ),

        "linkedin_url": (
            "linkedin profile url",
            "linkedin profile",
            "linkedin url",
            "linkedin",
        ),

        "github_url": (
            "github profile url",
            "github profile",
            "github url",
        ),

        "portfolio_url": (
            "personal website",
            "portfolio url",
            "portfolio",
            "website",
        ),

        # ----------------------------------------------------------
        # Resume / application documents
        # ----------------------------------------------------------

        "resume": (
            "curriculum vitae",
            "resume",
            "cv",
        ),

        "cover_letter": (
            "covering statement",
            "covering letter",
            "cover letter",
        ),

        # ----------------------------------------------------------
        # Experience
        # ----------------------------------------------------------

        "experience_years": (
            "how many years of professional experience",
            "how many years of experience",
            "total years of professional experience",
            "total years experience",
            "years of professional experience",
            "professional experience",
            "total experience",
            "years experience",
        ),

        # ----------------------------------------------------------
        # Core technical skills
        # ----------------------------------------------------------

        "sql_experience": (
            "experience with sql",
            "sql experience",
            "sql skills",
            "sql knowledge",
            "proficiency in sql",
            "proficient in sql",
            "worked with sql",
        ),

        "python_experience": (
            "experience with python",
            "python experience",
            "python skills",
            "python knowledge",
            "proficiency in python",
            "proficient in python",
            "worked with python",
        ),

        "power_bi_experience": (
            "experience with power bi",
            "power bi experience",
            "power bi skills",
            "power bi knowledge",
            "power bi proficiency",
            "proficient in power bi",
        ),

        "tableau_experience": (
            "experience with tableau",
            "tableau experience",
            "tableau skills",
            "tableau knowledge",
            "tableau proficiency",
            "proficient in tableau",
        ),

        "excel_experience": (
            "experience with microsoft excel",
            "microsoft excel experience",
            "experience with excel",
            "microsoft excel",
            "excel experience",
            "excel skills",
            "excel knowledge",
            "proficiency in excel",
            "proficient in excel",
            "worked with excel",
        ),

        "jira_experience": (
            "experience with jira",
            "jira experience",
            "jira skills",
            "jira knowledge",
            "worked with jira",
        ),

        "etl_experience": (
            "extract transform load experience",
            "experience with etl",
            "etl experience",
            "etl skills",
            "etl knowledge",
        ),

        "data_visualization_experience": (
            "experience with data visualization",
            "data visualization experience",
            "data visualization skills",
            "data visualization knowledge",
        ),

        "data_cleaning_experience": (
            "experience with data cleaning",
            "data cleaning experience",
            "data cleaning skills",
            "data cleaning knowledge",
        ),

        "data_preparation_experience": (
            "experience with data preparation",
            "data preparation experience",
            "data preparation skills",
            "data preparation knowledge",
        ),

        "data_wrangling_experience": (
            "experience with data wrangling",
            "data wrangling experience",
            "data wrangling skills",
            "data wrangling knowledge",
        ),

        "statistical_analysis_experience": (
            "experience with statistical analysis",
            "statistical analysis experience",
            "statistical analysis skills",
            "statistical analysis knowledge",
        ),

        "data_interpretation_experience": (
            "experience with data interpretation",
            "data interpretation experience",
            "data interpretation skills",
            "data interpretation knowledge",
        ),

        "dbms_experience": (
            "database management systems experience",
            "experience with dbms",
            "dbms experience",
            "dbms skills",
            "dbms knowledge",
        ),

        # ----------------------------------------------------------
        # Git / development tools
        # ----------------------------------------------------------

        "github_experience": (
            "experience with github",
            "github experience",
            "github skills",
            "github knowledge",
            "worked with github",
        ),

        "gitlab_experience": (
            "experience with gitlab",
            "gitlab experience",
            "gitlab skills",
            "gitlab knowledge",
            "worked with gitlab",
        ),

        "powershell_experience": (
            "experience with powershell",
            "powershell experience",
            "powershell skills",
            "powershell knowledge",
            "worked with powershell",
        ),

        "mysql_workbench_experience": (
            "experience with mysql workbench",
            "mysql workbench experience",
            "mysql workbench skills",
            "mysql workbench knowledge",
        ),

        "stored_procedures_experience": (
            "experience with stored procedures",
            "stored procedures experience",
            "stored procedure experience",
            "stored procedures skills",
        ),

        # ----------------------------------------------------------
        # Business / analytical skills
        # ----------------------------------------------------------

        "data_storytelling_experience": (
            "experience with data storytelling",
            "data storytelling experience",
            "data storytelling skills",
            "data storytelling knowledge",
        ),

        "business_acumen": (
            "business acumen experience",
            "business acumen",
            "business knowledge",
        ),

        "business_intelligence_experience": (
            "experience with business intelligence",
            "business intelligence experience",
            "business intelligence skills",
            "business intelligence knowledge",
            "business intelligence",
            "bi experience",
            "bi skills",
        ),

        "data_management_experience": (
            "experience with data management",
            "data management experience",
            "data management skills",
            "data management knowledge",
        ),

        "data_extraction_experience": (
            "experience with data extraction",
            "data extraction experience",
            "data extraction skills",
            "data extraction knowledge",
        ),

        # ----------------------------------------------------------
        # AI / GenAI
        # ----------------------------------------------------------

        "genai_experience": (
            "experience with generative ai",
            "generative ai experience",
            "experience with genai",
            "genai experience",
            "genai skills",
            "generative ai skills",
        ),

        "prompt_engineering_experience": (
            "experience with prompt engineering",
            "prompt engineering experience",
            "prompt engineering skills",
            "prompt engineering knowledge",
        ),

        "nlp_experience": (
            "natural language processing experience",
            "experience with natural language processing",
            "experience with nlp",
            "nlp experience",
            "nlp skills",
            "nlp knowledge",
        ),

        "ai_concepts_experience": (
            "artificial intelligence experience",
            "ai concepts experience",
            "experience with ai concepts",
            "ai knowledge",
            "ai skills",
        ),

        # ----------------------------------------------------------
        # Soft skills
        # ----------------------------------------------------------

        "critical_thinking": (
            "critical thinking skills",
            "critical thinking experience",
            "critical thinking",
        ),

        "problem_solving": (
            "problem solving skills",
            "problem solving experience",
            "problem solving",
        ),

        "teamwork": (
            "teamwork skills",
            "teamwork experience",
            "team collaboration",
            "collaboration skills",
            "teamwork",
        ),

        "attention_to_detail": (
            "attention to detail skills",
            "attention to detail experience",
            "attention to detail",
            "detail oriented",
        ),

        # ----------------------------------------------------------
        # Application preferences
        # ----------------------------------------------------------

        "salary": (
            "expected salary",
            "salary expectation",
            "salary expectations",
            "desired salary",
            "expected compensation",
            "compensation",
            "salary",
        ),

        "notice_period": (
            "current notice period",
            "notice period",
            "joining period",
            "time to join",
            "days to join",
            "notice",
            "availability",
        ),

        "immediate_joiner": (
            "available to join immediately",
            "available immediately",
            "can join immediately",
            "able to join immediately",
            "ready to join immediately",
            "immediate joiner",
        ),

        "joining_date": (
            "earliest joining date",
            "date available to join",
            "available start date",
            "joining date",
            "start date",
        ),

        "target_role": (
            "preferred job role",
            "desired job role",
            "preferred role",
            "desired role",
            "desired position",
            "position",
            "role",
        ),

        "preferred_location": (
            "preferred work location",
            "preferred location",
            "location preference",
            "desired location",
        ),

        "work_mode": (
            "onsite hybrid or remote",
            "onsite hybrid remote",
            "hybrid onsite remote",
            "hybrid remote onsite",
            "remote hybrid onsite",
            "remote hybrid or onsite",
            "work arrangement",
            "working arrangement",
            "work mode",
            "remote or onsite",
            "remote work",
            "hybrid work",
            "onsite work",
            "work from home",
        ),

        # ----------------------------------------------------------
        # Sensitive factual fields
        # ----------------------------------------------------------

        "work_authorization": (
            "authorized to work",
            "legally authorized to work",
            "right to work",
            "work authorization",
            "work permit",
        ),

        "sponsorship": (
            "require visa sponsorship",
            "require sponsorship",
            "visa sponsorship",
            "visa support",
            "need sponsorship",
            "sponsorship",
        ),
    }

    def map_field(
        self,
        field: ApplicationFormField,
    ) -> MappedApplicationField:
        """
        Normalize one application field.

        Matching order:

        1. Exact alias.
        2. Longest matching partial alias.
        3. Unknown.

        Longest-match behavior prevents generic aliases from
        incorrectly overriding more specific application fields.
        """

        if field is None:
            raise ValueError(
                "field cannot be None."
            )

        normalized_label = self._normalize(
            field.label
        )

        if not normalized_label:
            return MappedApplicationField(
                field_id=field.field_id,
                normalized_name="unknown",
                original_label=field.label,
                confidence=0.0,
            )

        normalized_aliases = {
            normalized_name: tuple(
                self._normalize(alias)
                for alias in aliases
                if self._normalize(alias)
            )
            for normalized_name, aliases
            in self._ALIASES.items()
        }

        # ----------------------------------------------------------
        # Exact alias match
        # ----------------------------------------------------------

        exact_matches: list[
            tuple[str, str]
        ] = []

        for normalized_name, aliases in (
            normalized_aliases.items()
        ):
            for alias in aliases:
                if normalized_label == alias:
                    exact_matches.append(
                        (
                            normalized_name,
                            alias,
                        )
                    )

        if exact_matches:
            normalized_name, _ = max(
                exact_matches,
                key=lambda item: len(item[1]),
            )

            return MappedApplicationField(
                field_id=field.field_id,
                normalized_name=normalized_name,
                original_label=field.label,
                confidence=1.0,
            )

        # ----------------------------------------------------------
        # Partial alias match
        #
        # Choose the longest alias rather than the first alias.
        # ----------------------------------------------------------

        partial_matches: list[
            tuple[str, str]
        ] = []

        for normalized_name, aliases in (
            normalized_aliases.items()
        ):
            for alias in aliases:
                if (
                    alias
                    and alias in normalized_label
                ):
                    partial_matches.append(
                        (
                            normalized_name,
                            alias,
                        )
                    )

        if partial_matches:
            normalized_name, _ = max(
                partial_matches,
                key=lambda item: len(item[1]),
            )

            return MappedApplicationField(
                field_id=field.field_id,
                normalized_name=normalized_name,
                original_label=field.label,
                confidence=0.85,
            )

        # ----------------------------------------------------------
        # Unknown field
        # ----------------------------------------------------------

        return MappedApplicationField(
            field_id=field.field_id,
            normalized_name="unknown",
            original_label=field.label,
            confidence=0.0,
        )

    def map_fields(
        self,
        fields: tuple[ApplicationFormField, ...],
    ) -> tuple[MappedApplicationField, ...]:
        """Normalize multiple application fields."""

        if fields is None:
            raise ValueError(
                "fields cannot be None."
            )

        return tuple(
            self.map_field(field)
            for field in fields
        )

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:
        """
        Normalize text before comparison.

        The normalization:

        1. Converts text to lowercase.
        2. Removes punctuation.
        3. Converts punctuation into spaces.
        4. Collapses repeated whitespace.
        """

        if value is None:
            return ""

        value = str(value).lower().strip()

        value = re.sub(
            r"[^a-z0-9\s]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value


__all__ = [
    "MappedApplicationField",
    "LinkedInApplicationFieldMapper",
]