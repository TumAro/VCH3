"""AC-7 / AC-8 / AC-9 on the real dataset, checked against an independent CSV calculation (T5)."""
import csv
from collections import defaultdict
from pathlib import Path

import pytest

from src.infrastructure.in_memory_repository import InMemoryRepositoryContainer
from src.services.network_overview_service import NetworkOverviewService

DATA_DIR = Path("data/csv")


def _rows(name):
    with open(DATA_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def expected():
    """Independent figures computed with the csv module only."""
    packaging = {r["sku_id"].strip() for r in _rows("items.csv") if r["is_packaging"].strip() == "1"}
    stores = {r["store_id"].strip(): r for r in _rows("stores.csv")}
    bill_store = {r["bill_id"].strip(): r["store_id"].strip() for r in _rows("bills.csv")}

    revenue_by_state = defaultdict(float)
    for r in _rows("bill_lines.csv"):
        if r["sku_id"].strip() in packaging:
            continue
        store_id = bill_store.get(r["bill_id"].strip())
        if store_id in stores:
            revenue_by_state[stores[store_id]["state"]] += int(r["qty"]) * float(r["selling_price"])

    on_hand_by_store = defaultdict(int)
    for r in _rows("stock_snapshot.csv"):
        if r["sku_id"].strip() not in packaging:
            on_hand_by_store[r["location_id"].strip()] += int(r["on_hand"])

    stores_by_state = defaultdict(int)
    for s in stores.values():
        stores_by_state[s["state"]] += 1

    return {
        "revenue_by_state": dict(revenue_by_state),
        "on_hand_by_store": dict(on_hand_by_store),
        "stores_by_state": dict(stores_by_state),
    }


@pytest.fixture(scope="module")
def service():
    c = InMemoryRepositoryContainer(DATA_DIR)
    return NetworkOverviewService(c.stores, c.sales, c.stock)


@pytest.fixture(scope="module")
def overview(service):
    return service.get_network_overview()


def _state(overview, name):
    return next(s for s in overview.states if s.state == name)


def test_ac7_state_revenue_matches_csv_to_the_rupee(overview, expected):
    actual = {s.state: s.revenue for s in overview.states}
    assert set(actual) == set(expected["revenue_by_state"])
    for state, rev in expected["revenue_by_state"].items():
        assert round(actual[state]) == round(rev), state


def test_ac7_store_counts(overview, expected):
    assert {s.state: s.store_count for s in overview.states} == expected["stores_by_state"]
    assert expected["stores_by_state"] == {"Uttar Pradesh": 7, "Bihar": 6, "Karnataka": 7}


def test_shares_sum_to_100(overview):
    assert sum(s.share_pct for s in overview.states) == pytest.approx(100.0, abs=0.1)


def test_ac8_months_and_monthly_sums(service, overview):
    mr = service.get_monthly_revenue()
    assert mr.months[0] == "2024-11"
    assert mr.months[-1] == "2026-10"
    assert len(mr.months) == 24
    for s in overview.states:
        assert sum(mr.series[s.state]) == pytest.approx(s.revenue)


def test_ac9_up_drilldown(overview, expected):
    up = _state(overview, "Uttar Pradesh")
    assert {c.city: c.store_count for c in up.cities} == {"Lucknow": 4, "Kanpur": 3}
    assert sum(c.revenue for c in up.cities) == pytest.approx(up.revenue)

    lucknow = next(c for c in up.cities if c.city == "Lucknow")
    assert sorted(st.store_id for st in lucknow.stores) == ["LKO-01", "LKO-02", "LKO-03", "LKO-04"]
    for st in lucknow.stores:
        assert st.on_hand == expected["on_hand_by_store"].get(st.store_id, 0), st.store_id


def test_warehouse_and_west_bengal_absent(overview):
    assert "West Bengal" not in {s.state for s in overview.states}
    ids = {st.store_id for s in overview.states for c in s.cities for st in c.stores}
    assert "WH-KOL" not in ids
