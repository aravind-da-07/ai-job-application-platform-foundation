"""
LinkedIn live DOM diagnostic.

Purpose:
    Inspect the actual DOM returned by LinkedIn through Playwright
    before changing the production job-card extractor.

This script does not:
    - submit applications
    - bypass authentication
    - bypass CAPTCHA
    - bypass MFA
    - enter credentials

It only navigates to the configured public/search page and records
DOM diagnostics.
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


OUTPUT_DIR = Path("browser_sessions") / "linkedin_dom_diagnostic"


def print_section(number: int, title: str) -> None:
    print()
    print("=" * 70)
    print(f"[{number}] {title}")
    print("=" * 70)


def main() -> None:
    engine: BrowserEngine | None = None
    session: PlaywrightPortalSession | None = None
    tracing_started = False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # --------------------------------------------------------------
        # 1. Search criteria
        # --------------------------------------------------------------

        print_section(1, "Creating search criteria")

        criteria = JobSearchCriteria(
            keywords=(
                "Data Analyst",
                "Business Analyst",
            ),
            locations=(
                "Hyderabad",
            ),
            maximum_results=5,
        )

        print("Keywords:", criteria.keywords)
        print("Locations:", criteria.locations)
        print("Maximum results:", criteria.maximum_results)

        # --------------------------------------------------------------
        # 2. LinkedIn adapter
        # --------------------------------------------------------------

        print_section(2, "Creating LinkedIn adapter")

        adapter = LinkedInPortalAdapter()

        print("Name:", adapter.name)
        print("Source:", adapter.source.value)
        print("Base URL:", adapter.base_url)

        # --------------------------------------------------------------
        # 3. Build search URL
        # --------------------------------------------------------------

        print_section(3, "Building search URL")

        search_urls = adapter.build_search_urls(criteria)

        if not search_urls:
            raise RuntimeError("No LinkedIn search URL was generated.")

        search_url = search_urls[0]

        print("Search URL:")
        print(search_url)

        # --------------------------------------------------------------
        # 4. Start browser
        # --------------------------------------------------------------

        print_section(4, "Starting BrowserEngine")

        engine = BrowserEngine()
        engine.start()

        print("Browser running:", engine.running)

        # --------------------------------------------------------------
        # 5. Create session
        # --------------------------------------------------------------

        print_section(5, "Creating Playwright portal session")

        session = PlaywrightPortalSession(engine)
        session.start()

        print("Session running:", session.running)

        # --------------------------------------------------------------
        # 6. Start tracing
        # --------------------------------------------------------------

        print_section(6, "Starting tracing")

        session.start_tracing(
            screenshots=True,
            snapshots=True,
            sources=True,
        )

        tracing_started = True

        print("Tracing started")

        # --------------------------------------------------------------
        # 7. Navigate
        # --------------------------------------------------------------

        print_section(7, "Navigating to LinkedIn search")

        adapter.open_url(
            session,
            search_url,
        )

        print("Current URL:")
        print(session.current_url())

        print("Page title:")
        print(session.page.title())

        authenticated = adapter.is_authenticated(session)

        print("Authenticated:", authenticated)

        if not authenticated:
            print()
            print("LinkedIn authentication is required.")
            print("No extraction will be attempted.")
            return

        # Give dynamic content a short opportunity to render.
        session.page.wait_for_timeout(3000)

        # --------------------------------------------------------------
        # 8. Inspect candidate selectors
        # --------------------------------------------------------------

        print_section(8, "Inspecting candidate DOM selectors")

        selectors = [
            "article",
            "li",
            "[data-job-id]",
            "[data-entity-urn]",
            "[data-occludable-job-id]",
            "a[href*='/jobs/view/']",
            "h3",
            "h4",
            "[class*='job']",
            "[class*='base-search-card']",
            "[class*='job-search-card']",
            "[class*='jobs-search']",
        ]

        for selector in selectors:
            try:
                count = session.page.locator(selector).count()
                print(f"{selector:<45} -> {count}")
            except Exception as exc:
                print(
                    f"{selector:<45} -> ERROR: {type(exc).__name__}: {exc}"
                )

        # --------------------------------------------------------------
        # 9. Inspect job links
        # --------------------------------------------------------------

        print_section(9, "Inspecting job links and surrounding HTML")

        job_links = session.page.locator(
            "a[href*='/jobs/view/']"
        )

        job_link_count = job_links.count()

        print("Job links found:", job_link_count)

        limit = min(job_link_count, 10)

        for index in range(limit):
            link = job_links.nth(index)

            try:
                href = link.get_attribute("href")
            except Exception:
                href = None

            try:
                text = link.inner_text()
            except Exception:
                text = ""

            try:
                outer_html = link.evaluate(
                    "(element) => element.outerHTML"
                )
            except Exception:
                outer_html = ""

            print()
            print("-" * 70)
            print(f"JOB LINK {index + 1}")
            print("HREF:", href)
            print("TEXT:", text[:300])
            print("OUTER HTML:")
            print(outer_html[:2000])

        # --------------------------------------------------------------
        # Inspect articles
        # --------------------------------------------------------------

        articles = session.page.locator("article")

        article_count = articles.count()

        print()
        print("Article count:", article_count)

        limit = min(article_count, 10)

        for index in range(limit):
            article = articles.nth(index)

            try:
                html = article.evaluate(
                    "(element) => element.outerHTML"
                )
            except Exception:
                html = ""

            print()
            print("-" * 70)
            print(f"ARTICLE {index + 1}")
            print(html[:3000])

        # --------------------------------------------------------------
        # 10. Save diagnostics
        # --------------------------------------------------------------

        print_section(10, "Saving diagnostics")

        screenshot_path = session.screenshot(
            name=str(
                OUTPUT_DIR / "linkedin-live-dom.png"
            ),
            full_page=True,
        )

        print("Screenshot:")
        print(screenshot_path)

        html_path = OUTPUT_DIR / "linkedin-live-dom.html"

        html_content = session.page.content()

        html_path.write_text(
            html_content,
            encoding="utf-8",
        )

        print("HTML:")
        print(html_path)

        metadata_path = OUTPUT_DIR / "linkedin-live-dom.txt"

        metadata_path.write_text(
            "\n".join(
                [
                    f"URL: {session.current_url()}",
                    f"Title: {session.page.title()}",
                    f"Authenticated: {authenticated}",
                    f"Job links: {job_link_count}",
                    f"Articles: {article_count}",
                ]
            ),
            encoding="utf-8",
        )

        print("Metadata:")
        print(metadata_path)

    except Exception as exc:
        print()
        print("=" * 70)
        print("DIAGNOSTIC ERROR")
        print("=" * 70)
        print(type(exc).__name__ + ":", exc)
        raise

    finally:
        # Stop tracing before session shutdown.
        if session is not None and tracing_started:
            try:
                trace_path = session.stop_tracing(
                    name=str(
                        OUTPUT_DIR
                        / "linkedin-live-dom-trace.zip"
                    )
                )

                print()
                print("Trace:")
                print(trace_path)

            except Exception as exc:
                print(
                    "WARNING: Could not stop tracing:",
                    exc,
                )

        # Close session.
        if session is not None:
            try:
                session.close()
                print("Portal session closed.")
            except Exception as exc:
                print(
                    "WARNING: Could not close session:",
                    exc,
                )

        # Shut down browser.
        if engine is not None:
            try:
                engine.shutdown()
                print("Browser engine shut down.")
            except Exception as exc:
                print(
                    "WARNING: Could not shut down browser:",
                    exc,
                )

    print()
    print("=" * 70)
    print("LINKEDIN LIVE DOM DIAGNOSTIC COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()