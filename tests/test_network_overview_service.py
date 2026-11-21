"""Unit tests for NetworkOverviewService against fake repositories (T3, T4)."""
from datetime import date

import pytest

from src.domain.models import SalesLine, StockPosition, Store
from src.services.network_overview_service import NetworkOverviewService
from tests.fakes import FakeSalesRepository, FakeStockRepository, FakeStoreRepository


def store(store_id, city, state, capacity=100, tier="A"):
    return Store(store_id, city, state, "Zone", tier, 1000, capacity, date(2020, 1, 1), "AM-01")


def line(store_id, qty, price, d=date(2025, 1, 15)):
    return SalesLine("B1", d, store_id, "SP1", "C1", "SKU-1", qty, price, price)


def pos(location_id, sku_id, on_hand, in_transit=0):
    return StockPosition(location_id, sku_id, on_hand, in_transit, None, None)


STORES = [
    store("A-01", "Alpha", "StateX", capacity=200),
    store("A-02", "Alpha", "StateX"),
    store("B-01", "Beta", "StateX"),
    store("C-01", "Gamma", "StateY"),
    store("C-02", "Gamma", "StateY"),  # no sales, no snapshot rows
]


def make_service(lines, positions=()):
    return NetworkOverviewService(
        FakeStoreRepository(STORES),
        FakeSalesRepository(lines),
        FakeStockRepository(list(positions)),
    )


# --- T3: network overview --------------------------------------------------

def test_revenue_counts_and_shares():
    svc = make_service([line("A-01", 2, 100), line("A-02", 1, 300), line("B-01", 1, 100), line("C-01", 4, 100)])
    ov = svc.get_network_overview()

    assert ov.total_revenue == 1000
    assert ov.store_count == 5
    by_state = {s.state: s for s in ov.states}
    assert by_state["StateX"].revenue == 600
    assert by_state["StateX"].store_count == 3
    assert by_state["StateY"].store_count == 2
    assert by_state["StateX"].share_pct == pytest.approx(60.0)
    assert sum(s.share_pct for s in ov.states) == pytest.approx(100.0)


def test_sorted_by_revenue_desc():
    svc = make_service([line("A-01", 1, 100), line("C-01", 1, 900)])
    ov = svc.get_network_overview()
    assert [s.state for s in ov.states] == ["StateY", "StateX"]
    state_x = ov.states[1]
    assert [c.city for c in state_x.cities] == ["Alpha", "Beta"]


def test_city_and_store_nesting():
    svc = make_service([line("A-01", 1, 100), line("A-02", 3, 100), line("B-01", 1, 400)])
    state_x = next(s for s in svc.get_network_overview().states if s.state == "StateX")
    alpha = next(c for c in state_x.cities if c.city == "Alpha")

    assert alpha.store_count == 2
    assert alpha.revenue == 400
    assert alpha.share_of_state_pct == pytest.approx(50.0)
    assert [st.store_id for st in alpha.stores] == ["A-02", "A-01"]
    assert sum(c.revenue for c in state_x.cities) == state_x.revenue


def test_store_stock_figures():
    positions = [
        pos("A-01", "S1", 50, 5),
        pos("A-01", "S2", 0, 2),
        pos("A-01", "S3", 0),
        pos("WH-KOL", "S1", 999),  # warehouse: never a store row
    ]
    svc = make_service([], positions)
    ov = svc.get_network_overview()
    a01 = next(
        st for s in ov.states for c in s.cities for st in c.stores if st.store_id == "A-01"
    )
    assert (a01.on_hand, a01.in_transit, a01.capacity) == (50, 7, 200)
    assert a01.utilisation_pct == pytest.approx(25.0)
    assert a01.zero_stock_skus == 2
    all_ids = {st.store_id for s in ov.states for c in s.cities for st in c.stores}
    assert "WH-KOL" not in all_ids


def test_store_without_sales_or_snapshot_listed_with_zeros():
    svc = make_service([line("A-01", 1, 100)])
    c02 = next(
        st for s in svc.get_network_overview().states for c in s.cities for st in c.stores
        if st.store_id == "C-02"
    )
    assert (c02.revenue, c02.on_hand, c02.in_transit, c02.zero_stock_skus) == (0, 0, 0, 0)


def test_zero_total_revenue_gives_zero_shares():
    ov = make_service([]).get_network_overview()
    assert ov.total_revenue == 0
    assert all(s.share_pct == 0 for s in ov.states)
    assert all(c.share_of_state_pct == 0 for s in ov.states for c in s.cities)


# --- T4: monthly revenue ---------------------------------------------------

def test_monthly_range_and_zero_fill():
    svc = make_service([
        line("A-01", 1, 100, date(2024, 11, 3)),
        line("C-01", 1, 50, date(2025, 2, 28)),
    ])
    mr = svc.get_monthly_revenue()
    assert mr.months == ["2024-11", "2024-12", "2025-01", "2025-02"]
    assert mr.series["StateX"] == [100, 0, 0, 0]
    assert mr.series["StateY"] == [0, 0, 0, 50]


def test_monthly_sum_equals_state_total():
    lines = [
        line("A-01", 2, 100, date(2024, 12, 1)),
        line("B-01", 1, 70, date(2025, 3, 9)),
        line("C-01", 3, 10, date(2025, 1, 31)),
    ]
    svc = make_service(lines)
    mr = svc.get_monthly_revenue()
    for state in svc.get_network_overview().states:
        assert sum(mr.series[state.state]) == pytest.approx(state.revenue)


def test_monthly_crosses_year_boundary():
    svc = make_service([line("A-01", 1, 1, date(2025, 12, 1)), line("A-01", 1, 1, date(2026, 1, 1))])
    assert svc.get_monthly_revenue().months == ["2025-12", "2026-01"]


def test_monthly_no_sales_lists_states_with_no_months():
    mr = make_service([]).get_monthly_revenue()
    assert mr.months == []
    assert set(mr.series) == {"StateX", "StateY"}
