"""
Browser infrastructure smoke tests.

These tests verify that BrowserEngine can:
    1. Start Playwright.
    2. Launch Chromium.
    3. Create an isolated browser context.
    4. Create a page.
    5. Navigate to a public test page.
    6. Read the page URL/title.
    7. Shut everything down cleanly.

These tests do not interact with LinkedIn.
"""

from __future__ import annotations

from src.shared.browser.browser_engine import BrowserEngine


def test_browser_engine_can_launch_and_navigate() -> None:
    """
    Verify that the real Playwright browser infrastructure works.
    """

    engine = BrowserEngine()

    try:
        engine.start()

        assert engine.running is True

        with engine.isolated_context() as context:
            page = engine.new_page(context)

            engine.navigate(
                page,
                "https://example.com",
            )

            assert "example.com" in page.url

            title = page.title()

            assert title == "Example Domain"

    finally:
        engine.shutdown()

    assert engine.running is False