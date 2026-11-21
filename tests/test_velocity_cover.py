"""Unit and integration tests for Track 2 Velocity & Cover Intelligence."""
from datetime import date
from pathlib import Path

import pytest

from src.domain.models import (
    Item,
    SalesLine,
    StockPosition,
    Store,
    WeeklyStock,
)
from src.infrastructure.in_memory_repository import InMemoryRepositoryContainer
from src.velocity_cover.pipeline import VelocityCoverPipeline
from src.velocity_cover.models import FindingType
from src.velocity_cover.position_cover_service import PositionCoverService
from src.velocity_cover.problem_detection_service import ProblemDetectionService
from src.velocity_cover.velocity_service import VelocityService


AS_OF = date(2026, 10, 31)


class Stores:
    def __init__(self, values):
        self.values = {row.store_id: row for row in values}

    def get_all(self):
        return list(self.values.values())

    def get_by_id(self, store_id):
        return self.values.get(store_id)


class Items:
    def __init__(self, values):
        self.values = {row.sku_id: row for row in values}

    def get_all(self):
        return list(self.values.values())

    def get_by_id(self, sku_id):
        return self.values.get(sku_id)

    def get_by_style(self, style_id):
        return [row for row in self.values.values() if row.style_id == style_id]


class Stock:
    def __init__(self, positions, weekly):
        self.positions = positions
        self.weekly = weekly

    def get_snapshot_positions(self):
        return list(self.positions)

    def get_position(self, location_id, sku_id):
        return next(
            (row for row in self.positions if row.location_id == location_id and row.sku_id == sku_id),
            None,
        )

    def get_weekly_stock(self, store_id, sku_id):
        return [row for row in self.weekly if row.store_id == store_id and row.sku_id == sku_id]

    def get_all_weekly_stock(self):
        return list(self.weekly)

    def get_warehouse_inbound(self):
        return []


class Sales:
    def __init__(self, lines):
        self.lines = lines

    def get_all_sales_lines(self):
        return list(self.lines)

    def get_sales_lines_by_store(self, store_id):
        return [row for row in self.lines if row.store_id == store_id]


class Rules:
    def __init__(self, lead_times=None):
        self.lead_times = lead_times or {}

    def get_min_display(self, tier, category):
        return 0

    def get_lead_time_days(self, from_location, to_location):
        return self.lead_times.get(to_location, 6)

    def get_flagship_protected_styles(self, store_id):
        return set()

    def get_all_data_issues(self):
        return []


class Repository:
    def __init__(self, stores, items, positions, weekly, sales, lead_times=None):
        self.stores = Stores(stores)
        self.items = Items(items)
        self.stock = Stock(positions, weekly)
        self.sales = Sales(sales)
        self.rules = Rules(lead_times)


def store(store_id, city="Bengaluru", tier="S+", opened=date(2020, 1, 1), zone="South"):
    is_new = (AS_OF - opened).days < 28
    return Store(store_id, city, "Karnataka", zone, tier, 1000, 500, opened, "AM-01", is_new)


def item(sku_id="SKU-1", style_id="STYLE-1", category="Kurta Set", mrp=1000.0, core=True):
    return Item(
        sku_id,
        style_id,
        "Test Style",
        category,
        "M",
        mrp,
        500.0,
        date(2024, 1, 1),
        core,
        False,
    )


def weekly(store_id, sku_id, days=7, count=12):
    return [
        WeeklyStock(date(2026, 8, 15) + __import__("datetime").timedelta(days=7 * index),
                    store_id, sku_id, 1, days)
        for index in range(count)
    ]


def sales_line(store_id, sku_id, qty):
    return SalesLine("B1", date(2026, 10, 25), store_id, "SP1", "C1", sku_id, qty, 1000.0, 900.0)


def test_stockout_aware_velocity_uses_in_stock_days():
    repo = Repository(
        [store("BLR-01")],
        [item()],
        [],
        [
            WeeklyStock(date(2026, 8, 15) + __import__("datetime").timedelta(days=7 * index),
                        "BLR-01", "SKU-1", 1, 3 if index == 11 else 0)
            for index in range(12)
        ],
        [sales_line("BLR-01", "SKU-1", 4)],
    )

    velocity = VelocityService(repo).compute()[0][0]
    assert velocity.velocity == pytest.approx(4 / 3)
    assert velocity.velocity > 4 / 7


def test_zero_sales_zero_days_and_rollups():
    repo = Repository(
        [store("BLR-01")],
        [item("SKU-1", "STYLE-1"), item("SKU-2", "STYLE-1")],
        [],
        [
            WeeklyStock(AS_OF, "BLR-01", "SKU-1", 0, 0),
            WeeklyStock(AS_OF, "BLR-01", "SKU-2", 1, 7),
        ],
        [sales_line("BLR-01", "SKU-2", 7)],
    )

    sku, style, category = VelocityService(repo).compute()
    assert next(row for row in sku if row.sku_id == "SKU-1").velocity == 0.0
    assert len(style) == 1
    assert style[0].quantity_sold == 7
    assert style[0].days_in_stock == 7
    assert style[0].velocity == 1.0


