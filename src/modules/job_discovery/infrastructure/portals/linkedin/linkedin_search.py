"""
LinkedIn search and job-card extraction utilities.

This module contains LinkedIn-specific infrastructure behavior.

Responsibilities:
    - Build deterministic LinkedIn job-search URLs.
    - Extract normalized DiscoveredJob objects from a PortalSession.
    - Support the local integration-test DOM.
    - Support the live LinkedIn search-result DOM.
    - Keep title/company/location associated with the correct job URL.
    - Remove duplicate job records.
    - Respect maximum-result limits.

The module does not import Playwright directly.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin, urlparse

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    PortalSession,
)
from src.shared.config.constants import JobSourceType


class LinkedInSearchBuilder:
    """
    Build LinkedIn job-search URLs.

    The builder does not perform navigation.
    """

    SEARCH_PATH = "/jobs/search/"

    def __init__(
        self,
        *,
        base_url: str = "https://www.linkedin.com",
    ) -> None:
        normalized_url = base_url.strip().rstrip("/")

        if not normalized_url:
            raise ValueError(
                "LinkedIn base URL cannot be empty."
            )

        parsed = urlparse(normalized_url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "LinkedIn base URL must use http or https."
            )

        if not parsed.netloc:
            raise ValueError(
                "LinkedIn base URL must contain a valid host."
            )

        self.base_url = normalized_url

    def build_url(
        self,
        *,
        keywords: str,
        location: str | None = None,
    ) -> str:
        """
        Build one LinkedIn search URL.
        """

        normalized_keywords = keywords.strip()

        if not normalized_keywords:
            raise ValueError(
                "Search keywords cannot be empty."
            )

        params: dict[str, str] = {
            "keywords": normalized_keywords,
        }

        if location is not None:
            normalized_location = location.strip()

            if normalized_location:
                params["location"] = normalized_location

        query_string = urlencode(params)

        return (
            f"{self.base_url}"
            f"{self.SEARCH_PATH}"
            f"?{query_string}"
        )

    def build_urls(
        self,
        criteria: JobSearchCriteria,
    ) -> tuple[str, ...]:
        """
        Build one LinkedIn search URL for each requested location.

        Multiple keywords are combined using an OR expression.
        """

        if not criteria.keywords:
            raise ValueError(
                "At least one keyword is required."
            )

        keyword_parts = tuple(
            keyword.strip()
            for keyword in criteria.keywords
            if keyword.strip()
        )

        if not keyword_parts:
            raise ValueError(
                "Search keywords cannot be empty."
            )

        keyword_expression = " OR ".join(
            keyword_parts
        )

        location_parts = tuple(
            location.strip()
            for location in criteria.locations
            if location.strip()
        )

        if not location_parts:
            return (
                self.build_url(
                    keywords=keyword_expression,
                ),
            )

        return tuple(
            self.build_url(
                keywords=keyword_expression,
                location=location,
            )
            for location in location_parts
        )


class LinkedInJobCardExtractor:
    """
    Extract normalized jobs from a LinkedIn PortalSession.

    Supported DOM strategies:

    1. Local integration-test DOM

        article[data-job-id]

    2. Live LinkedIn search-result DOM

        Job cards containing links such as:

            /jobs/view/<job-id>

    The live extractor treats each job card as the record boundary.
    This is important because querying title/company/location globally
    can associate the first job's title with every subsequent job.
    """

    # ------------------------------------------------------------------
    # Local integration-test selectors
    # ------------------------------------------------------------------

    DEFAULT_CARD_SELECTOR = (
        "article[data-job-id]"
    )

    DEFAULT_ID_SELECTOR = (
        "article[data-job-id]"
    )

    DEFAULT_TITLE_SELECTOR = (
        "article[data-job-id] .job-title"
    )

    DEFAULT_COMPANY_SELECTOR = (
        "article[data-job-id] .job-company"
    )

    DEFAULT_LOCATION_SELECTOR = (
        "article[data-job-id] .job-location"
    )

    DEFAULT_LINK_SELECTOR = (
        "article[data-job-id] a.job-link"
    )

    # ------------------------------------------------------------------
    # Live LinkedIn selectors
    # ------------------------------------------------------------------

    LIVE_JOB_LINK_SELECTOR = (
        "a[href*='/jobs/view/']"
    )

    LIVE_JOB_CARD_SELECTORS = (
        "li:has(a[href*='/jobs/view/'])",
        "div.base-card:has(a[href*='/jobs/view/'])",
        "div.job-search-card:has(a[href*='/jobs/view/'])",
        "div:has(a[href*='/jobs/view/'])",
    )

    LIVE_TITLE_SELECTORS = (
        "h3",
        "h4",
        ".base-search-card__title",
        ".job-search-card__title",
        "[class*='job-search-card__title']",
        "[class*='base-search-card__title']",
    )

    LIVE_COMPANY_SELECTORS = (
        "h4",
        ".base-search-card__subtitle",
        ".job-search-card__company-name",
        "[class*='job-search-card__company']",
        "[class*='base-search-card__subtitle']",
    )

    LIVE_LOCATION_SELECTORS = (
        ".job-search-card__location",
        ".base-search-card__metadata",
        "[class*='job-search-card__location']",
        "[class*='base-search-card__metadata']",
        ".location",
    )

    def __init__(
        self,
        *,
        card_selector: str = DEFAULT_CARD_SELECTOR,
        id_selector: str = DEFAULT_ID_SELECTOR,
        title_selector: str = DEFAULT_TITLE_SELECTOR,
        company_selector: str = DEFAULT_COMPANY_SELECTOR,
        location_selector: str = DEFAULT_LOCATION_SELECTOR,
        link_selector: str = DEFAULT_LINK_SELECTOR,
        base_url: str = "https://www.linkedin.com",
    ) -> None:
        self.card_selector = card_selector
        self.id_selector = id_selector
        self.title_selector = title_selector
        self.company_selector = company_selector
        self.location_selector = location_selector
        self.link_selector = link_selector
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public extraction entry point
    # ------------------------------------------------------------------

    def extract(
        self,
        session: PortalSession,
        *,
        maximum_results: int = 50,
    ) -> tuple[DiscoveredJob, ...]:
        """
        Extract normalized jobs from the current page.

        The extractor first attempts the deterministic local/test DOM.

        If that DOM is not present, the live LinkedIn DOM strategy
        is used.
        """

        if maximum_results < 1:
            raise ValueError(
                "maximum_results must be greater than zero."
            )

        # --------------------------------------------------------------
        # First: local integration-test format
        # --------------------------------------------------------------

        local_jobs = self._extract_local_dom(
            session,
            maximum_results=maximum_results,
        )

        if local_jobs:
            return local_jobs

        # --------------------------------------------------------------
        # Second: live LinkedIn format
        # --------------------------------------------------------------

        return self._extract_live_dom(
            session,
            maximum_results=maximum_results,
        )

    # ------------------------------------------------------------------
    # Local/test DOM extraction
    # ------------------------------------------------------------------

    def _extract_local_dom(
        self,
        session: PortalSession,
        *,
        maximum_results: int,
    ) -> tuple[DiscoveredJob, ...]:
        """
        Extract jobs from the deterministic local integration-test DOM.

        This preserves the existing Sprint 5 test behavior.
        """

        external_ids = session.get_attributes(
            self.id_selector,
            "data-job-id",
        )

        titles = session.get_texts(
            self.title_selector,
        )

        companies = session.get_texts(
            self.company_selector,
        )

        locations = session.get_texts(
            self.location_selector,
        )

        links = session.get_attributes(
            self.link_selector,
            "href",
        )

        field_lengths = {
            "external_ids": len(external_ids),
            "titles": len(titles),
            "companies": len(companies),
            "locations": len(locations),
            "links": len(links),
        }

        # No local DOM detected.
        if not any(field_lengths.values()):
            return ()

        required_lengths = {
            "external_ids": len(external_ids),
            "titles": len(titles),
            "companies": len(companies),
            "links": len(links),
        }

        unique_required_lengths = set(
            required_lengths.values()
        )

        if len(unique_required_lengths) != 1:
            raise ValueError(
                "LinkedIn job-card fields are not aligned: "
                f"{field_lengths}"
            )

        record_count = next(
            iter(unique_required_lengths)
        )

        normalized_locations: list[str | None] = []

        for index in range(record_count):
            if index < len(locations):
                location = (
                    locations[index] or ""
                ).strip()

                normalized_locations.append(
                    location or None
                )
            else:
                normalized_locations.append(
                    None
                )

        jobs: list[DiscoveredJob] = []

        limit = min(
            record_count,
            maximum_results,
        )

        seen_ids: set[str] = set()

        for index in range(limit):
            external_id = (
                external_ids[index] or ""
            ).strip()

            title = (
                titles[index] or ""
            ).strip()

            company_name = (
                companies[index] or ""
            ).strip()

            href = (
                links[index] or ""
            ).strip()

            location = normalized_locations[index]

            if not external_id:
                continue

            if not title:
                continue

            if not company_name:
                continue

            if not href:
                continue

            if external_id in seen_ids:
                continue

            seen_ids.add(external_id)

            job_url = urljoin(
                f"{self.base_url}/",
                href,
            )

            jobs.append(
                DiscoveredJob(
                    external_id=external_id,
                    title=title,
                    company_name=company_name,
                    source=JobSourceType.LINKEDIN,
                    url=job_url,
                    location=location,
                    metadata={
                        "portal": "LinkedIn",
                        "extraction_mode": "local",
                    },
                )
            )

        return tuple(jobs)

    # ------------------------------------------------------------------
    # Live LinkedIn DOM extraction
    # ------------------------------------------------------------------

    def _extract_live_dom(
        self,
        session: PortalSession,
        *,
        maximum_results: int,
    ) -> tuple[DiscoveredJob, ...]:
        """
        Extract jobs from the live LinkedIn search-result DOM.

        IMPORTANT:

        We do not query all titles, all companies and all locations
        independently and then zip them together.

        Instead, we first identify individual job cards and then query
        the fields inside each card. This prevents a common scraping
        error where Job #2 receives Job #1's title/company.
        """

        card_selector = self._find_live_card_selector(
            session
        )

        if card_selector:
            jobs = self._extract_live_cards(
                session,
                card_selector=card_selector,
                maximum_results=maximum_results,
            )

            if jobs:
                return jobs

        # --------------------------------------------------------------
        # Fallback strategy
        #
        # Some LinkedIn page variants may not expose a convenient
        # card wrapper through the generic PortalSession contract.
        #
        # In that case, use the job links as boundaries and derive
        # aligned fields from selector lists.
        # --------------------------------------------------------------

        return self._extract_live_aligned(
            session,
            maximum_results=maximum_results,
        )

    # ------------------------------------------------------------------
    # Live card detection
    # ------------------------------------------------------------------

    def _find_live_card_selector(
        self,
        session: PortalSession,
    ) -> str | None:
        """
        Find a live LinkedIn card selector that returns job cards.

        The generic PortalSession exposes text/attribute collection,
        so we detect a selector by checking whether it contains
        at least one LinkedIn job link.
        """

        for selector in self.LIVE_JOB_CARD_SELECTORS:
            try:
                hrefs = session.get_attributes(
                    f"{selector} a[href*='/jobs/view/']",
                    "href",
                )
            except Exception:
                continue

            valid_hrefs = [
                href
                for href in hrefs
                if href
                and "/jobs/view/" in href
            ]

            if valid_hrefs:
                return selector

        return None

    # ------------------------------------------------------------------
    # Live card extraction
    # ------------------------------------------------------------------

    def _extract_live_cards(
        self,
        session: PortalSession,
        *,
        card_selector: str,
        maximum_results: int,
    ) -> tuple[DiscoveredJob, ...]:
        """
        Extract jobs while preserving card-level association.

        Every field is queried beneath the same card selector.
        """

        card_link_selector = (
            f"{card_selector} "
            "a[href*='/jobs/view/']"
        )

        links = self._safe_get_attributes(
            session,
            card_link_selector,
            "href",
        )

        if not links:
            return ()

        # Try multiple title/company/location combinations.
        field_combinations = (
            (
                "h3",
                "h4",
                ".job-search-card__location",
            ),
            (
                "h3",
                "h4",
                ".base-search-card__metadata",
            ),
            (
                ".base-search-card__title",
                ".base-search-card__subtitle",
                ".job-search-card__location",
            ),
            (
                ".job-search-card__title",
                ".job-search-card__company-name",
                ".job-search-card__location",
            ),
            (
                "[class*='job-search-card__title']",
                "[class*='job-search-card__company']",
                "[class*='job-search-card__location']",
            ),
            (
                "[class*='base-search-card__title']",
                "[class*='base-search-card__subtitle']",
                "[class*='base-search-card__metadata']",
            ),
        )

        for (
            title_selector,
            company_selector,
            location_selector,
        ) in field_combinations:

            titles = self._safe_get_texts(
                session,
                f"{card_selector} {title_selector}",
            )

            companies = self._safe_get_texts(
                session,
                f"{card_selector} {company_selector}",
            )

            locations = self._safe_get_texts(
                session,
                f"{card_selector} {location_selector}",
            )

            if not self._fields_can_be_aligned(
                links,
                titles,
                companies,
            ):
                continue

            return self._build_live_jobs(
                links=links,
                titles=titles,
                companies=companies,
                locations=locations,
                maximum_results=maximum_results,
            )

        return ()

    # ------------------------------------------------------------------
    # Live aligned fallback
    # ------------------------------------------------------------------

    def _extract_live_aligned(
        self,
        session: PortalSession,
        *,
        maximum_results: int,
    ) -> tuple[DiscoveredJob, ...]:
        """
        Fallback live extraction when a card wrapper is unavailable.

        We still require the main field collections to be aligned.
        """

        links = self._safe_get_attributes(
            session,
            self.LIVE_JOB_LINK_SELECTOR,
            "href",
        )

        if not links:
            return ()

        field_combinations = (
            (
                self.LIVE_TITLE_SELECTORS,
                self.LIVE_COMPANY_SELECTORS,
                self.LIVE_LOCATION_SELECTORS,
            ),
        )

        for (
            title_selectors,
            company_selectors,
            location_selectors,
        ) in field_combinations:

            titles = self._collect_first_aligned_selector(
                session,
                title_selectors,
                expected_count=len(links),
            )

            companies = self._collect_first_aligned_selector(
                session,
                company_selectors,
                expected_count=len(links),
            )

            locations = self._collect_first_aligned_selector(
                session,
                location_selectors,
                expected_count=len(links),
            )

            if self._fields_can_be_aligned(
                links,
                titles,
                companies,
            ):
                return self._build_live_jobs(
                    links=links,
                    titles=titles,
                    companies=companies,
                    locations=locations,
                    maximum_results=maximum_results,
                )

        return ()

    # ------------------------------------------------------------------
    # Live field helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fields_can_be_aligned(
        links: list[str],
        titles: list[str],
        companies: list[str],
    ) -> bool:
        """
        Return True when the required live fields have matching counts.
        """

        if not links:
            return False

        return (
            len(links)
            == len(titles)
            == len(companies)
        )

    def _collect_first_aligned_selector(
        self,
        session: PortalSession,
        selectors: tuple[str, ...],
        *,
        expected_count: int,
    ) -> list[str]:
        """
        Try selectors until one returns the expected number of values.

        This prevents selecting a generic page-level heading that
        happens to match but does not correspond one-to-one with jobs.
        """

        for selector in selectors:
            values = self._safe_get_texts(
                session,
                selector,
            )

            if len(values) == expected_count:
                return values

        return []

    @staticmethod
    def _safe_get_texts(
        session: PortalSession,
        selector: str,
    ) -> list[str]:
        """
        Safely retrieve text values.
        """

        try:
            values = session.get_texts(
                selector
            )
        except Exception:
            return []

        return [
            (value or "").strip()
            for value in values
        ]

    @staticmethod
    def _safe_get_attributes(
        session: PortalSession,
        selector: str,
        attribute: str,
    ) -> list[str]:
        """
        Safely retrieve attributes.
        """

        try:
            values = session.get_attributes(
                selector,
                attribute,
            )
        except Exception:
            return []

        return [
            (value or "").strip()
            for value in values
        ]

    # ------------------------------------------------------------------
    # Build live normalized jobs
    # ------------------------------------------------------------------

    def _build_live_jobs(
        self,
        *,
        links: list[str],
        titles: list[str],
        companies: list[str],
        locations: list[str],
        maximum_results: int,
    ) -> tuple[DiscoveredJob, ...]:
        """
        Convert aligned live LinkedIn fields into DiscoveredJob objects.
        """

        jobs: list[DiscoveredJob] = []

        seen_ids: set[str] = set()

        limit = min(
            len(links),
            maximum_results,
        )

        for index in range(limit):
            normalized_href = (
                links[index] or ""
            ).strip()

            if not normalized_href:
                continue

            if "/jobs/view/" not in normalized_href:
                continue

            external_id = self._extract_external_id(
                normalized_href
            )

            if not external_id:
                continue

            if external_id in seen_ids:
                continue

            seen_ids.add(external_id)

            title = (
                titles[index]
                if index < len(titles)
                else ""
            ).strip()

            company_name = (
                companies[index]
                if index < len(companies)
                else ""
            ).strip()

            location = (
                locations[index]
                if index < len(locations)
                else ""
            ).strip()

            # ----------------------------------------------------------
            # LinkedIn can occasionally omit one field.
            # ----------------------------------------------------------

            if not title:
                title = self._clean_fallback_title(
                    normalized_href
                )

            if not company_name:
                company_name = "Unknown"

            if not location:
                location = None

            job_url = urljoin(
                f"{self.base_url}/",
                normalized_href,
            )

            jobs.append(
                DiscoveredJob(
                    external_id=external_id,
                    title=title,
                    company_name=company_name,
                    source=JobSourceType.LINKEDIN,
                    url=job_url,
                    location=location,
                    metadata={
                        "portal": "LinkedIn",
                        "extraction_mode": "live",
                    },
                )
            )

        return tuple(jobs)

    # ------------------------------------------------------------------
    # External ID extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_external_id(
        href: str,
    ) -> str | None:
        """
        Extract a LinkedIn job ID from a job URL.

        Supported examples:

            /jobs/view/123456789/

            https://www.linkedin.com/jobs/view/123456789/

            /jobs/view/123456789/?trackingId=abc

        Some LinkedIn URLs use SEO slugs followed by the numeric ID:

            /jobs/view/data-analyst-at-company-4451570216

        In that case the full final path component is retained as the
        external ID so that it remains deterministic.
        """

        parsed = urlparse(
            href
        )

        path = parsed.path.strip(
            "/"
        )

        match = re.search(
            r"/jobs/view/([^/]+)",
            f"/{path}",
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        external_id = (
            match.group(1)
            .strip()
        )

        return (
            external_id
            or None
        )

    # ------------------------------------------------------------------
    # Safe fallback title
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_fallback_title(
        href: str,
    ) -> str:
        """
        Return a safe placeholder title when LinkedIn does not expose
        a usable title through the available session selectors.

        Normally the live title selectors should provide the actual
        LinkedIn job title.
        """

        external_id = (
            LinkedInJobCardExtractor._extract_external_id(
                href
            )
        )

        if external_id:
            return (
                f"LinkedIn Job {external_id}"
            )

        return "LinkedIn Job"