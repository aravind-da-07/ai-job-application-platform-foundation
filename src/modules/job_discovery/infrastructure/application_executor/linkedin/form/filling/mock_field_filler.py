"""
Test-only LinkedIn application field filler.

Records approved answers without interacting with a browser.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
    ApplicationAnswerDecision,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling.field_filler import (
    FieldFillResult,
)


class MockLinkedInApplicationFieldFiller:
    """
    Test implementation of the application field filler.

    It refuses to fill anything that has not been explicitly approved
    as AUTO_ANSWER.
    """

    def __init__(self) -> None:
        self.filled_answers: list[ApplicationAnswer] = []

    async def fill_field(
        self,
        answer: ApplicationAnswer,
    ) -> FieldFillResult:
        if (
            answer.decision
            != ApplicationAnswerDecision.AUTO_ANSWER
        ):
            return FieldFillResult(
                field_id=answer.field_id,
                success=False,
                error_code="answer_not_approved",
                error_message=(
                    "Only AUTO_ANSWER fields may be filled."
                ),
            )

        if answer.value is None or not answer.value.strip():
            return FieldFillResult(
                field_id=answer.field_id,
                success=False,
                error_code="empty_answer",
                error_message=(
                    "Approved answer contains no value."
                ),
            )

        self.filled_answers.append(answer)

        return FieldFillResult(
            field_id=answer.field_id,
            success=True,
            filled_value=answer.value,
            metadata={
                "normalized_field_name": (
                    answer.normalized_field_name
                ),
            },
        )

    @property
    def fill_count(self) -> int:
        """Number of successfully recorded fields."""

        return len(self.filled_answers)