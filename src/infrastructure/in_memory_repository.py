"""In-memory domain repositories implementation."""
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.domain.models import (
    DataIssue,
    Item,
    LeadTimeRule,
    SalesLine,
    StockPosition,
    Store,
    WarehouseInbound,
    WeeklyStock,
)
from src.domain.repositories import (
    IItemRepository,
    IRulesRepository,
    ISalesRepository,
    IStockRepository,
    IStoreRepository,
)
from src.infrastructure.csv_adapter import CSVDataSourceAdapter


class StoreRepository(IStoreRepository):
    def __init__(self, stores: List[Store]):
        self._stores = stores
        self._by_id = {s.store_id: s for s in stores}

    def get_all(self) -> List[Store]:
        return list(self._stores)

    def get_by_id(self, store_id: str) -> Optional[Store]:
        return self._by_id.get(store_id)


class ItemRepository(IItemRepository):
    def __init__(self, items: List[Item]):
        self._items = items
        self._by_id = {item.sku_id: item for item in items}
        self._by_style: Dict[str, List[Item]] = {}
        for item in items:
            self._by_style.setdefault(item.style_id, []).append(item)

    def get_all(self) -> List[Item]:
        return list(self._items)

    def get_by_id(self, sku_id: str) -> Optional[Item]:
        return self._by_id.get(sku_id)

    def get_by_style(self, style_id: str) -> List[Item]:
        return list(self._by_style.get(style_id, []))


class StockRepository(IStockRepository):
    def __init__(
        self,
        positions: List[StockPosition],
        weekly_stock: List[WeeklyStock],
        warehouse_inbound: List[WarehouseInbound],
    ):
        self._positions = positions
        self._pos_by_key = {(p.location_id, p.sku_id): p for p in positions}
        self._weekly_stock = weekly_stock
        self._weekly_by_store_sku: Dict[Tuple[str, str], List[WeeklyStock]] = {}
        for ws in weekly_stock:
            self._weekly_by_store_sku.setdefault((ws.store_id, ws.sku_id), []).append(ws)
        self._inbound = warehouse_inbound

    def get_snapshot_positions(self) -> List[StockPosition]:
        return list(self._positions)

    def get_position(self, location_id: str, sku_id: str) -> Optional[StockPosition]:
        return self._pos_by_key.get((location_id, sku_id))

    def get_weekly_stock(self, store_id: str, sku_id: str) -> List[WeeklyStock]:
        return list(self._weekly_by_store_sku.get((store_id, sku_id), []))

    def get_all_weekly_stock(self) -> List[WeeklyStock]:
        return list(self._weekly_stock)

    def get_warehouse_inbound(self) -> List[WarehouseInbound]:
        return list(self._inbound)


class SalesRepository(ISalesRepository):
    def __init__(self, sales_lines: List[SalesLine]):
        self._sales_lines = sales_lines
        self._by_store: Dict[str, List[SalesLine]] = {}
        for line in sales_lines:
            self._by_store.setdefault(line.store_id, []).append(line)

    def get_all_sales_lines(self) -> List[SalesLine]:
        return self._sales_lines

    def get_sales_lines_by_store(self, store_id: str) -> List[SalesLine]:
        return list(self._by_store.get(store_id, []))


class RulesRepository(IRulesRepository):
    def __init__(
        self,
        min_display: Dict[Tuple[str, str], int],
        flagship_protected: Dict[str, Set[str]],
        lead_times: List[LeadTimeRule],
        stores_by_id: Dict[str, Store],
        data_issues: List[DataIssue],
    ):
        self._min_display = min_display
        self._flagship_protected = flagship_protected
        self._lead_times = lead_times
        self._stores = stores_by_id
        self._data_issues = data_issues

    def get_min_display(self, tier: str, category: str) -> int:
        cat = category.strip()
        if cat in ("Safa", "Mala", "Stole"):
            cat = "Accessories (Safa/Mala/Stole)"
        return self._min_display.get((tier, cat), 0)

    def get_lead_time_days(self, from_location: str, to_location: str) -> int:
        if from_location == to_location:
            return 0

        # Warehouse to Store
        if from_location == "WH-KOL":
            to_store = self._stores.get(to_location)
            if not to_store:
                return 4  # Default fallback
            zone = to_store.zone.lower()
            if "east" in zone:
                return 3
            elif "north" in zone:
                return 4
            elif "south" in zone:
                return 6
            return 4

        # Store to Warehouse
        if to_location == "WH-KOL":
            return 999  # No direct forward route configured

        # Store to Store
        from_store = self._stores.get(from_location)
        to_store = self._stores.get(to_location)
        if not from_store or not to_store:
            return 7

        if from_store.city == to_store.city:
            return 2
        elif from_store.zone == to_store.zone:
            return 4
        else:
            return 7

    def get_flagship_protected_styles(self, store_id: str) -> Set[str]:
        return set(self._flagship_protected.get(store_id, set()))

    def get_all_data_issues(self) -> List[DataIssue]:
        return list(self._data_issues)


class InMemoryRepositoryContainer:
    """Unified container implementing and exposing all domain repositories."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.stores: StoreRepository
        self.items: ItemRepository
        self.stock: StockRepository
        self.sales: SalesRepository
        self.rules: RulesRepository
        self.sync()

    def sync(self) -> None:
        """Loads and indexes data from self.data_dir."""
        adapter = CSVDataSourceAdapter(self.data_dir)
        raw_stores = adapter.load_stores()
        raw_items = adapter.load_items()

        valid_sku_ids = {item.sku_id for item in raw_items}
        store_capacities = {s.store_id: s.stock_capacity_units for s in raw_stores}
        stores_by_id = {s.store_id: s for s in raw_stores}

        raw_weekly = adapter.load_weekly_stock(valid_sku_ids)

        # Build final week (2026-10-31) lookup for snapshot cross-check
        final_week_stock: Dict[Tuple[str, str], int] = {}
        for ws in raw_weekly:
            if ws.week_ending == CSVDataSourceAdapter.AS_OF_DATE:
                final_week_stock[(ws.store_id, ws.sku_id)] = ws.closing_on_hand

        raw_positions = adapter.load_stock_snapshot(
            valid_sku_ids, store_capacities, final_week_stock
        )
        raw_inbound = adapter.load_warehouse_inbound(valid_sku_ids)
        raw_sales = adapter.load_sales_lines(valid_sku_ids)
        raw_min_display = adapter.load_min_display()
        raw_protected = adapter.load_flagship_protected()
        raw_lead_times = adapter.load_lead_times()

        self.stores = StoreRepository(raw_stores)
        self.items = ItemRepository(raw_items)
        self.stock = StockRepository(raw_positions, raw_weekly, raw_inbound)
        self.sales = SalesRepository(raw_sales)
        self.rules = RulesRepository(
            min_display=raw_min_display,
            flagship_protected=raw_protected,
            lead_times=raw_lead_times,
            stores_by_id=stores_by_id,
            data_issues=adapter.data_issues,
        )
