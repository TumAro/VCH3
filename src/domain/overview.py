"""Read-only result models for the network overview (dashboard Part A)."""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class StoreOverview:
    store_id: str
    tier: str
    revenue: float
    on_hand: int
    in_transit: int
    capacity: int
    utilisation_pct: float
    zero_stock_skus: int


@dataclass(frozen=True)
class CityOverview:
    city: str
    store_count: int
    revenue: float
    share_of_state_pct: float
    stores: List[StoreOverview] = field(default_factory=list)


@dataclass(frozen=True)
class StateOverview:
    state: str
    store_count: int
    revenue: float
    share_pct: float
    cities: List[CityOverview] = field(default_factory=list)


@dataclass(frozen=True)
class NetworkOverview:
    total_revenue: float
    store_count: int
    states: List[StateOverview] = field(default_factory=list)


@dataclass(frozen=True)
class MonthlyRevenue:
    months: List[str]
    series: Dict[str, List[float]]
