from __future__ import annotations

from collections import defaultdict

from src.moves.config import WH_LOCATION, display_category
from src.moves.inputs import EngineInputs
from src.moves.models import CandidateMove


class InventoryLedger:
    """Simulated stock state: snapshot plus accepted moves (D-7, D-15, D-17)."""

    def __init__(self, inputs: EngineInputs) -> None:
        self._inputs = inputs
        self._out = defaultdict(int)  # (location, sku) -> units
        self._in = defaultdict(int)  # (store, sku) -> units
        self._style_out = defaultdict(int)  # (location, style) -> units
        self._cat_on_hand = defaultdict(int)  # (store, display cat)
        self._cap_load = defaultdict(int)  # store
        for p in inputs.positions:
            if p.location_id == WH_LOCATION:
                continue
            oh = max(0, p.on_hand)
            cat = display_category(inputs.item(p.sku_id).category)
            self._cat_on_hand[(p.location_id, cat)] += oh
            self._cap_load[p.location_id] += oh + p.in_transit

    @classmethod
    def from_inputs(cls, inputs: EngineInputs) -> "InventoryLedger":
        return cls(inputs)

    def available(self, location_id: str, sku_id: str) -> int:
        p = self._inputs.position(location_id, sku_id)
        if p.quarantined:
            return 0
        return max(0, p.on_hand - self._out[(location_id, sku_id)])

    def category_on_hand(self, store_id: str, display_category: str) -> int:
        return self._cat_on_hand[(store_id, display_category)]

    def capacity_load(self, store_id: str) -> int:
        return self._cap_load[store_id]

    def style_units_out(self, store_id: str, style_id: str) -> int:
        return self._style_out[(store_id, style_id)]

    def snapshot_in_transit(self, store_id: str, sku_id: str) -> int:
        return self._inputs.position(store_id, sku_id).in_transit

    def is_quarantined(self, location_id: str, sku_id: str) -> bool:
        return self._inputs.position(location_id, sku_id).quarantined

    def apply(self, move: CandidateMove) -> None:
        src, dst, q = move.from_location, move.to_location, move.qty
        self._out[(src, move.sku_id)] += q
        self._style_out[(src, move.style_id)] += q
        if src != WH_LOCATION:
            cat = display_category(self._inputs.item(move.sku_id).category)
            self._cat_on_hand[(src, cat)] -= q
        self._in[(dst, move.sku_id)] += q
        self._cap_load[dst] += q
