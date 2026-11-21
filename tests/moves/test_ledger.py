from __future__ import annotations

from fakes import item, make_inputs, pos, store
from src.moves.ledger import InventoryLedger
from src.moves.models import CandidateMove, MoveType


def _inputs():
    return make_inputs(
        stores=(store("A"), store("B")),
        items=(
            item("K1", "S1", "Kurta Set"),
            item("K2", "S1", "Kurta Set"),
            item("M1", "S2", "Mala"),
        ),
        positions=(
            pos("A", "K1", on_hand=10, in_transit=2),
            pos("A", "K2", on_hand=-4, in_transit=1),
            pos("A", "M1", on_hand=5, quarantined=True),
            pos("B", "K1", on_hand=3, in_transit=4),
            pos("WH-KOL", "K1", on_hand=50),
        ),
    )


def _s2s(qty=4):
    return CandidateMove(MoveType.S2S, "A", "B", "K1", "S1", qty, 2)


def test_aggregates_clamp_and_count_quarantined():
    led = InventoryLedger.from_inputs(_inputs())
    assert led.category_on_hand("A", "Kurta Set") == 10  # -4 clamped to 0
    assert led.category_on_hand("A", "Accessories (Safa/Mala/Stole)") == 5  # quarantined counted
    assert led.capacity_load("A") == 10 + 2 + 0 + 1 + 5
    assert led.capacity_load("B") == 7


def test_quarantined_and_missing_positions():
    led = InventoryLedger.from_inputs(_inputs())
    assert led.is_quarantined("A", "M1") is True
    assert led.available("A", "M1") == 0
    assert led.available("A", "K2") == 0  # negative on-hand
    assert led.available("B", "M1") == 0
    assert led.snapshot_in_transit("B", "M1") == 0
    assert led.is_quarantined("B", "M1") is False
    assert led.snapshot_in_transit("B", "K1") == 4


def test_s2s_apply():
    led = InventoryLedger.from_inputs(_inputs())
    led.apply(_s2s())
    assert led.available("A", "K1") == 6
    assert led.category_on_hand("A", "Kurta Set") == 6
    assert led.style_units_out("A", "S1") == 4
    assert led.capacity_load("B") == 11
    assert led.capacity_load("A") == 18  # outbound never frees capacity
    assert led.category_on_hand("B", "Kurta Set") == 3  # inbound not added
    assert led.snapshot_in_transit("B", "K1") == 4


def test_w2s_apply():
    led = InventoryLedger.from_inputs(_inputs())
    led.apply(CandidateMove(MoveType.W2S, "WH-KOL", "B", "K1", "S1", 20, 3))
    assert led.available("WH-KOL", "K1") == 30
    assert led.capacity_load("B") == 27
    assert led.style_units_out("WH-KOL", "S1") == 20
