"""Abstract repository interfaces following the Repository Design Pattern."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple
from src.domain.models import (
    DataIssue,
    FlagshipProtectedRule,
    Item,
    LeadTimeRule,
    MinDisplayRule,
    SalesLine,
    StockPosition,
    Store,
    WarehouseInbound,
    WeeklyStock,
)


class IStoreRepository(ABC):
    """Interface for Store operations."""

    @abstractmethod
    def get_all(self) -> List[Store]:
        """Return all stores."""
        pass

    @abstractmethod
    def get_by_id(self, store_id: str) -> Optional[Store]:
        """Return store by ID."""
        pass


class IItemRepository(ABC):
    """Interface for Item (SKU) operations."""

    @abstractmethod
    def get_all(self) -> List[Item]:
        """Return all non-packaging items."""
        pass

    @abstractmethod
    def get_by_id(self, sku_id: str) -> Optional[Item]:
        """Return item by SKU ID."""
        pass

    @abstractmethod
    def get_by_style(self, style_id: str) -> List[Item]:
        """Return all items belonging to a style."""
        pass


class IStockRepository(ABC):
    """Interface for inventory position and weekly stock operations."""

    @abstractmethod
    def get_snapshot_positions(self) -> List[StockPosition]:
        """Return all snapshot positions."""
        pass

    @abstractmethod
    def get_position(self, location_id: str, sku_id: str) -> Optional[StockPosition]:
        """Return position by location and SKU."""
        pass

    @abstractmethod
    def get_weekly_stock(self, store_id: str, sku_id: str) -> List[WeeklyStock]:
        """Return weekly stock history for store and SKU."""
        pass

    @abstractmethod
    def get_all_weekly_stock(self) -> List[WeeklyStock]:
        """Return all weekly stock history."""
        pass

    @abstractmethod
    def get_warehouse_inbound(self) -> List[WarehouseInbound]:
        """Return planned warehouse inbound shipments."""
        pass


class ISalesRepository(ABC):
    """Interface for sales transaction queries."""

    @abstractmethod
    def get_all_sales_lines(self) -> List[SalesLine]:
        """Return all clean sales lines (non-packaging)."""
        pass

    @abstractmethod
    def get_sales_lines_by_store(self, store_id: str) -> List[SalesLine]:
        """Return clean sales lines for a store."""
        pass


class IRulesRepository(ABC):
    """Interface for stock movement rules and constraints."""

    @abstractmethod
    def get_min_display(self, tier: str, category: str) -> int:
        """Return minimum display quantity for tier and category."""
        pass

    @abstractmethod
    def get_lead_time_days(self, from_location: str, to_location: str) -> int:
        """Return transit days between locations based on route matrix."""
        pass

    @abstractmethod
    def get_flagship_protected_styles(self, store_id: str) -> Set[str]:
        """Return set of protected style IDs for an S++ flagship store."""
        pass

    @abstractmethod
    def get_all_data_issues(self) -> List[DataIssue]:
        """Return all quarantined data issues."""
        pass
