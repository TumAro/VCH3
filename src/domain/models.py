"""Domain entities for Manyavar Daily Stock Move Recommender."""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Store:
    store_id: str
    city: str
    state: str
    zone: str
    tier: str
    size_sqft: int
    stock_capacity_units: int
    opened_on: date
    area_manager_id: str
    is_new_store: bool = False


@dataclass(frozen=True)
class Item:
    sku_id: str
    style_id: str
    style_name: str
    category: str
    size: str
    mrp: float
    cost_price: float
    launch_date: Optional[date]
    is_core_style: bool
    is_packaging: bool = False


@dataclass(frozen=True)
class StockPosition:
    location_id: str
    sku_id: str
    on_hand: int
    in_transit: int
    in_transit_arrives_on: Optional[date]
    oldest_stock_received_on: Optional[date]
    is_untrusted: bool = False
    untrusted_reason: Optional[str] = None

    @property
    def effective_stock(self) -> int:
        return self.on_hand + self.in_transit


@dataclass(frozen=True)
class WeeklyStock:
    week_ending: date
    store_id: str
    sku_id: str
    closing_on_hand: int
    days_in_stock: int


@dataclass(frozen=True)
class SalesLine:
    bill_id: str
    bill_date: date
    store_id: str
    salesperson_id: str
    customer_id: str
    sku_id: str
    qty: int
    mrp: float
    selling_price: float

    @property
    def line_revenue(self) -> float:
        return self.qty * self.selling_price

    @property
    def discount_per_unit(self) -> float:
        return self.mrp - self.selling_price


@dataclass(frozen=True)
class WarehouseInbound:
    expected_date: date
    sku_id: str
    qty: int
    status: str


@dataclass(frozen=True)
class LeadTimeRule:
    route: str
    days: int


@dataclass(frozen=True)
class DataIssue:
    table: str
    key: str
    column: str
    value_seen: str
    rule_violated: str
    action_taken: str


@dataclass(frozen=True)
class MinDisplayRule:
    tier: str
    category: str
    min_display_units: int


@dataclass(frozen=True)
class FlagshipProtectedRule:
    store_id: str
    rank: int
    style_id: str
