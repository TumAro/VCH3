from __future__ import annotations

from src.moves.inputs import EngineInputs, Item, Position, Store

# Typed in from data/csv/min_display.csv (24 rows); unit tests never read real data.
_ACC = "Accessories (Safa/Mala/Stole)"
_CATS = ("Kurta Set", "Sherwani", "Indo-Western", "Jacket", "Mojari", _ACC)
_UNITS = {
    "S++": (120, 30, 25, 40, 25, 20),
    "S+": (70, 18, 15, 25, 15, 12),
    "A": (35, 8, 6, 12, 8, 6),
    "B": (25, 5, 4, 8, 6, 4),
}
DEFAULT_MIN_DISPLAY = {
    (tier, cat): n for tier, row in _UNITS.items() for cat, n in zip(_CATS, row)
}


def store(store_id="S1", city="Kolkata", zone="East", tier="A", stock_capacity_units=1000):
    return Store(store_id, city, zone, tier, stock_capacity_units)


def item(sku_id="SKU1", style_id="STY1", category="Kurta Set", mrp=1000):
    return Item(sku_id, style_id, category, mrp)


def pos(location_id="S1", sku_id="SKU1", on_hand=0, in_transit=0, quarantined=False):
    return Position(location_id, sku_id, on_hand, in_transit, quarantined)


def make_inputs(**overrides):
    kw = dict(
        stores=(),
        items=(),
        positions=(),
        sku_velocity={},
        style_velocity={},
        style_cover={},
        min_display=dict(DEFAULT_MIN_DISPLAY),
        flagship=frozenset(),
    )
    kw.update(overrides)
    return EngineInputs(**kw)
