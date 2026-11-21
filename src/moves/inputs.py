from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Mapping, Optional, Tuple

from src.moves.config import WH_LOCATION


@dataclass(frozen=True)
class Store:
    store_id: str
    city: str
    zone: str
    tier: str
    stock_capacity_units: int


@dataclass(frozen=True)
class Item:
    sku_id: str
    style_id: str
    category: str
    mrp: int


@dataclass(frozen=True)
class Position:
    location_id: str
    sku_id: str
    on_hand: int
    in_transit: int
    quarantined: bool = False


@dataclass(frozen=True)
class EngineInputs:
    stores: Tuple[Store, ...]
    items: Tuple[Item, ...]
    positions: Tuple[Position, ...]
    sku_velocity: Mapping[Tuple[str, str], float]
    style_velocity: Mapping[Tuple[str, str], float]
    style_cover: Mapping[Tuple[str, str], Optional[float]]
    min_display: Mapping[Tuple[str, str], int]
    flagship: frozenset
    wh_velocity: Optional[Mapping[str, float]] = None

    def __post_init__(self) -> None:
        seen = set()
        for p in self.positions:
            if p.sku_id not in self._items:
                raise ValueError(f"position SKU {p.sku_id!r} not in items")
            if p.location_id != WH_LOCATION and p.location_id not in self._stores:
                raise ValueError(f"unknown location {p.location_id!r}")
            key = (p.location_id, p.sku_id)
            if key in seen:
                raise ValueError(f"duplicate position {key}")
            seen.add(key)

    @cached_property
    def _stores(self) -> dict:
        return {s.store_id: s for s in self.stores}

    @cached_property
    def _items(self) -> dict:
        return {i.sku_id: i for i in self.items}

    @cached_property
    def _positions(self) -> dict:
        return {(p.location_id, p.sku_id): p for p in self.positions}

    @cached_property
    def _styles(self) -> dict:
        d: dict = {}
        for i in sorted(self.items, key=lambda i: i.sku_id):
            d.setdefault(i.style_id, []).append(i.sku_id)
        return {k: tuple(v) for k, v in d.items()}

    def store(self, store_id: str) -> Store:
        return self._stores[store_id]

    def item(self, sku_id: str) -> Item:
        return self._items[sku_id]

    def skus_of_style(self, style_id: str) -> Tuple[str, ...]:
        return self._styles.get(style_id, ())

    def position(self, location_id: str, sku_id: str) -> Position:
        return self._positions.get((location_id, sku_id)) or Position(location_id, sku_id, 0, 0)

    def sku_vel(self, store_id: str, sku_id: str) -> float:
        return self.sku_velocity.get((store_id, sku_id), 0.0)

    def style_vel(self, store_id: str, style_id: str) -> float:
        return self.style_velocity.get((store_id, style_id), 0.0)

    def cover(self, store_id: str, style_id: str) -> Optional[float]:
        return self.style_cover.get((store_id, style_id))
