from __future__ import annotations

from fakes import item, make_inputs, pos, store
from independent_validator import find_violations

from src.moves.engine import MoveEngine
from src.moves.models import MoveType


def run(inp):
    res = MoveEngine().run(inp)
    assert find_violations(inp, res.approved_moves) == []  # AC-1
    return res


def key(res):
    return [(m.move_type, m.from_location, m.to_location, m.sku_id, m.qty) for m in res.approved_moves]


def test_wh_exhaustion_falls_through_to_s2s():
    # need = ceil(2*3) - 0 = 6; WH holds 4, donor D (same city) covers the rest.
    inp = make_inputs(
        stores=(store("R", "Kolkata", "East"), store("D", "Kolkata", "East")),
        items=(item("A"),),
        positions=(pos("WH-KOL", "A", 4), pos("D", "A", 100)),
        sku_velocity={("R", "A"): 2.0},
        style_velocity={("R", "STY1"): 2.0, ("D", "STY1"): 1.0},
        style_cover={("R", "STY1"): 0.0, ("D", "STY1"): 100.0},
    )
    res = run(inp)
    assert key(res) == [(MoveType.W2S, "WH-KOL", "R", "A", 4), (MoveType.S2S, "D", "R", "A", 2)]
    assert res.rejected_moves == () and res.unfulfilled_deficits == ()


def test_tie_equal_revenue_orders_by_sku_then_store():
    # Equal velocity x mrp everywhere; WH has 6 units of each SKU, each need is 6, only one fits per SKU.
    inp = make_inputs(
        stores=(store("E2", "Kolkata", "East"), store("E1", "Kolkata", "East")),
        items=(item("B", mrp=1000), item("A", mrp=1000)),
        positions=(pos("WH-KOL", "A", 6), pos("WH-KOL", "B", 6)),
        sku_velocity={(s, k): 2.0 for s in ("E1", "E2") for k in ("A", "B")},
        style_velocity={("E1", "STY1"): 4.0, ("E2", "STY1"): 4.0},
        style_cover={("E1", "STY1"): 0.0, ("E2", "STY1"): 0.0},
    )
    res = run(inp)
    # Lower store_id wins each SKU; both SKUs served, E2 left unserved.
    assert key(res) == [
        (MoveType.W2S, "WH-KOL", "E1", "A", 6),
        (MoveType.W2S, "WH-KOL", "E1", "B", 6),
    ]
    assert {u.store_id for u in res.unfulfilled_deficits} == {"E2"}


def test_tie_sku_order_when_supply_shared():
    # One receiver, same revenue loss for A and B; WH can only fully serve one -> A first.
    inp = make_inputs(
        stores=(store("E1", "Kolkata", "East"),),
        items=(item("B", mrp=1000), item("A", mrp=1000)),
        positions=(pos("WH-KOL", "A", 6), pos("WH-KOL", "B", 6)),
        sku_velocity={("E1", "A"): 2.0, ("E1", "B"): 2.0},
        style_velocity={("E1", "STY1"): 4.0},
        style_cover={("E1", "STY1"): 0.0},
    )
    res = run(inp)
    assert [m.sku_id for m in res.approved_moves] == ["A", "B"]


def test_tie_donors_equal_route_and_cover_pick_lower_store_id():
    inp = make_inputs(
        stores=(store("R", "Kolkata", "East"), store("D2", "Kolkata", "East"), store("D1", "Kolkata", "East")),
        items=(item("A"),),
        positions=(pos("D1", "A", 100), pos("D2", "A", 100)),
        sku_velocity={("R", "A"): 1.0},
        style_velocity={("R", "STY1"): 1.0, ("D1", "STY1"): 1.0, ("D2", "STY1"): 1.0},
        style_cover={("R", "STY1"): 0.0, ("D1", "STY1"): 100.0, ("D2", "STY1"): 100.0},
    )
    res = run(inp)
    assert [(m.from_location, m.qty) for m in res.approved_moves] == [("D1", 2)]


def test_zero_viable_donors_gives_unfulfilled_only():
    inp = make_inputs(
        stores=(store("R", "Kolkata", "East"), store("D", "Kolkata", "East")),
        items=(item("A"),),
        positions=(pos("D", "A", 10),),
        sku_velocity={("R", "A"): 2.0},
        style_velocity={("R", "STY1"): 2.0, ("D", "STY1"): 1.0},
        style_cover={("R", "STY1"): 0.0, ("D", "STY1"): 10.0},  # cover not above 45 d
    )
    res = run(inp)
    assert res.approved_moves == () and res.rejected_moves == ()
    assert [(u.store_id, u.sku_id) for u in res.unfulfilled_deficits] == [("R", "A")]
