"""
Playwright browser engine integration test.

Tests the shared browser infrastructure without depending on any
external job portal.

Coverage:
1. Browser configuration
2. Browser engine creation
3. Browser startup
4. Isolated browser context
5. Page creation
6. Local page navigation
7. Page interaction/content verification
8. Screenshot capture
9. Playwright tracing
10. Browser/context cleanup
"""

from __future__ import annotations

import base64

from src.shared.browser import BrowserConfig, BrowserEngine


def main() -> None:
    print()
    print("=" * 70)
    print("PLAYWRIGHT BROWSER ENGINE INTEGRATION TEST")
    print("=" * 70)

    engine: BrowserEngine | None = None

    try:
        # --------------------------------------------------------------
        # 1. Browser configuration
        # --------------------------------------------------------------

        print()
        print("[1/10] Loading browser configuration...")

        config = BrowserConfig.from_settings()

        print("BROWSER CONFIGURATION successful")
        print(f"Browser type: {config.browser_type.value}")
        print(f"Headless: {config.headless}")
        print(f"Slow motion: {config.slow_mo_ms} ms")
        print(
            "Navigation timeout: "
            f"{config.navigation_timeout_ms} ms"
        )
        print(f"Sessions directory: {config.sessions_dir}")

        # --------------------------------------------------------------
        # 2. Browser engine creation
        # --------------------------------------------------------------

        print()
        print("[2/10] Creating browser engine...")

        engine = BrowserEngine(config)

        assert engine.running is False

        print("BROWSER ENGINE CREATION successful")
        print(f"Running: {engine.running}")

        # --------------------------------------------------------------
        # 3. Browser startup
        # --------------------------------------------------------------

        print()
        print("[3/10] Starting browser...")

        engine.start()

        assert engine.running is True

        print("BROWSER START successful")
        print(f"Running: {engine.running}")

        # --------------------------------------------------------------
        # 4. Isolated context
        # --------------------------------------------------------------

        print()
        print("[4/10] Creating isolated browser context...")

        with engine.isolated_context() as context:
            print("BROWSER CONTEXT creation successful")

            # ----------------------------------------------------------
            # 5. Page creation
            # ----------------------------------------------------------

            print()
            print("[5/10] Creating browser page...")

            page = engine.new_page(context)

            assert page is not None

            print("PAGE CREATION successful")
            print(f"Initial URL: {page.url}")

            # ----------------------------------------------------------
            # 6. Local page navigation
            # ----------------------------------------------------------

            print()
            print("[6/10] Navigating to local test page...")

            html = """
            <!DOCTYPE html>
            <html>
                <head>
                    <title>AI Job Application Platform</title>
                </head>

                <body>
                    <main>
                        <h1 id="title">
                            AI Job Application Platform
                        </h1>

                        <p id="status">
                            Playwright engine test successful.
                        </p>

                        <button id="test-button">
                            Test Button
                        </button>

                        <p id="button-result"></p>

                        <script>
                            document
                                .getElementById("test-button")
                                .addEventListener("click", function () {
                                    document
                                        .getElementById("button-result")
                                        .textContent =
                                        "Button interaction successful.";
                                });
                        </script>
                    </main>
                </body>
            </html>
            """

            encoded_html = base64.b64encode(
                html.encode("utf-8")
            ).decode("ascii")

            data_url = (
                "data:text/html;base64,"
                f"{encoded_html}"
            )

            engine.navigate(
                page,
                data_url,
            )

            assert (
                page.title()
                == "AI Job Application Platform"
            )

            print("LOCAL NAVIGATION successful")
            print(f"Page title: {page.title()}")
            print(f"Page URL: {page.url[:80]}...")

            # ----------------------------------------------------------
            # 7. Page interaction
            # ----------------------------------------------------------

            print()
            print("[7/10] Verifying page content and interaction...")

            title_text = page.locator(
                "#title"
            ).inner_text()

            status_text = page.locator(
                "#status"
            ).inner_text()

            assert (
                title_text
                == "AI Job Application Platform"
            )

            assert (
                status_text
                == "Playwright engine test successful."
            )

            page.locator(
                "#test-button"
            ).click()

            button_result = page.locator(
                "#button-result"
            ).inner_text()

            assert (
                button_result
                == "Button interaction successful."
            )

            print("PAGE INTERACTION successful")
            print(f"Title: {title_text}")
            print(f"Status: {status_text}")
            print(f"Interaction: {button_result}")

            # ----------------------------------------------------------
            # 8. Screenshot
            # ----------------------------------------------------------

            print()
            print("[8/10] Capturing screenshot...")

            screenshot_path = engine.screenshot(
                page,
                name="playwright-engine-test.png",
                full_page=True,
            )

            assert screenshot_path.exists()
            assert screenshot_path.is_file()

            print("SCREENSHOT successful")
            print(f"Screenshot: {screenshot_path}")

            # ----------------------------------------------------------
            # 9. Tracing
            # ----------------------------------------------------------

            print()
            print("[9/10] Testing Playwright tracing...")

            engine.start_tracing(
                context,
                screenshots=True,
                snapshots=True,
                sources=True,
            )

            # Perform one additional operation while tracing.
            page.locator(
                "#title"
            ).inner_text()

            trace_path = engine.stop_tracing(
                context,
                name="playwright-engine-test-trace.zip",
            )

            assert trace_path.exists()
            assert trace_path.is_file()

            print("TRACING successful")
            print(f"Trace: {trace_path}")

        # Context automatically closes here.

        print()
        print("BROWSER CONTEXT CLEANUP successful")

        # --------------------------------------------------------------
        # 10. Browser shutdown
        # --------------------------------------------------------------

        print()
        print("[10/10] Shutting down browser engine...")

        engine.shutdown()

        assert engine.running is False

        print("BROWSER SHUTDOWN successful")
        print(f"Running: {engine.running}")

        print()
        print("=" * 70)
        print("PLAYWRIGHT ENGINE INTEGRATION TEST PASSED")
        print("=" * 70)
        print()

    except Exception:
        print()
        print("=" * 70)
        print("PLAYWRIGHT ENGINE INTEGRATION TEST FAILED")
        print("=" * 70)
        print()
        raise

    finally:
        if engine is not None and engine.running:
            engine.shutdown()


if __name__ == "__main__":
    main()