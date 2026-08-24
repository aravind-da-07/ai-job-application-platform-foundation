"""
Unit tests for LinkedIn search URL construction and job extraction.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.entities.job_discovery import (
    JobSearchCriteria,
)
from src.modules.job_discovery.infrastructure.portals.linkedin.linkedin_search import (
    LinkedInJobCardExtractor,
    LinkedInSearchBuilder,
)
from src.shared.config.constants import JobSourceType


class FakePortalSession:
    """
    Minimal PortalSession implementation for extractor unit tests.
    """

    def __init__(
        self,
        *,
        attributes: dict[tuple[str, str], list[str | None]] | None = None,
        texts: dict[str, list[str]] | None = None,
    ) -> None:
        self.attributes = attributes or {}
        self.texts = texts or {}

    def get_attributes(
        self,
        selector: str,
        attribute: str,
    ) -> list[str | None]:
        return self.attributes.get(
            (selector, attribute),
            [],
        )

    def get_texts(
        self,
        selector: str,
    ) -> list[str]:
        return self.texts.get(
            selector,
            [],
        )


def test_search_builder_builds_keyword_url() -> None:
    builder = LinkedInSearchBuilder()

    url = builder.build_url(
        keywords="Data Analyst",
    )

    assert url == (
        "https://www.linkedin.com/jobs/search/"
        "?keywords=Data+Analyst"
    )


def test_search_builder_builds_keyword_and_location_url() -> None:
    builder = LinkedInSearchBuilder()

    url = builder.build_url(
        keywords="Data Analyst",
        location="Hyderabad",
    )

    assert url == (
        "https://www.linkedin.com/jobs/search/"
        "?keywords=Data+Analyst&location=Hyderabad"
    )


def test_search_builder_builds_multiple_location_urls() -> None:
    builder = LinkedInSearchBuilder()

    criteria = JobSearchCriteria(
        keywords=(
            "Data Analyst",
            "Business Analyst",
        ),
        locations=(
            "Hyderabad",
            "Bangalore",
        ),
    )

    urls = builder.build_urls(criteria)

    assert urls == (
        (
            "https://www.linkedin.com/jobs/search/"
            "?keywords=Data+Analyst+OR+Business+Analyst"
            "&location=Hyderabad"
        ),
        (
            "https://www.linkedin.com/jobs/search/"
            "?keywords=Data+Analyst+OR+Business+Analyst"
            "&location=Bangalore"
        ),
    )


def test_search_builder_requires_keywords() -> None:
    builder = LinkedInSearchBuilder()

    criteria = JobSearchCriteria(
        keywords=(),
    )

    try:
        builder.build_urls(criteria)
    except ValueError as exc:
        assert "keyword" in str(exc).lower()
    else:
        raise AssertionError(
            "Expected ValueError when keywords are missing."
        )


def test_local_job_extractor_returns_normalized_jobs() -> None:
    extractor = LinkedInJobCardExtractor()

    session = FakePortalSession(
        attributes={
            (
                "article[data-job-id]",
                "data-job-id",
            ): [
                "1001",
                "1002",
            ],
            (
                "article[data-job-id] a.job-link",
                "href",
            ): [
                "/jobs/view/1001/",
                "/jobs/view/1002/",
            ],
        },
        texts={
            "article[data-job-id] .job-title": [
                "Data Analyst",
                "Senior Data Analyst",
            ],
            "article[data-job-id] .job-company": [
                "Company A",
                "Company B",
            ],
            "article[data-job-id] .job-location": [
                "Hyderabad",
                "Bangalore",
            ],
        },
    )

    jobs = extractor.extract(
        session,
        maximum_results=10,
    )

    assert len(jobs) == 2

    assert jobs[0].external_id == "1001"
    assert jobs[0].title == "Data Analyst"
    assert jobs[0].company_name == "Company A"
    assert jobs[0].location == "Hyderabad"
    assert jobs[0].source == JobSourceType.LINKEDIN
    assert jobs[0].url == (
        "https://www.linkedin.com/jobs/view/1001/"
    )

    assert jobs[1].external_id == "1002"
    assert jobs[1].title == "Senior Data Analyst"
    assert jobs[1].company_name == "Company B"
    assert jobs[1].location == "Bangalore"


def test_local_job_extractor_removes_duplicate_ids() -> None:
    extractor = LinkedInJobCardExtractor()

    session = FakePortalSession(
        attributes={
            (
                "article[data-job-id]",
                "data-job-id",
            ): [
                "1001",
                "1001",
                "1002",
            ],
            (
                "article[data-job-id] a.job-link",
                "href",
            ): [
                "/jobs/view/1001/",
                "/jobs/view/1001/",
                "/jobs/view/1002/",
            ],
        },
        texts={
            "article[data-job-id] .job-title": [
                "Data Analyst",
                "Data Analyst",
                "Business Analyst",
            ],
            "article[data-job-id] .job-company": [
                "Company A",
                "Company A",
                "Company B",
            ],
            "article[data-job-id] .job-location": [
                "Hyderabad",
                "Hyderabad",
                "Bangalore",
            ],
        },
    )

    jobs = extractor.extract(
        session,
        maximum_results=10,
    )

    assert len(jobs) == 2
    assert [
        job.external_id
        for job in jobs
    ] == [
        "1001",
        "1002",
    ]


def test_local_job_extractor_respects_maximum_results() -> None:
    extractor = LinkedInJobCardExtractor()

    session = FakePortalSession(
        attributes={
            (
                "article[data-job-id]",
                "data-job-id",
            ): [
                "1001",
                "1002",
                "1003",
            ],
            (
                "article[data-job-id] a.job-link",
                "href",
            ): [
                "/jobs/view/1001/",
                "/jobs/view/1002/",
                "/jobs/view/1003/",
            ],
        },
        texts={
            "article[data-job-id] .job-title": [
                "Data Analyst",
                "Business Analyst",
                "Senior Analyst",
            ],
            "article[data-job-id] .job-company": [
                "Company A",
                "Company B",
                "Company C",
            ],
            "article[data-job-id] .job-location": [
                "Hyderabad",
                "Bangalore",
                "Chennai",
            ],
        },
    )

    jobs = extractor.extract(
        session,
        maximum_results=2,
    )

    assert len(jobs) == 2
    assert [
        job.external_id
        for job in jobs
    ] == [
        "1001",
        "1002",
    ]


def test_external_id_is_extracted_from_linkedin_url() -> None:
    extractor = LinkedInJobCardExtractor()

    assert (
        extractor._extract_external_id(
            "/jobs/view/123456789/"
        )
        == "123456789"
    )

    assert (
        extractor._extract_external_id(
            "https://www.linkedin.com/jobs/view/123456789/"
        )
        == "123456789"
    )

    assert (
        extractor._extract_external_id(
            "/jobs/view/data-analyst-at-company-4451570216"
        )
        == "data-analyst-at-company-4451570216"
    )


def test_external_id_returns_none_for_non_job_url() -> None:
    extractor = LinkedInJobCardExtractor()

    assert (
        extractor._extract_external_id(
            "/jobs/search/?keywords=Data+Analyst"
        )
        is None
    )