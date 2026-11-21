"""Immutable result models for velocity and cover calculations."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class FindingType(str, Enum):
    STOCKOUT_RISK = "STOCKOUT_RISK"
    AGEING_RISK = "AGEING_RISK"
    ZERO_SALES_DIAGNOSIS = "ZERO_SALES_DIAGNOSIS"


@dataclass(frozen=True)
class DailyVelocity:
    store_id: str
    sku_id: str
    quantity_sold: int
    days_in_stock: int
    velocity: float
    is_peer_fallback: bool = False
    peer_store_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AggregateVelocity:
    store_id: str
    level: str
    level_id: str
    quantity_sold: int
    days_in_stock: int
    velocity: float


@dataclass(frozen=True)
class InventoryPosition:
    store_id: str
    sku_id: str
    on_hand: int
    in_transit: int
    effective_stock: int
    daily_velocity: float
    cover_days: float
    stock_age_days: int


@dataclass(frozen=True)
class Finding:
    finding_type: FindingType
    store_id: str
    sku_id: Optional[str]
    style_id: Optional[str]
    metric_value: float
    diagnosis: str
    potential_revenue_loss: float = 0.0


@dataclass(frozen=True)
class VelocityCoverResult:
    sku_velocities: Tuple[DailyVelocity, ...]
    style_velocities: Tuple[AggregateVelocity, ...]
    category_velocities: Tuple[AggregateVelocity, ...]
    positions: Tuple[InventoryPosition, ...]
    findings: Tuple[Finding, ...]
