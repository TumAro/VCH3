from __future__ import annotations

import random

from fakes import item, make_inputs, pos, store
from independent_validator import find_violations

from src.moves.engine import MoveEngine
from src.moves.models import MoveType


def inputs():
    # 6 stores over 3 zones; STY1 (A, B) has W2S + S2S, STY2 (C) has no stock anywhere donor-side.
    stores = (
        store("E1", "Kolkata", "East"), store("E2", "Kolkata", "East"),
        store("N1", "Delhi", "North"), store("N2", "Delhi", "North"),
        store("S1", "Chennai", "South"), store("S2", "Chennai", "South"),
    )
    items = (
        item("A", "STY1", mrp=5000), item("B", "STY1", mrp=5000), item("C", "STY2", mrp=2000),
    )
    positions = (
        pos("WH-KOL", "A", 5), pos("WH-KOL", "B", 50),
        pos("E1", "A", 1), pos("E1", "B", 2), pos("E1", "C", 0),
        pos("N1", "A", 0), pos("N1", "B", 0, in_transit=3),  # R4 rejection on B
        pos("S1", "A", 0), pos("S1", "B", 1),
        pos("E2", "A", 150), pos("E2", "B", 150),
        pos("N2", "A", 120), pos("S2", "A", 120),
    )
    sku_velocity = {
        ("E1", "A"): 2.0, ("E1", "B"): 2.0, ("E1", "C"): 1.0,
        ("N1", "A"): 2.0, ("N1", "B"): 2.0,
        ("S1", "A"): 1.0, ("S1", "B"): 1.0,
    }
    style_velocity = {("E1", "STY1"): 4.0, ("N1", "STY1"): 4.0, ("S1", "STY1"): 2.0,
                      ("E1", "STY2"): 1.0, ("E2", "STY1"): 2.0, ("N2", "STY1"): 2.0, ("S2", "STY1"): 2.0}
    style_cover = {("E1", "STY1"): 0.75, ("N1", "STY1"): 0.0, ("S1", "STY1"): 0.5,
                   ("E1", "STY2"): 0.0, ("E2", "STY1"): 150.0, ("N2", "STY1"): 60.0, ("S2", "STY1"): 60.0}
    return make_inputs(stores=stores, items=items, positions=positions, sku_velocity=sku_velocity,
                       style_velocity=style_velocity, style_cover=style_cover)


def shuffled(inp, seed=0):
    rng = random.Random(seed)

    def sh(seq):
        seq = list(seq)
        rng.shuffle(seq)
        return seq

    return make_inputs(
        stores=tuple(sh(inp.stores)), items=tuple(sh(inp.items)), positions=tuple(sh(inp.positions)),
        sku_velocity=dict(sh(inp.sku_velocity.items())),
        style_velocity=dict(sh(inp.style_velocity.items())),
        style_cover=dict(sh(inp.style_cover.items())),
        min_display=dict(sh(inp.min_display.items())),
        flagship=inp.flagship,
    )


def test_fixture_is_rich():
    inp = inputs()
    res = MoveEngine().run(inp)
    assert {m.move_type for m in res.approved_moves} == {MoveType.W2S, MoveType.S2S}
    assert res.rejected_moves
    assert res.unfulfilled_deficits
    assert find_violations(inp, res.approved_moves) == []


def test_determinism_repeat_and_shuffled():
    inp = inputs()
    first = MoveEngine().run(inp)
    assert first == MoveEngine().run(inp)
    assert find_violations(inp, first.approved_moves) == []
    for seed in range(5):
        sh = shuffled(inp, seed)
        res = MoveEngine().run(sh)
        assert res == first
        assert find_violations(sh, res.approved_moves) == []
