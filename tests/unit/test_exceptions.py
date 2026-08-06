from __future__ import annotations

import pytest

from src.shared.core.exceptions import (
    CaptchaDetectedError,
    PlatformError,
    RecordNotFoundError,
    ValidationError,
)


def test_platform_error_to_dict() -> None:
    err = ValidationError("Missing field", details={"field": "email"})
    payload = err.to_dict()
    assert payload == {
        "error": "validation_error",
        "message": "Missing field",
        "details": {"field": "email"},
    }


def test_subclasses_inherit_platform_error() -> None:
    assert issubclass(RecordNotFoundError, PlatformError)
    assert issubclass(CaptchaDetectedError, PlatformError)


def test_http_status_codes_are_distinct_and_sensible() -> None:
    assert RecordNotFoundError("x").http_status == 404
    assert CaptchaDetectedError("x").http_status == 423


def test_raising_and_catching_by_base_class() -> None:
    with pytest.raises(PlatformError):
        raise ValidationError("bad input")
