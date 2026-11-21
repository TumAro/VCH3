from src.domain.notifications import Notification
from src.domain.overview import (
    CityOverview,
    MonthlyRevenue,
    NetworkOverview,
    StateOverview,
    StoreOverview,
)
from src.services.assistant_evidence_service import AssistantEvidenceService


def make_overview():
    lko_01 = StoreOverview("LKO-01", "S+", 200000.0, 80, 10, 200, 45.0, 2)
    lko_02 = StoreOverview("LKO-02", "A", 150000.0, 70, 0, 160, 43.75, 0)
    lucknow = CityOverview("Lucknow", 2, 350000.0, 100.0, [lko_01, lko_02])
    up = StateOverview("Uttar Pradesh", 2, 350000.0, 100.0, [lucknow])
    return NetworkOverview(350000.0, 2, [up])


def test_retrieves_network_and_store_evidence():
    service = AssistantEvidenceService(
        make_overview(),
        MonthlyRevenue(["2026-09", "2026-10"], {"Uttar Pradesh": [150000.0, 200000.0]}),
    )

    network = service.retrieve("show me the overall network")
    assert network[0].metric == "total_revenue"
    assert network[0].value == 350000.0

    store = service.retrieve("how is LKO-01?")
    assert store
    assert store[0].scope == "store:LKO-01"
    assert store[0].details["zero_stock_skus"] == 2


def test_daily_tasks_are_capped_ranked_and_store_owned():
    service = AssistantEvidenceService(
        make_overview(),
        MonthlyRevenue(["2026-10"], {"Uttar Pradesh": [350000.0]}),
        [
            Notification(
                id="issue-1",
                kind="data_issue",
                title="Negative stock row",
                detail="KUR-02-M at MYS-02: -4 units. Marked untrusted.",
            )
        ],
    )

    tasks = service.daily_tasks()

    assert len(tasks) == 2
    assert tasks[0].rank == 1
    assert tasks[0].owner == "LKO-01"
    assert tasks[0].impact_unit == "zero-stock SKUs"
