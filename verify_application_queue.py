"""
Application Queue Service Integration Test.

Tests the in-memory application queue independently from
databases, browsers, and external job portals.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.services.application_queue import (
    ApplicationQueueService,
)
from src.shared.config.constants import JobSourceType


def create_job(
    external_id: str,
    *,
    title: str = "Data Analyst",
    company_name: str = "Test Company",
) -> DiscoveredJob:
    """Create a deterministic test job."""

    return DiscoveredJob(
        external_id=external_id,
        title=title,
        company_name=company_name,
        source=JobSourceType.LINKEDIN,
        url=(
            "https://www.linkedin.com/jobs/view/"
            f"{external_id}"
        ),
        location="Hyderabad, Telangana, India",
    )


def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION QUEUE SERVICE INTEGRATION TEST")
    print("=" * 70)

    # --------------------------------------------------------------
    # 1/10
    # --------------------------------------------------------------

    print()
    print("[1/10] Creating application queue service...")

    service = ApplicationQueueService()

    assert isinstance(
        service,
        ApplicationQueueService,
    )

    assert service.size == 0
    assert service.maximum_queue_size == 1000

    print("QUEUE SERVICE creation successful")
    print("Initial size:", service.size)
    print("Maximum size:", service.maximum_queue_size)

    # --------------------------------------------------------------
    # 2/10
    # --------------------------------------------------------------

    print()
    print("[2/10] Testing valid job enqueue...")

    job = create_job(
        "queue-test-001"
    )

    decision = service.enqueue(
        job,
        match_score=0.92,
    )

    assert decision.accepted is True
    assert decision.item is not None
    assert decision.duplicate is False
    assert decision.queue_full is False

    item = decision.item

    assert item.external_job_id == "queue-test-001"
    assert item.job_title == "Data Analyst"
    assert item.company_name == "Test Company"
    assert item.match_score == 0.92

    print("JOB ENQUEUE successful")
    print("Accepted:", decision.accepted)
    print("Application ID:", item.application_id)
    print("External Job ID:", item.external_job_id)
    print("Match score:", item.match_score)

    # --------------------------------------------------------------
    # 3/10
    # --------------------------------------------------------------

    print()
    print("[3/10] Testing duplicate protection...")

    duplicate_decision = service.enqueue(
        job,
        match_score=0.95,
    )

    assert duplicate_decision.accepted is False
    assert duplicate_decision.duplicate is True
    assert duplicate_decision.item is None

    print("DUPLICATE protection successful")
    print("Accepted:", duplicate_decision.accepted)
    print("Duplicate:", duplicate_decision.duplicate)
    print("Reason:", duplicate_decision.reason)

    # --------------------------------------------------------------
    # 4/10
    # --------------------------------------------------------------

    print()
    print("[4/10] Testing queue capacity...")

    small_queue = ApplicationQueueService(
        maximum_queue_size=2
    )

    small_queue.enqueue(
        create_job("capacity-test-001"),
        match_score=0.90,
    )

    small_queue.enqueue(
        create_job("capacity-test-002"),
        match_score=0.85,
    )

    full_decision = small_queue.enqueue(
        create_job("capacity-test-003"),
        match_score=0.80,
    )

    assert full_decision.accepted is False
    assert full_decision.queue_full is True

    print("QUEUE CAPACITY handling successful")
    print("Queue size:", small_queue.size)
    print("Maximum:", small_queue.maximum_queue_size)
    print("Queue full:", full_decision.queue_full)

    # --------------------------------------------------------------
    # 5/10
    # --------------------------------------------------------------

    print()
    print("[5/10] Testing match-score validation...")

    invalid_low = False
    invalid_high = False

    try:
        service.enqueue(
            create_job("score-test-low"),
            match_score=-0.1,
        )
    except ValueError:
        invalid_low = True

    try:
        service.enqueue(
            create_job("score-test-high"),
            match_score=1.1,
        )
    except ValueError:
        invalid_high = True

    assert invalid_low is True
    assert invalid_high is True

    print("MATCH SCORE validation successful")
    print("Below zero rejected:", invalid_low)
    print("Above one rejected:", invalid_high)

    # --------------------------------------------------------------
    # 6/10
    # --------------------------------------------------------------

    print()
    print("[6/10] Testing priority ordering...")

    priority_service = ApplicationQueueService()

    priority_service.enqueue(
        create_job(
            "priority-low",
            title="Data Analyst",
        ),
        match_score=0.99,
        priority=1,
    )

    priority_service.enqueue(
        create_job(
            "priority-high",
            title="Business Analyst",
        ),
        match_score=0.80,
        priority=10,
    )

    priority_service.enqueue(
        create_job(
            "priority-medium",
            title="Data Analyst",
        ),
        match_score=0.90,
        priority=5,
    )

    ordered = priority_service.list_items()

    assert ordered[0].external_job_id == "priority-high"
    assert ordered[1].external_job_id == "priority-medium"
    assert ordered[2].external_job_id == "priority-low"

    print("PRIORITY ordering successful")

    for index, item in enumerate(
        ordered,
        start=1,
    ):
        print(
            f"{index}. "
            f"{item.external_job_id} | "
            f"Priority: {item.priority} | "
            f"Score: {item.match_score:.0%}"
        )

    # --------------------------------------------------------------
    # 7/10
    # --------------------------------------------------------------

    print()
    print("[7/10] Testing job lookup...")

    lookup_service = ApplicationQueueService()

    lookup_decision = lookup_service.enqueue(
        create_job("lookup-test-001"),
        match_score=0.88,
    )

    assert lookup_decision.item is not None

    application_id = (
        lookup_decision.item.application_id
    )

    by_application = lookup_service.get(
        application_id
    )

    by_job = lookup_service.get_by_job(
        "lookup-test-001"
    )

    assert by_application is not None
    assert by_job is not None

    assert (
        by_application.application_id
        == application_id
    )

    assert (
        by_job.external_job_id
        == "lookup-test-001"
    )

    print("LOOKUP successful")
    print("Application ID:", application_id)
    print("External Job ID:", by_job.external_job_id)

    # --------------------------------------------------------------
    # 8/10
    # --------------------------------------------------------------

    print()
    print("[8/10] Testing queued-item retrieval...")

    queue_service = ApplicationQueueService()

    queue_service.enqueue(
        create_job("queued-test-001"),
        match_score=0.95,
    )

    queue_service.enqueue(
        create_job("queued-test-002"),
        match_score=0.85,
    )

    queued = queue_service.queued_items()

    assert len(queued) == 2

    for item in queued:
        assert item.status.value == "queued"

    print("QUEUED ITEM retrieval successful")
    print("Queued items:", len(queued))

    for item in queued:
        print(
            f"- {item.external_job_id} | "
            f"{item.status.value}"
        )

    # --------------------------------------------------------------
    # 9/10
    # --------------------------------------------------------------

    print()
    print("[9/10] Testing removal...")

    removal_service = ApplicationQueueService()

    removal_decision = removal_service.enqueue(
        create_job("remove-test-001"),
        match_score=0.91,
    )

    assert removal_decision.item is not None

    removal_id = (
        removal_decision.item.application_id
    )

    assert removal_service.size == 1
    assert removal_service.contains_job(
        "remove-test-001"
    ) is True

    removed = removal_service.remove(
        removal_id
    )

    assert removed is not None
    assert removed.external_job_id == "remove-test-001"

    assert removal_service.size == 0
    assert removal_service.contains_job(
        "remove-test-001"
    ) is False

    print("REMOVAL successful")
    print("Removed:", removed.external_job_id)
    print("Queue size:", removal_service.size)

    # --------------------------------------------------------------
    # 10/10
    # --------------------------------------------------------------

    print()
    print("[10/10] Testing queue clear/reset...")

    clear_service = ApplicationQueueService()

    for index in range(1, 4):
        clear_service.enqueue(
            create_job(
                f"clear-test-{index:03d}"
            ),
            match_score=0.80 + (
                index * 0.03
            ),
        )

    assert clear_service.size == 3

    clear_service.clear()

    assert clear_service.size == 0
    assert clear_service.list_items() == []
    assert clear_service.queued_items() == []

    assert clear_service.contains_job(
        "clear-test-001"
    ) is False

    print("QUEUE CLEAR/RESET successful")
    print("Queue size after clear:", clear_service.size)

    print()
    print("=" * 70)
    print("APPLICATION QUEUE SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()