"""
Application answer resolver service.

Resolves normalized application fields against explicit candidate
data and application preferences.

This service does not interact with Playwright and does not submit
forms.

Unknown or unsupported questions are never guessed.
"""

from __future__ import annotations

from typing import Any, Mapping

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
    ApplicationAnswerDecision,
    ApplicationAnswerSource,
    AnswerResolutionResult,
)


class AnswerResolverService:
    """
    Resolve normalized application fields into safe answer candidates.

    The resolver consumes the generic mapping produced by
    CandidateApplicationProfile.to_candidate_data().

    It remains independent of Playwright and individual job portals.
    """

    # ------------------------------------------------------------------
    # Direct candidate/application profile fields
    # ------------------------------------------------------------------

    _PROFILE_FIELDS: dict[str, str] = {

        # --------------------------------------------------------------
        # Identity / contact
        # --------------------------------------------------------------

        "first_name": "first_name",
        "last_name": "last_name",
        "full_name": "full_name",
        "email": "email",
        "phone": "phone",
        "location": "location",
        "linkedin_url": "linkedin_url",
        "github_url": "github_url",
        "portfolio_url": "portfolio_url",

        # --------------------------------------------------------------
        # Documents
        # --------------------------------------------------------------

        "resume": "resume",
        "cover_letter": "cover_letter",

        # --------------------------------------------------------------
        # Candidate facts
        # --------------------------------------------------------------

        "experience_years": "experience_years",
        "certifications": "certifications",

        # --------------------------------------------------------------
        # Application preferences
        # --------------------------------------------------------------

        "salary": "salary",
        "notice_period": "notice_period",
        "immediate_joiner": "immediate_joiner",
        "joining_date": "joining_date",
        "target_role": "target_role",
        "preferred_location": "preferred_location",
        "work_mode": "work_mode",

        # --------------------------------------------------------------
        # Sensitive fields
        # --------------------------------------------------------------

        "work_authorization": "work_authorization",
        "sponsorship": "sponsorship",
    }

    # ------------------------------------------------------------------
    # Skill / experience questions
    #
    # normalized field → candidate skill
    # ------------------------------------------------------------------

    _SKILL_FIELDS: dict[str, str] = {

        # --------------------------------------------------------------
        # Core Data Analyst / Business Analyst skills
        # --------------------------------------------------------------

        "sql_experience": "SQL",
        "python_experience": "Python",
        "power_bi_experience": "Power BI",
        "tableau_experience": "Tableau",
        "excel_experience": "Excel",

        # --------------------------------------------------------------
        # Business / analytics tools
        # --------------------------------------------------------------

        "jira_experience": "Jira",
        "etl_experience": "ETL",
        "data_visualization_experience": "Data Visualization",
        "data_cleaning_experience": "Data Cleaning",
        "data_preparation_experience": "Data Preparation",
        "data_wrangling_experience": "Data Wrangling",
        "statistical_analysis_experience": "Statistical Analysis",
        "data_interpretation_experience": "Data Interpretation",
        "dbms_experience": "DBMS",
        "business_intelligence_experience": "Business Intelligence",

        # --------------------------------------------------------------
        # Development / database tools
        # --------------------------------------------------------------

        "github_experience": "GitHub",
        "gitlab_experience": "GitLab",
        "powershell_experience": "PowerShell",
        "mysql_workbench_experience": "MySQL Workbench",
        "stored_procedures_experience": "Stored Procedures",

        # --------------------------------------------------------------
        # Data / business skills
        # --------------------------------------------------------------

        "data_storytelling_experience": "Data Storytelling",
        "business_acumen": "Business Acumen",
        "data_management_experience": "Data Management",
        "data_extraction_experience": "Data Extraction",

        # --------------------------------------------------------------
        # AI / GenAI
        # --------------------------------------------------------------

        "genai_experience": "GenAI",
        "prompt_engineering_experience": "Prompt Engineering",
        "nlp_experience": "NLP",
        "ai_concepts_experience": "AI Concepts",

        # --------------------------------------------------------------
        # Professional / soft skills
        # --------------------------------------------------------------

        "critical_thinking": "Critical Thinking",
        "problem_solving": "Problem Solving",
        "teamwork": "Teamwork",
        "attention_to_detail": "Attention to Detail",
    }

    # ------------------------------------------------------------------
    # Sensitive fields must never be inferred.
    # ------------------------------------------------------------------

    _SENSITIVE_FIELDS = {
        "work_authorization",
        "sponsorship",
    }

    # ------------------------------------------------------------------
    # Fields that naturally contain multiple values.
    # ------------------------------------------------------------------

    _LIST_FIELDS = {
        "certifications",
        "target_role",
        "preferred_location",
        "work_mode",
    }

    # ------------------------------------------------------------------
    # Main resolver
    # ------------------------------------------------------------------

    def resolve_field(
        self,
        *,
        field_id: str,
        normalized_field_name: str,
        candidate_data: Mapping[str, Any],
        source: ApplicationAnswerSource = (
            ApplicationAnswerSource.CANDIDATE_PROFILE
        ),
    ) -> ApplicationAnswer:
        """
        Resolve one normalized application field.
        """

        if not field_id.strip():
            raise ValueError(
                "field_id cannot be empty."
            )

        if not normalized_field_name.strip():
            raise ValueError(
                "normalized_field_name cannot be empty."
            )

        normalized_field_name = (
            normalized_field_name.strip()
        )

        # --------------------------------------------------------------
        # Unknown question
        # --------------------------------------------------------------

        if normalized_field_name == "unknown":
            return self._manual(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                reason=(
                    "Application question could not be "
                    "reliably classified."
                ),
            )

        # --------------------------------------------------------------
        # Skill / experience question
        # --------------------------------------------------------------

        skill_name = self._SKILL_FIELDS.get(
            normalized_field_name
        )

        if skill_name is not None:
            return self._resolve_skill(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                skill_name=skill_name,
                candidate_data=candidate_data,
                source=source,
            )

        # --------------------------------------------------------------
        # Direct profile/application field
        # --------------------------------------------------------------

        candidate_key = self._PROFILE_FIELDS.get(
            normalized_field_name
        )

        if candidate_key is None:
            return self._manual(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                reason=(
                    "No supported answer resolver exists "
                    "for this field."
                ),
            )

        # --------------------------------------------------------------
        # Sensitive fields
        # --------------------------------------------------------------

        if normalized_field_name in self._SENSITIVE_FIELDS:
            value = candidate_data.get(
                candidate_key
            )

            if value is None:
                return self._manual(
                    field_id=field_id,
                    normalized_field_name=normalized_field_name,
                    reason=(
                        "Sensitive authorization or sponsorship "
                        "question requires an explicit candidate "
                        "value."
                    ),
                )

            value_string = self._stringify(
                value
            )

            if not value_string:
                return self._manual(
                    field_id=field_id,
                    normalized_field_name=normalized_field_name,
                    reason=(
                        "Sensitive candidate data is empty."
                    ),
                )

            return self._manual(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                value=value_string,
                confidence=1.0,
                source=source,
                reason=(
                    "Sensitive authorization or sponsorship "
                    "question requires explicit review before "
                    "submission."
                ),
            )

        # --------------------------------------------------------------
        # Normal profile / preference fields
        # --------------------------------------------------------------

        value = candidate_data.get(
            candidate_key
        )

        if value is None:
            return self._manual(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                reason=(
                    "Candidate data does not contain an "
                    "explicit value for this question."
                ),
            )

        value_string = self._stringify(
            value
        )

        if not value_string:
            return self._manual(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                reason=(
                    "Candidate data contains an empty value."
                ),
            )

        return ApplicationAnswer(
            field_id=field_id,
            normalized_field_name=normalized_field_name,
            value=value_string,
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=source,
            reason=(
                "Answer was explicitly provided in the "
                "candidate application profile."
            ),
        )

    # ------------------------------------------------------------------
    # Skill resolver
    # ------------------------------------------------------------------

    def _resolve_skill(
        self,
        *,
        field_id: str,
        normalized_field_name: str,
        skill_name: str,
        candidate_data: Mapping[str, Any],
        source: ApplicationAnswerSource,
    ) -> ApplicationAnswer:
        """
        Resolve a skill-experience question.

        The resolver answers YES only when the candidate profile
        explicitly contains the requested skill.
        """

        skills = candidate_data.get(
            "skills",
            (),
        )

        normalized_skills = {
            self._normalize_skill_name(
                str(skill)
            )
            for skill in skills
        }

        requested_skill = (
            self._normalize_skill_name(
                skill_name
            )
        )

        if requested_skill not in normalized_skills:
            return self._manual(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                confidence=0.0,
                reason=(
                    f"Candidate profile does not explicitly "
                    f"contain the skill '{skill_name}'."
                ),
            )

        return ApplicationAnswer(
            field_id=field_id,
            normalized_field_name=normalized_field_name,
            value="Yes",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=source,
            reason=(
                f"Candidate profile explicitly contains "
                f"the skill '{skill_name}'."
            ),
            metadata={
                "skill": skill_name,
            },
        )

    # ------------------------------------------------------------------
    # Resolve multiple fields
    # ------------------------------------------------------------------

    def resolve_fields(
        self,
        fields: tuple[Any, ...],
        candidate_data: Mapping[str, Any],
        source: ApplicationAnswerSource = (
            ApplicationAnswerSource.CANDIDATE_PROFILE
        ),
    ) -> AnswerResolutionResult:
        """
        Resolve multiple already-normalized fields.
        """

        answers = tuple(
            self.resolve_field(
                field_id=field.field_id,
                normalized_field_name=field.normalized_name,
                candidate_data=candidate_data,
                source=source,
            )
            for field in fields
        )

        auto_answer_count = sum(
            answer.decision
            == ApplicationAnswerDecision.AUTO_ANSWER
            for answer in answers
        )

        manual_review_count = sum(
            answer.decision
            == ApplicationAnswerDecision.MANUAL_REVIEW
            for answer in answers
        )

        skipped_count = sum(
            answer.decision
            == ApplicationAnswerDecision.SKIP
            for answer in answers
        )

        return AnswerResolutionResult(
            answers=answers,
            auto_answer_count=auto_answer_count,
            manual_review_count=manual_review_count,
            skipped_count=skipped_count,
            metadata={
                "total_fields": len(answers),
                "automatic_answer_rate": (
                    auto_answer_count / len(answers)
                    if answers
                    else 0.0
                ),
                "manual_review_rate": (
                    manual_review_count / len(answers)
                    if answers
                    else 0.0
                ),
                "skipped_rate": (
                    skipped_count / len(answers)
                    if answers
                    else 0.0
                ),
            },
        )

    # ------------------------------------------------------------------
    # Convert values to application-compatible strings
    # ------------------------------------------------------------------

    @staticmethod
    def _stringify(
        value: Any,
    ) -> str:
        """
        Convert candidate data into a form-compatible string.
        """

        if isinstance(value, bool):
            return (
                "Yes"
                if value
                else "No"
            )

        if isinstance(
            value,
            (list, tuple, set),
        ):
            return ", ".join(
                str(item).strip()
                for item in value
                if str(item).strip()
            )

        return str(value).strip()

    # ------------------------------------------------------------------
    # Normalize skill names
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_skill_name(
        value: str,
    ) -> str:
        """
        Normalize skill names for comparison.
        """

        return " ".join(
            value.lower()
            .strip()
            .split()
        )

    # ------------------------------------------------------------------
    # Manual-review result helper
    # ------------------------------------------------------------------

    @staticmethod
    def _manual(
        *,
        field_id: str,
        normalized_field_name: str,
        reason: str,
        value: str | None = None,
        confidence: float = 0.0,
        source: ApplicationAnswerSource = (
            ApplicationAnswerSource.UNKNOWN
        ),
    ) -> ApplicationAnswer:
        """
        Create a manual-review answer.
        """

        return ApplicationAnswer(
            field_id=field_id,
            normalized_field_name=normalized_field_name,
            value=value,
            decision=ApplicationAnswerDecision.MANUAL_REVIEW,
            confidence=confidence,
            source=source,
            reason=reason,
        )


__all__ = [
    "AnswerResolverService",
]