from __future__ import annotations

from fakes import item, make_inputs, pos, store

from src.moves.generation import MoveGenerationService
from src.moves.ledger import InventoryLedger
from src.moves.models import HardRule, MoveType
from src.moves.validation import ConstraintValidationService

R = store("R", "Kolkata", "East")


def D(sid, city="Kolkata", zone="East", tier="A"):
    return store(sid, city, zone, tier)


def run(stores, items, positions, vel=None, covers=None, flagship=frozenset()):
    """covers: store -> style cover (default: R 1.0, others 100.0); style velocity 1.0 everywhere."""
    covers = covers or {}
    vel = vel or {("R", "A"): 1.0}
    inp = make_inputs(
        stores=tuple(stores), items=tuple(items), positions=tuple(positions),
        sku_velocity=vel,
        style_velocity={(s.store_id, "STY1"): 1.0 for s in stores},
        style_cover={(s.store_id, "STY1"): covers.get(s.store_id, 1.0 if s.store_id == "R" else 100.0)
                     for s in stores},
        flagship=flagship,
    )
    v = ConstraintValidationService(inp)
    return MoveGenerationService(inp, v).generate(InventoryLedger.from_inputs(inp)), v


def srcs(res):
    return [(m.from_location, m.to_location, m.sku_id, m.qty) for m in res.accepted]


def test_route_order_city_zone_cross():
    stores = [R, D("Dx", "Delhi", "North"), D("Dz", "Howrah"), D("Dc")]
    p = [pos(s, "A", 100) for s in ("Dx", "Dz", "Dc")]
    res, _ = run(stores, [item("A")], p)  # T = 7 (cross zone viable)
    assert srcs(res) == [("Dc", "R", "A", 7)]
    assert res.accepted[0].move_type is MoveType.S2S and res.accepted[0].route_days == 2
    # remove the city donor -> same zone wins over cross zone
    res, _ = run(stores[:3], [item("A")], p[:2])
    assert srcs(res) == [("Dz", "R", "A", 7)] and res.accepted[0].route_days == 4


def test_equal_route_higher_cover_then_store_id():
    stores = [R, D("D1"), D("D2"), D("D3")]
    p = [pos(s, "A", 100) for s in ("D1", "D2", "D3")]
    res, _ = run(stores, [item("A")], p, covers={"D1": 60.0, "D2": 80.0, "D3": 80.0})
    assert srcs(res) == [("D2", "R", "A", 2)]


def test_ineligible_donors_skipped():
    stores = [R, D("D1"), D("D2"), D("D3"), D("Z")]
    p = [pos("D1", "A", 100), pos("D2", "A", 35), pos("D3", "A", 100), pos("Z", "A", 100)]
    res, _ = run(stores, [item("A")], p, covers={"D1": 45.0, "D3": None})
    # D1 cover 45 (not > 45), D2 category on-hand == min display 35, D3 None cover
    assert srcs(res) == [("Z", "R", "A", 2)]


def test_donor_ineligible_after_earlier_move_d22():
    stores = [R, D("D1"), D("D2", "Howrah")]
    items = [item("A", mrp=2000), item("B", mrp=1000)]
    p = [pos(d, s, 50) for d in ("D1", "D2") for s in ("A", "B")]
    res, _ = run(stores, items, p, vel={("R", "A"): 1.0, ("R", "B"): 1.0}, covers={"D1": 46.0})
    # T = 4. A (higher mrp) takes 4 from D1 -> cover 42 <= 45, so B must use D2
    assert srcs(res) == [("D1", "R", "A", 4), ("D2", "R", "B", 4)]


def test_flagship_blocks_then_next_donor():
    stores = [R, D("D1", tier="S++"), D("D2", "Howrah")]
    p = [pos("D1", "A", 200), pos("D2", "A", 100)]
    res, v = run(stores, [item("A")], p, flagship=frozenset({("D1", "STY1")}))
    assert srcs(res) == [("D2", "R", "A", 4)]
    assert [(r.rule_violated, r.from_location) for r in v.rejected] == [(HardRule.R3, "D1")]


def test_several_donors_fill_one_need():
    stores = [R, D("D1"), D("D2", "Howrah")]
    items = [item("A"), item("C", "STY2")]
    p = [pos("D1", "A", 3), pos("D1", "C", 100), pos("D2", "A", 50)]
    res, v = run(stores, items, p)  # T = 4, need 4
    assert srcs(res) == [("D1", "R", "A", 3), ("D2", "R", "A", 1)]
    assert res.unfulfilled == [] and v.rejected == []


def test_w2s_partial_plus_s2s_topup():
    stores = [R, D("D1")]
    res, _ = run(stores, [item("A")], [pos("WH-KOL", "A", 2), pos("D1", "A", 100)])  # T = 3
    assert srcs(res) == [("WH-KOL", "R", "A", 2), ("D1", "R", "A", 1)]
    assert [m.move_type for m in res.accepted] == [MoveType.W2S, MoveType.S2S]
    assert res.unfulfilled == []


def test_quarantine_excluded():
    stores = [R, D("D1"), D("D2", "Howrah")]
    p = [pos("D1", "A", 100, quarantined=True), pos("D2", "A", 100)]
    res, _ = run(stores, [item("A")], p)
    assert srcs(res) == [("D2", "R", "A", 4)]  # T = 4: D1 is not a viable route either


def test_unfulfilled():
    # no viable donor: one unfulfilled, no rejection, no move
    res, v = run([R, D("D1")], [item("A")], [pos("D1", "A", 100)], covers={"D1": 45.0})
    assert res.accepted == [] and v.rejected == []
    [u] = res.unfulfilled
    assert (u.store_id, u.needed_qty, u.unfilled_qty) == ("R", 3, 3)  # no viable route: T = longest route (WH East 3d)
    # donor runs out: partial move, remainder unfulfilled, still no rejection
    res, v = run([R, D("D1")], [item("A"), item("C", "STY2")],
                 [pos("D1", "A", 1), pos("D1", "C", 100)])
    assert srcs(res) == [("D1", "R", "A", 1)] and v.rejected == []
    [u] = res.unfulfilled
    assert (u.needed_qty, u.unfilled_qty, u.reason) == (2, 1, "unfilled 1 of 2 after W2S and S2S")
