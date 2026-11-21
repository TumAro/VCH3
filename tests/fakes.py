"""In-memory fake repositories for service unit tests (no CSV access)."""
from typing import List, Optional, Set

from src.domain.models import DataIssue, SalesLine, StockPosition, Store, WarehouseInbound, WeeklyStock
from src.domain.repositories import IRulesRepository, IStockRepository, ISalesRepository, IStoreRepository


class FakeRulesRepository(IRulesRepository):
    """Only data issues are configurable; rule lookups return neutral values."""

    def __init__(self, data_issues: List[DataIssue] = ()):
        self._issues = list(data_issues)

    def get_min_display(self, tier: str, category: str) -> int:
        return 0

    def get_lead_time_days(self, from_location: str, to_location: str) -> int:
        return 0

    def get_flagship_protected_styles(self, store_id: str) -> Set[str]:
        return set()

    def get_all_data_issues(self) -> List[DataIssue]:
        return list(self._issues)


class FakeStoreRepository(IStoreRepository):
    def __init__(self, stores: List[Store]):
        self._stores = list(stores)

    def get_all(self) -> List[Store]:
        return list(self._stores)

    def get_by_id(self, store_id: str) -> Optional[Store]:
        return next((s for s in self._stores if s.store_id == store_id), None)


class FakeSalesRepository(ISalesRepository):
    def __init__(self, lines: List[SalesLine]):
        self._lines = list(lines)

    def get_all_sales_lines(self) -> List[SalesLine]:
        return list(self._lines)

    def get_sales_lines_by_store(self, store_id: str) -> List[SalesLine]:
        return [line for line in self._lines if line.store_id == store_id]


class FakeStockRepository(IStockRepository):
    def __init__(self, positions: List[StockPosition]):
        self._positions = list(positions)

    def get_snapshot_positions(self) -> List[StockPosition]:
        return list(self._positions)

    def get_position(self, location_id: str, sku_id: str) -> Optional[StockPosition]:
        return next(
            (p for p in self._positions if p.location_id == location_id and p.sku_id == sku_id),
            None,
        )

    def get_weekly_stock(self, store_id: str, sku_id: str) -> List[WeeklyStock]:
        return []

    def get_all_weekly_stock(self) -> List[WeeklyStock]:
        return []

    def get_warehouse_inbound(self) -> List[WarehouseInbound]:
        return []
