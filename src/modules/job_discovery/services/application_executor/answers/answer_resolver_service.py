"""
Application answer resolver service.

Resolves normalized application fields against explicit candidate data.

This service does not interact with Playwright and does not submit forms.
Unknown or sensitive questions are never guessed.
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

    candidate_data is intentionally a generic mapping so this service
    remains independent of a particular candidate/profile database model.
    """

    _PROFILE_FIELDS: dict[str, str] = {
        "first_name": "first_name",
        "last_name": "last_name",
        "full_name": "full_name",
        "email": "email",
        "phone": "phone",
        "location": "location",
        "experience_years": "experience_years",
        "linkedin_url": "linkedin_url",
        "resume": "resume",
        "cover_letter": "cover_letter",
        "salary": "salary",
        "notice_period": "notice_period",
        "work_authorization": "work_authorization",
        "sponsorship": "sponsorship",
    }

    # These fields require explicit candidate-provided values.
    # The resolver must never infer them.
    _SENSITIVE_FIELDS = {
        "work_authorization",
        "sponsorship",
    }

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

        if normalized_field_name == "unknown":
            return ApplicationAnswer(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                value=None,
                decision=ApplicationAnswerDecision.MANUAL_REVIEW,
                confidence=0.0,
                source=ApplicationAnswerSource.UNKNOWN,
                reason=(
                    "Application question could not be reliably "
                    "classified."
                ),
            )

        candidate_key = self._PROFILE_FIELDS.get(
            normalized_field_name
        )

        if candidate_key is None:
            return ApplicationAnswer(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                value=None,
                decision=ApplicationAnswerDecision.SKIP,
                confidence=0.0,
                source=ApplicationAnswerSource.UNKNOWN,
                reason=(
                    "No supported answer resolver exists for "
                    "this field."
                ),
            )

        value = candidate_data.get(candidate_key)

        if value is None:
            return ApplicationAnswer(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                value=None,
                decision=ApplicationAnswerDecision.MANUAL_REVIEW,
                confidence=0.0,
                source=ApplicationAnswerSource.UNKNOWN,
                reason=(
                    "Candidate data does not contain an explicit "
                    "value for this question."
                ),
            )

        value_string = str(value).strip()

        if not value_string:
            return ApplicationAnswer(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                value=None,
                decision=ApplicationAnswerDecision.MANUAL_REVIEW,
                confidence=0.0,
                source=ApplicationAnswerSource.UNKNOWN,
                reason=(
                    "Candidate data contains an empty value."
                ),
            )

        if normalized_field_name in self._SENSITIVE_FIELDS:
            return ApplicationAnswer(
                field_id=field_id,
                normalized_field_name=normalized_field_name,
                value=value_string,
                decision=ApplicationAnswerDecision.MANUAL_REVIEW,
                confidence=1.0,
                source=source,
                reason=(
                    "Sensitive authorization or sponsorship "
                    "question requires explicit review before "
                    "submission."
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
                "Answer was explicitly provided in candidate data."
            ),
        )

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

        Each field is expected to expose:
            field_id
            normalized_name
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
        )