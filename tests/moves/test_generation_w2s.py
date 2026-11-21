from __future__ import annotations

from fakes import item, make_inputs, pos, store

from src.moves.generation import MoveGenerationService
from src.moves.ledger import InventoryLedger
from src.moves.models import HardRule, MoveType
from src.moves.validation import ConstraintValidationService


def run(stores, items, positions, vel, cover=1.0):
    inp = make_inputs(
        stores=tuple(stores), items=tuple(items), positions=tuple(positions),
        sku_velocity=vel,
        style_velocity={(s.store_id, "STY1"): 1.0 for s in stores},
        style_cover={(s.store_id, "STY1"): cover for s in stores},
    )
    v = ConstraintValidationService(inp)
    res = MoveGenerationService(inp, v).generate(InventoryLedger.from_inputs(inp))
    return res, v


R = lambda **kw: store("R", "Kolkata", "East", **kw)  # East: WH 3 days -> T = 3


def test_priority_and_exhaustion():
    # R2 has the higher velocity x mrp -> served first; WH exhausted, R1 left over, no rejection
    res, v = run([store("R1"), store("R2")], [item("A")],
                 [pos("WH-KOL", "A", 3)], {("R1", "A"): 1.0, ("R2", "A"): 2.0})
    assert [(m.to_location, m.qty) for m in res.accepted] == [("R2", 3)]
    m = res.accepted[0]
    assert (m.move_type, m.from_location, m.route_days) == (MoveType.W2S, "WH-KOL", 3)
    assert [(u.store_id, u.needed_qty, u.unfilled_qty) for u in res.unfulfilled] == [
        ("R2", 6, 3), ("R1", 3, 3)]
    assert res.unfulfilled[1].reason == "unfilled 3 of 3 after W2S and S2S"
    assert v.rejected == []


def test_only_warehouse_source():
    # donor D has stock and cover but W2S phase must only use WH-KOL
    res, _ = run([R(), store("D", "Kolkata", "East")], [item("A")],
                 [pos("WH-KOL", "A", 10), pos("D", "A", 500)], {("R", "A"): 1.0})
    assert res.accepted and {m.from_location for m in res.accepted} == {"WH-KOL"}


def test_partial_fill_then_unfulfilled_residual():
    res, _ = run([R()], [item("A")], [pos("WH-KOL", "A", 2)], {("R", "A"): 1.0})
    assert [m.qty for m in res.accepted] == [2]
    assert res.unfulfilled[0].unfilled_qty == 1 and res.unfulfilled[0].needed_qty == 3


def test_w2s_rules_logged():
    res, v = run([R()], [item("A")], [pos("WH-KOL", "A", 10), pos("R", "A", 0, 1)],
                 {("R", "A"): 3.0})  # need 9-1 = 8, R4 blocks
    assert res.accepted == []
    assert [r.rule_violated for r in v.rejected] == [HardRule.R4]
    res, v = run([R(stock_capacity_units=0)], [item("A")], [pos("WH-KOL", "A", 10)],
                 {("R", "A"): 1.0})
    assert res.accepted == []
    assert [r.rule_violated for r in v.rejected] == [HardRule.R2]


def test_partial_r2_room_trims_without_log():
    res, v = run([R(stock_capacity_units=2)], [item("A")], [pos("WH-KOL", "A", 10)],
                 {("R", "A"): 1.0})
    assert [m.qty for m in res.accepted] == [2]
    assert v.rejected == []
    assert res.unfulfilled[0].unfilled_qty == 1


def test_quarantine_excluded():
    # quarantined WH stock is not a source -> no viable route, unfulfilled, no move
    res, v = run([R()], [item("A")], [pos("WH-KOL", "A", 10, quarantined=True)], {("R", "A"): 1.0})
    assert res.accepted == [] and v.rejected == []
    assert res.unfulfilled[0].reason == "no viable route; threshold 3d"


def test_receiver_quarantined():
    res, v = run([R()], [item("A")], [pos("WH-KOL", "A", 10), pos("R", "A", 0, quarantined=True)],
                 {("R", "A"): 1.0})
    assert res.accepted == [] and v.rejected == []
    [u] = res.unfulfilled
    assert (u.needed_qty, u.unfilled_qty, u.reason) == (3, 3, "receiver position quarantined")


def test_non_viable_reported():
    res, v = run([R()], [item("A")], [], {("R", "A"): 1.0})
    [u] = res.unfulfilled
    assert (u.needed_qty, u.unfilled_qty, u.reason) == (3, 3, "no viable route; threshold 3d")
    assert res.accepted == [] and v.rejected == []
