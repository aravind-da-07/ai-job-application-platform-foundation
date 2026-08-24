"""
Integration tests for PlaywrightPortalSession.

These tests verify that the infrastructure session correctly adapts
Playwright pages to the generic PortalSession contract.
"""

from __future__ import annotations

from src.modules.job_discovery.infrastructure.browser.playwright_portal_session import (
    PlaywrightPortalSession,
)
from src.shared.browser.browser_engine import BrowserEngine


def test_playwright_portal_session_supports_basic_page_operations() -> None:
    """
    Verify navigation, URL access, text extraction, attributes,
    element counting, and clicking through the PortalSession adapter.
    """

    engine = BrowserEngine()

    try:
        engine.start()

        with PlaywrightPortalSession(engine) as session:
            session.navigate(
                "https://example.com"
            )

            assert "example.com" in session.current_url()

            heading = session.get_text("h1")

            assert heading == "Example Domain"

            paragraph = session.get_text("p")

            assert "documentation examples" in paragraph.lower()

            paragraphs = session.get_texts("p")

            assert len(paragraphs) >= 1

            link_count = session.get_element_count("a")

            assert link_count == 1

            link_href = session.get_attribute(
                "a",
                "href",
            )

            assert link_href is not None
            assert "iana.org" in link_href

    finally:
        engine.shutdown()

    assert engine.running is False