def test_blr05_uses_bengaluru_s_plus_peer_mean():
    stores = [
        store("BLR-03", tier="S+"),
        store("BLR-04", tier="S+"),
        store("BLR-05", tier="B", opened=date(2026, 10, 10)),
    ]
    rows = []
    sales = []
    for peer_id, qty in (("BLR-03", 4), ("BLR-04", 6)):
        rows.extend(weekly(peer_id, "SKU-1", days=7))
        sales.append(sales_line(peer_id, "SKU-1", qty))
    for peer_id in ("BLR-03", "BLR-04"):
        pass
    rows.extend(weekly("BLR-05", "SKU-1", days=21))

    repo = Repository(stores, [item()], [], rows, sales)
    result = next(
        row for row in VelocityService(repo).compute()[0]
        if row.store_id == "BLR-05"
    )

    assert result.is_peer_fallback is True
    assert result.velocity == pytest.approx((4 / 84 + 6 / 84) / 2)
    assert set(result.peer_store_ids) == {"BLR-03", "BLR-04"}


def test_cover_and_stock_age_branches():
    stores = [store("BLR-01")]
    items = [item()]
    positions = [
        StockPosition("BLR-01", "SKU-1", 5, 2, None, date(2026, 9, 1)),
        StockPosition("BLR-01", "SKU-2", 0, 0, None, None),
    ]
    items.append(item("SKU-2"))
    from src.velocity_cover.models import DailyVelocity

    repo = Repository(stores, items, positions, [], [])
    positive = PositionCoverService(repo).compute((
        DailyVelocity("BLR-01", "SKU-1", 14, 84, 1.0),
        DailyVelocity("BLR-01", "SKU-2", 0, 84, 0.0),
    ))

    assert positive[0].effective_stock == 7
    assert positive[0].cover_days == 7.0
    assert positive[0].stock_age_days == 60
    assert positive[1].cover_days == 0.0
    assert positive[1].stock_age_days == 0

    infinite_positions = [
        StockPosition("BLR-01", "SKU-1", 5, 0, None, AS_OF)
    ]
    repo.stock.positions = infinite_positions
    infinite = PositionCoverService(repo).compute((
        DailyVelocity("BLR-01", "SKU-1", 0, 84, 0.0),
    ))
    assert infinite[0].cover_days == 999.0


def test_ageing_and_zero_sales_findings():
    stores = [store("BLR-01")]
    fashion = item("SKU-FASHION", "STYLE-F", core=False)
    no_stock = item("SKU-NOSTOCK")
    no_demand = item("SKU-NODEMAND")
    repo = Repository(
        stores,
        [fashion, no_stock, no_demand],
        [
            StockPosition("BLR-01", "SKU-FASHION", 100, 0, None, date(2026, 5, 1)),
            StockPosition("BLR-01", "SKU-NOSTOCK", 0, 0, None, None),
            StockPosition("BLR-01", "SKU-NODEMAND", 3, 0, None, AS_OF),
        ],
        [],
        [],
        {"BLR-01": 6},
    )
    from src.velocity_cover.models import DailyVelocity, InventoryPosition

    positions = (
        InventoryPosition("BLR-01", "SKU-FASHION", 100, 0, 100, 1.0, 100.0, 183),
        InventoryPosition("BLR-01", "SKU-NOSTOCK", 0, 0, 0, 0.0, 0.0, 0),
        InventoryPosition("BLR-01", "SKU-NODEMAND", 3, 0, 3, 0.0, 999.0, 0),
    )
    velocities = (
        DailyVelocity("BLR-01", "SKU-FASHION", 84, 84, 1.0),
        DailyVelocity("BLR-01", "SKU-NOSTOCK", 0, 0, 0.0),
        DailyVelocity("BLR-01", "SKU-NODEMAND", 0, 7, 0.0),
    )
    findings = ProblemDetectionService(repo).detect(positions, velocities)
    ageing = [row for row in findings if row.finding_type == FindingType.AGEING_RISK]
    zero = [row for row in findings if row.finding_type == FindingType.ZERO_SALES_DIAGNOSIS]
    assert len(ageing) == 1
    assert {row.diagnosis for row in zero} == {"no stock", "no demand"}


def test_stockout_findings_sorted_by_revenue_loss():
    stores = [store("BLR-01"), store("BLR-02")]
    items = [item("SKU-LOW", "S-LOW", mrp=100), item("SKU-HIGH", "S-HIGH", mrp=10000)]
    repo = Repository(stores, items, [], [], [], {"BLR-01": 6, "BLR-02": 6})
    from src.velocity_cover.models import DailyVelocity, InventoryPosition

    positions = (
        InventoryPosition("BLR-01", "SKU-LOW", 1, 0, 1, 1.0, 1.0, 10),
        InventoryPosition("BLR-02", "SKU-HIGH", 1, 0, 1, 2.0, 0.5, 10),
    )
    velocities = (
        DailyVelocity("BLR-01", "SKU-LOW", 84, 84, 1.0),
        DailyVelocity("BLR-02", "SKU-HIGH", 168, 84, 2.0),
    )
    findings = ProblemDetectionService(repo).detect(positions, velocities)
    stockout = [row for row in findings if row.finding_type == FindingType.STOCKOUT_RISK]
    assert stockout[0].sku_id == "SKU-HIGH"
    assert stockout[1].sku_id == "SKU-LOW"


def test_real_repository_pipeline():
    repo = InMemoryRepositoryContainer(Path("data/csv"))
    result = VelocityCoverPipeline(repo).run()

    blr05 = [row for row in result.sku_velocities if row.store_id == "BLR-05"]
    assert blr05
    assert all(row.quantity_sold >= 0 for row in blr05)
    assert len(result.positions) > 0
    assert len(result.findings) > 0
