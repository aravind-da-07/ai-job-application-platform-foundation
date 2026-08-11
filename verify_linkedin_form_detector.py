"""
LinkedIn application form detector integration test.

Uses a fake Playwright-like page so the detector can be tested without
opening LinkedIn or submitting an application.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormType,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.form import (
    LinkedInApplicationFormDetector,
)


@dataclass
class FakeElement:
    visible: bool = True
    attributes: dict[str, str] | None = None
    text: str = ""

    def __post_init__(self) -> None:
        if self.attributes is None:
            self.attributes = {}

    def is_visible(self) -> bool:
        return self.visible

    def get_attribute(
        self,
        name: str,
    ) -> str | None:
        return self.attributes.get(name)

    def inner_text(self) -> str:
        return self.text


class FakeLocator:
    def __init__(
        self,
        elements: list[FakeElement],
    ) -> None:
        self.elements = elements

    def count(self) -> int:
        return len(self.elements)

    def nth(
        self,
        index: int,
    ) -> FakeElement:
        return self.elements[index]

    @property
    def first(self) -> FakeElement:
        return self.elements[0]


class FakePage:
    """
    Small Playwright-like fake page.

    selectors maps CSS selectors to fake elements.
    """

    def __init__(
        self,
        *,
        url: str = "https://www.linkedin.com/jobs/view/test",
        title: str = "Test Job",
        selectors: dict[str, list[FakeElement]] | None = None,
    ) -> None:
        self.url = url
        self.title = title
        self.selectors = selectors or {}

    def locator(
        self,
        selector: str,
    ) -> FakeLocator:
        return FakeLocator(
            self.selectors.get(
                selector,
                [],
            )
        )


def test_authentication_required() -> None:
    page = FakePage(
        selectors={
            "input[name='session_key']": [
                FakeElement()
            ],
        }
    )

    snapshot = LinkedInApplicationFormDetector(
        page
    ).detect()

    assert (
        snapshot.form_type
        == ApplicationFormType.AUTHENTICATION_REQUIRED
    )

    assert snapshot.requires_authentication is True
    assert snapshot.detected is False

    print("AUTHENTICATION detection successful")
    print("Form type:", snapshot.form_type.value)


def test_captcha_detected() -> None:
    page = FakePage(
        selectors={
            "[id*='captcha']": [
                FakeElement()
            ],
        }
    )

    snapshot = LinkedInApplicationFormDetector(
        page
    ).detect()

    assert (
        snapshot.form_type
        == ApplicationFormType.CAPTCHA_DETECTED
    )

    assert snapshot.captcha_detected is True
    assert snapshot.detected is False

    print("CAPTCHA detection successful")
    print("Form type:", snapshot.form_type.value)


def test_easy_apply() -> None:
    page = FakePage(
        title="Data Analyst - Test Company",
        selectors={
            "button.jobs-apply-button": [
                FakeElement()
            ],
            "input": [
                FakeElement(
                    attributes={
                        "id": "first-name",
                        "name": "first_name",
                        "type": "text",
                        "aria-label": "First name",
                        "required": "true",
                    }
                ),
                FakeElement(
                    attributes={
                        "id": "email",
                        "name": "email",
                        "type": "email",
                        "aria-label": "Email",
                        "required": "true",
                    }
                ),
            ],
            "textarea": [
                FakeElement(
                    attributes={
                        "id": "summary",
                        "name": "summary",
                        "placeholder": "Professional summary",
                    }
                ),
            ],
            ".job-details-jobs-unified-top-card__company-name": [
                FakeElement(
                    text="Test Company"
                )
            ],
        },
    )

    snapshot = LinkedInApplicationFormDetector(
        page
    ).detect()

    assert (
        snapshot.form_type
        == ApplicationFormType.EASY_APPLY
    )

    assert snapshot.detected is True
    assert snapshot.captcha_detected is False
    assert snapshot.requires_authentication is False

    assert snapshot.field_count == 3

    assert snapshot.company_name == "Test Company"

    labels = {
        field.label
        for field in snapshot.fields
    }

    assert "First name" in labels
    assert "Email" in labels
    assert "Professional summary" in labels

    print("EASY APPLY detection successful")
    print("Form type:", snapshot.form_type.value)
    print("Fields detected:", snapshot.field_count)
    print("Company:", snapshot.company_name)


def test_external_application() -> None:
    page = FakePage(
        selectors={
            "a[href*='apply']": [
                FakeElement()
            ],
        }
    )

    snapshot = LinkedInApplicationFormDetector(
        page
    ).detect()

    assert (
        snapshot.form_type
        == ApplicationFormType.EXTERNAL_APPLICATION
    )

    assert snapshot.detected is True
    assert snapshot.field_count == 0

    print("EXTERNAL APPLICATION detection successful")
    print("Form type:", snapshot.form_type.value)


def test_unknown_flow() -> None:
    page = FakePage()

    snapshot = LinkedInApplicationFormDetector(
        page
    ).detect()

    assert (
        snapshot.form_type
        == ApplicationFormType.MANUAL_REVIEW_REQUIRED
    )

    assert snapshot.detected is False

    print("UNKNOWN FLOW handling successful")
    print("Form type:", snapshot.form_type.value)


def main() -> None:
    print()
    print("=" * 70)
    print("LINKEDIN APPLICATION FORM DETECTOR INTEGRATION TEST")
    print("=" * 70)

    print()
    print("[1/5] Testing authentication detection...")
    test_authentication_required()

    print()
    print("[2/5] Testing CAPTCHA detection...")
    test_captcha_detected()

    print()
    print("[3/5] Testing Easy Apply detection...")
    test_easy_apply()

    print()
    print("[4/5] Testing external application detection...")
    test_external_application()

    print()
    print("[5/5] Testing unknown application flow...")
    test_unknown_flow()

    print()
    print("=" * 70)
    print("LINKEDIN APPLICATION FORM DETECTOR TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()