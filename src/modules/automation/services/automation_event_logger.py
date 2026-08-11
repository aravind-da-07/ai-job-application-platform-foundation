"""
Automation event logger.

Bridges the in-process EventBus with persistent automation audit logs.

The EventBus remains infrastructure-level and does not know about
database repositories. This subscriber translates application events
into persistent audit records through AutomationService.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.modules.automation.domain.entities.automation import (
    AutomationLogLevel,
)
from src.modules.automation.services.automation_service import (
    AutomationService,
)
from src.shared.config.constants import EventType
from src.shared.events.event_bus import Event


class AutomationEventLogger:
    """
    Persists important application events as automation audit logs.

    Only events that belong to an automation run are persisted.

    The automation run ID is expected in the event payload as:

        {
            "automation_run_id": "<UUID>"
        }

    Events without an automation_run_id are intentionally ignored.
    """

    def __init__(
        self,
        automation_service: AutomationService,
    ) -> None:
        self.automation_service = automation_service

    def handle(
        self,
        event: Event,
    ) -> None:
        """
        Handle one EventBus event and persist it when associated
        with an automation run.
        """

        run_id = self._extract_run_id(
            event.payload
        )

        if run_id is None:
            return

        level = self._resolve_level(
            event.type
        )

        entity_type = self._extract_string(
            event.payload,
            "entity_type",
        )

        entity_id = self._extract_uuid(
            event.payload,
            "entity_id",
        )

        status = self._extract_string(
            event.payload,
            "status",
        )

        error_code = self._extract_string(
            event.payload,
            "error_code",
        )

        message = self._build_message(
            event
        )

        # Convert UUIDs and other supported nested values into
        # JSON-safe values before storing the payload in PostgreSQL.
        metadata = self._make_json_safe(
            dict(event.payload)
        )

        # automation_run_id is stored in the dedicated run_id
        # database column and therefore does not need to remain
        # inside metadata.
        metadata.pop(
            "automation_run_id",
            None,
        )

        self.automation_service.log(
            run_id=run_id,
            event_type=event.type.value,
            message=message,
            level=level,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            error_code=error_code,
            metadata=metadata,
        )

    @staticmethod
    def _make_json_safe(
        value: Any,
    ) -> Any:
        """
        Convert event payload values into JSON-serializable values.

        UUID values are converted to strings.

        Nested dictionaries and lists are processed recursively so
        UUIDs cannot remain hidden inside complex event metadata.
        """

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, dict):
            return {
                str(key): AutomationEventLogger._make_json_safe(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                AutomationEventLogger._make_json_safe(
                    item
                )
                for item in value
            ]

        return value

    @staticmethod
    def _extract_run_id(
        payload: dict[str, Any],
    ) -> UUID | None:
        """
        Extract and validate automation_run_id from an event payload.
        """

        value = payload.get(
            "automation_run_id"
        )

        if value is None:
            return None

        if isinstance(value, UUID):
            return value

        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                return None

        return None

    @staticmethod
    def _extract_uuid(
        payload: dict[str, Any],
        key: str,
    ) -> UUID | None:
        """
        Extract an optional UUID field from an event payload.
        """

        value = payload.get(
            key
        )

        if value is None:
            return None

        if isinstance(value, UUID):
            return value

        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                return None

        return None

    @staticmethod
    def _extract_string(
        payload: dict[str, Any],
        key: str,
    ) -> str | None:
        """
        Extract an optional string field from an event payload.
        """

        value = payload.get(
            key
        )

        if value is None:
            return None

        return str(value)

    @staticmethod
    def _resolve_level(
        event_type: EventType,
    ) -> AutomationLogLevel:
        """
        Determine persistent automation log severity from event type.
        """

        if event_type in (
            EventType.APPLICATION_FAILED,
            EventType.CAPTCHA_DETECTED,
            EventType.AUTHENTICATION_REQUIRED,
        ):
            return AutomationLogLevel.ERROR

        if event_type in (
            EventType.JOB_DISCOVERED,
            EventType.JOB_MATCHED,
            EventType.APPLICATION_SUBMITTED,
        ):
            return AutomationLogLevel.INFO

        return AutomationLogLevel.INFO

    @staticmethod
    def _build_message(
        event: Event,
    ) -> str:
        """
        Build the persistent audit message for an event.
        """

        payload = event.payload

        explicit_message = payload.get(
            "message"
        )

        if explicit_message:
            return str(
                explicit_message
            )

        return (
            f"Automation event "
            f"'{event.type.value}' "
            "was received."
        )


def register_automation_event_logger(
    event_logger: AutomationEventLogger,
) -> None:
    """
    Register the automation logger with the global EventBus.

    These application events can become persistent automation
    audit records when they contain an automation_run_id.
    """

    from src.shared.events.event_bus import (
        get_event_bus,
    )

    event_bus = get_event_bus()

    event_types = (
        EventType.RESUME_UPLOADED,
        EventType.CANDIDATE_UPDATED,
        EventType.JOB_DISCOVERED,
        EventType.JOB_MATCHED,
        EventType.RESUME_TAILORED,
        EventType.APPLICATION_QUEUED,
        EventType.APPLICATION_SUBMITTED,
        EventType.APPLICATION_FAILED,
        EventType.AUTHENTICATION_REQUIRED,
        EventType.CAPTCHA_DETECTED,
        EventType.INTERVIEW_RECEIVED,
        EventType.NOTIFICATION_SENT,
        EventType.DASHBOARD_UPDATED,
    )

    for event_type in event_types:
        event_bus.subscribe(
            event_type,
            event_logger.handle,
        )