from __future__ import annotations

import dataclasses

import pytest

from fakes import DEFAULT_MIN_DISPLAY, item, make_inputs, pos, store
from src.moves.models import (
    ApprovedMove,
    CandidateMove,
    EngineResult,
    HardRule,
    MoveType,
    RejectedMove,
    UnfulfilledDeficit,
)


def test_frozen():
    for obj in (store(), item(), pos()):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, dataclasses.fields(obj)[0].name, "x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        make_inputs().stores = ()
    c = CandidateMove(MoveType.W2S, "WH-KOL", "S1", "SKU1", "STY1", 5, 3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.qty = 1


def test_default_min_display_has_24_rows():
    assert len(DEFAULT_MIN_DISPLAY) == 24
    assert DEFAULT_MIN_DISPLAY[("S++", "Kurta Set")] == 120
    assert DEFAULT_MIN_DISPLAY[("B", "Accessories (Safa/Mala/Stole)")] == 4


def test_lookups_and_missing_defaults():
    inp = make_inputs(
        stores=(store("S1"),),
        items=(item("SKU1"),),
        positions=(pos("S1", "SKU1", on_hand=7, in_transit=2),),
        sku_velocity={("S1", "SKU1"): 1.5},
        style_velocity={("S1", "STY1"): 2.0},
        style_cover={("S1", "STY1"): 10.0},
    )
    assert inp.store("S1").tier == "A"
    assert inp.item("SKU1").mrp == 1000
    assert inp.position("S1", "SKU1").on_hand == 7
    assert inp.sku_vel("S1", "SKU1") == 1.5
    assert inp.style_vel("S1", "STY1") == 2.0
    assert inp.cover("S1", "STY1") == 10.0
    # D-23: missing position = zeros, missing velocity = 0.0, missing cover = None
    p = inp.position("S1", "NOPE")
    assert (p.on_hand, p.in_transit, p.quarantined) == (0, 0, False)
    assert inp.sku_vel("S1", "NOPE") == 0.0
    assert inp.style_vel("S1", "NOPE") == 0.0
    assert inp.cover("S1", "NOPE") is None
    assert inp.wh_velocity is None


def test_missing_min_display_raises_keyerror():
    inp = make_inputs(min_display={})
    with pytest.raises(KeyError):
        inp.min_display[("A", "Kurta Set")]


def test_unknown_store_item_keyerror():
    inp = make_inputs()
    with pytest.raises(KeyError):
        inp.store("X")
    with pytest.raises(KeyError):
        inp.item("X")


def test_value_errors():
    s, i = (store("S1"),), (item("SKU1"),)
    with pytest.raises(ValueError):
        make_inputs(stores=s, items=i, positions=(pos("S1", "SKU1"), pos("S1", "SKU1")))
    with pytest.raises(ValueError):
        make_inputs(stores=s, items=i, positions=(pos("S1", "OTHER"),))
    with pytest.raises(ValueError):
        make_inputs(stores=s, items=i, positions=(pos("S9", "SKU1"),))
    make_inputs(stores=s, items=i, positions=(pos("WH-KOL", "SKU1"),))  # ok


def test_skus_of_style_sorted():
    inp = make_inputs(items=(item("C", "S"), item("A", "S"), item("B", "T")))
    assert inp.skus_of_style("S") == ("A", "C")
    assert inp.skus_of_style("none") == ()


def test_candidate_with_qty():
    c = CandidateMove(MoveType.S2S, "A", "B", "SKU1", "STY1", 5, 2)
    d = c.with_qty(3)
    assert d.qty == 3 and c.qty == 5 and d.to_location == "B"


def test_enums():
    assert [r.value for r in HardRule] == ["R1", "R2", "R3", "R4", "R5", "R6"]
    assert {m.value for m in MoveType} == {"W2S", "S2S"}


def names(cls):
    return [f.name for f in dataclasses.fields(cls)]


def test_rejected_move_fields_match_req7():
    assert names(RejectedMove) == [
        "move_type", "from_location", "to_location", "sku_id", "qty",
        "rule_violated", "rejection_reason",
    ]


def test_approved_and_other_fields():
    assert names(ApprovedMove) == [
        "move_type", "from_location", "to_location", "sku_id", "style_id", "qty",
        "value_mrp", "route_days", "dispatch_date", "arrival_date",
        "requires_human_approval", "reason", "receiver_cover", "velocity", "donor_cover",
    ]
    assert names(UnfulfilledDeficit) == [
        "store_id", "style_id", "sku_id", "needed_qty", "unfilled_qty", "reason",
    ]
    assert names(EngineResult) == ["approved_moves", "rejected_moves", "unfulfilled_deficits"]
