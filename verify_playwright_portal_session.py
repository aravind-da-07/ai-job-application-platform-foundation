"""
Playwright PortalSession integration test.

Validates the complete infrastructure bridge:

    BrowserEngine
        ↓
    BrowserContext
        ↓
    Page
        ↓
    PlaywrightPortalSession
        ↓
    PortalSession contract
"""

from __future__ import annotations

import base64

from src.modules.job_discovery.domain.ports.job_portal import (
    PortalSession,
)
from src.modules.job_discovery.infrastructure.browser import (
    PlaywrightPortalSession,
)
from src.shared.browser import BrowserEngine


TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Job Application Platform</title>
</head>
<body>
    <h1 id="title">Job Discovery Portal Test</h1>

    <p id="status">Ready</p>

    <button id="test-button" onclick="
        document.getElementById('status').innerText =
        'Portal session interaction successful.'
    ">
        Run Test
    </button>
</body>
</html>
"""


def main() -> None:
    print()
    print("=" * 70)
    print("PLAYWRIGHT PORTAL SESSION INTEGRATION TEST")
    print("=" * 70)

    html_base64 = base64.b64encode(
        TEST_HTML.encode("utf-8")
    ).decode("ascii")

    test_url = (
        "data:text/html;base64,"
        f"{html_base64}"
    )

    # --------------------------------------------------------------
    # 1. Browser engine
    # --------------------------------------------------------------

    print()
    print("[1/10] Creating browser engine...")

    engine = BrowserEngine()

    assert engine.running is False

    print("BROWSER ENGINE creation successful")
    print(f"Running: {engine.running}")

    # --------------------------------------------------------------
    # 2. Start engine
    # --------------------------------------------------------------

    print()
    print("[2/10] Starting browser engine...")

    engine.start()

    assert engine.running is True

    print("BROWSER ENGINE start successful")
    print(f"Running: {engine.running}")

    try:
        # ----------------------------------------------------------
        # 3. Create portal session
        # ----------------------------------------------------------

        print()
        print("[3/10] Creating Playwright portal session...")

        session = PlaywrightPortalSession(
            engine
        )

        assert isinstance(
            session,
            PortalSession,
        )

        assert session.running is False

        print("PORTAL SESSION creation successful")
        print(
            f"Implements PortalSession: "
            f"{isinstance(session, PortalSession)}"
        )
        print(f"Running: {session.running}")

        # ----------------------------------------------------------
        # 4. Start portal session
        # ----------------------------------------------------------

        print()
        print("[4/10] Starting isolated portal session...")

        session.start()

        assert session.running is True

        print("PORTAL SESSION start successful")
        print(f"Running: {session.running}")

        # ----------------------------------------------------------
        # 5. Navigate
        # ----------------------------------------------------------

        print()
        print("[5/10] Navigating to local test page...")

        session.navigate(
            test_url
        )

        assert session.current_url().startswith(
            "data:text/html;base64,"
        )

        print("PORTAL NAVIGATION successful")
        print(
            f"Current URL: {session.current_url()[:70]}..."
        )

        # ----------------------------------------------------------
        # 6. Read page content
        # ----------------------------------------------------------

        print()
        print("[6/10] Reading page content...")

        title = session.get_text(
            "#title"
        )

        status = session.get_text(
            "#status"
        )

        assert title == "Job Discovery Portal Test"
        assert status == "Ready"

        print("PAGE CONTENT successful")
        print(f"Title: {title}")
        print(f"Status: {status}")

        # ----------------------------------------------------------
        # 7. Click interaction
        # ----------------------------------------------------------

        print()
        print("[7/10] Testing page interaction...")

        session.click(
            "#test-button"
        )

        updated_status = session.get_text(
            "#status"
        )

        assert (
            updated_status
            == "Portal session interaction successful."
        )

        print("PAGE INTERACTION successful")
        print(f"Updated status: {updated_status}")

        # ----------------------------------------------------------
        # 8. Screenshot
        # ----------------------------------------------------------

        print()
        print("[8/10] Capturing screenshot...")

        screenshot = session.screenshot(
            name="portal-session-test.png"
        )

        assert screenshot.exists()

        print("SCREENSHOT successful")
        print(f"Screenshot: {screenshot}")

        # ----------------------------------------------------------
        # 9. Tracing
        # ----------------------------------------------------------

        print()
        print("[9/10] Testing Playwright tracing...")

        session.start_tracing()

        session.navigate(
            test_url
        )

        trace = session.stop_tracing(
            name="portal-session-test-trace.zip"
        )

        assert trace.exists()

        print("TRACING successful")
        print(f"Trace: {trace}")

        # ----------------------------------------------------------
        # 10. Close session
        # ----------------------------------------------------------

        print()
        print("[10/10] Closing portal session...")

        session.close()

        assert session.running is False

        print("PORTAL SESSION shutdown successful")
        print(f"Running: {session.running}")

    finally:
        engine.shutdown()

    assert engine.running is False

    print()
    print("=" * 70)
    print("PLAYWRIGHT PORTAL SESSION INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()