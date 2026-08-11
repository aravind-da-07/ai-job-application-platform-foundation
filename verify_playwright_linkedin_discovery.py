"""
Playwright -> LinkedIn discovery integration verification.

This test verifies the complete infrastructure path:

    BrowserEngine
        |
        v
    PlaywrightPortalSession
        |
        v
    LinkedInPortalAdapter
        |
        v
    LinkedIn search URL
        |
        v
    LinkedIn page
        |
        v
    LinkedInJobCardExtractor

The test does NOT use credentials and does NOT bypass
authentication, MFA, CAPTCHA, or other security controls.

If LinkedIn requires authentication, the test reports that
state and exits successfully after capturing diagnostics.
"""

from __future__ import annotations

from pathlib import Path

from src.modules.job_discovery.domain.entities.job_discovery import (
    JobSearchCriteria,
)
from src.modules.job_discovery.infrastructure.browser.playwright_portal_session import (
    PlaywrightPortalSession,
)
from src.modules.job_discovery.infrastructure.portals.linkedin.linkedin_portal import (
    LinkedInPortalAdapter,
)
from src.shared.browser import BrowserEngine


TEST_KEYWORDS = (
    "Data Analyst",
    "Business Analyst",
)

TEST_LOCATIONS = (
    "Hyderabad",
)

MAXIMUM_RESULTS = 3


def print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:
    print_header("PLAYWRIGHT LINKEDIN DISCOVERY INTEGRATION TEST")

    engine: BrowserEngine | None = None
    session: PlaywrightPortalSession | None = None
    tracing_started = False

    try:
        # --------------------------------------------------------------
        # 1. Search criteria
        # --------------------------------------------------------------

        print("[1/10] Creating search criteria...")

        criteria = JobSearchCriteria(
            keywords=TEST_KEYWORDS,
            locations=TEST_LOCATIONS,
            maximum_results=MAXIMUM_RESULTS,
        )

        print("SEARCH CRITERIA successful")
        print("Keywords:", criteria.keywords)
        print("Locations:", criteria.locations)
        print("Maximum results:", criteria.maximum_results)

        # --------------------------------------------------------------
        # 2. LinkedIn adapter
        # --------------------------------------------------------------

        print("[2/10] Creating LinkedIn adapter...")

        adapter = LinkedInPortalAdapter()

        print("LINKEDIN ADAPTER successful")
        print("Name:", adapter.name)
        print("Source:", adapter.source.value)
        print("Base URL:", adapter.base_url)

        # --------------------------------------------------------------
        # 3. Search URL generation
        # --------------------------------------------------------------

        print("[3/10] Building LinkedIn search URL...")

        search_urls = adapter.build_search_urls(criteria)

        assert search_urls, "LinkedIn search URL list is empty."

        print("SEARCH URL BUILD successful")

        for index, url in enumerate(search_urls, start=1):
            print(f"Search URL {index}: {url}")

        # --------------------------------------------------------------
        # 4. Browser engine
        # --------------------------------------------------------------

        print("[4/10] Starting BrowserEngine...")

        engine = BrowserEngine()

        print("Before start:", engine.running)

        engine.start()

        assert engine.running is True

        print("BROWSER ENGINE start successful")
        print("Running:", engine.running)

        # --------------------------------------------------------------
        # 5. Portal session
        # --------------------------------------------------------------

        print("[5/10] Creating Playwright portal session...")

        session = PlaywrightPortalSession(engine)

        assert session.running is False

        print("PORTAL SESSION creation successful")
        print("Running:", session.running)

        # --------------------------------------------------------------
        # 6. Start session
        # --------------------------------------------------------------

        print("[6/10] Starting Playwright portal session...")

        session.start()

        assert session.running is True

        print("PORTAL SESSION start successful")
        print("Running:", session.running)

        # --------------------------------------------------------------
        # 7. Start tracing
        # --------------------------------------------------------------

        print("[7/10] Starting Playwright tracing...")

        session.start_tracing(
            screenshots=True,
            snapshots=True,
            sources=True,
        )

        tracing_started = True

        print("TRACING started successfully")

        # --------------------------------------------------------------
        # 8. Navigate to LinkedIn search
        # --------------------------------------------------------------

        print("[8/10] Navigating to LinkedIn search page...")

        first_search_url = search_urls[0]

        print("Target URL:")
        print(first_search_url)

        adapter.open_url(
            session,
            first_search_url,
        )

        current_url = session.current_url()

        print("NAVIGATION successful")
        print("Current URL:", current_url)

        # --------------------------------------------------------------
        # 9. Inspect page / authentication / discovery
        # --------------------------------------------------------------

        print("[9/10] Inspecting LinkedIn page...")

        page_title = session.page.title()

        print("Page title:", page_title)

        authenticated = adapter.is_authenticated(session)

        print("Authenticated:", authenticated)

        screenshot_path = session.screenshot(
            name="linkedin-live-discovery-test.png",
            full_page=True,
        )

        print("Screenshot:", screenshot_path)

        if not authenticated:
            print()
            print("LINKEDIN AUTHENTICATION REQUIRED")
            print(
                "The page is not authenticated. "
                "No credentials or security controls were bypassed."
            )
            print(
                "Discovery extraction will not be treated as a "
                "successful live scrape."
            )

            return

        # --------------------------------------------------------------
        # Authenticated discovery
        # --------------------------------------------------------------

        result = adapter.discover_jobs(
            session,
            criteria,
        )

        print("LIVE DISCOVERY successful")
        print("Source:", result.source.value)
        print("Jobs returned:", len(result.jobs))
        print("Total found:", result.total_found)

        for index, job in enumerate(result.jobs, start=1):
            print()
            print(f"Job {index}")
            print("  External ID:", job.external_id)
            print("  Title:", job.title)
            print("  Company:", job.company_name)
            print("  Location:", job.location)
            print("  URL:", job.url)

        # --------------------------------------------------------------
        # 10. Final diagnostics
        # --------------------------------------------------------------

        print()
        print("[10/10] Finalizing diagnostics...")

    except Exception as exc:
        print()
        print("LIVE LINKEDIN INTEGRATION TEST ERROR")
        print(type(exc).__name__ + ":", exc)
        raise

    finally:
        # --------------------------------------------------------------
        # Stop tracing before closing the context.
        # --------------------------------------------------------------

        if session is not None and tracing_started:
            try:
                trace_path = session.stop_tracing(
                    name="linkedin-live-discovery-test-trace.zip",
                )
                print("Trace:", trace_path)
            except Exception as exc:
                print("WARNING: Failed to stop tracing:", exc)

        # --------------------------------------------------------------
        # Close portal session.
        # --------------------------------------------------------------

        if session is not None:
            try:
                session.close()
                print("PORTAL SESSION closed")
                print("Running:", session.running)
            except Exception as exc:
                print("WARNING: Failed to close portal session:", exc)

        # --------------------------------------------------------------
        # Shut down browser engine.
        # --------------------------------------------------------------

        if engine is not None:
            try:
                engine.shutdown()
                print("BROWSER ENGINE shut down")
                print("Running:", engine.running)
            except Exception as exc:
                print("WARNING: Failed to shut down browser engine:", exc)

    print()
    print("=" * 70)
    print("PLAYWRIGHT LINKEDIN DISCOVERY INTEGRATION TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()