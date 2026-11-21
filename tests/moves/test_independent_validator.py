from __future__ import annotations

import ast
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from fakes import item, make_inputs, pos, store
from independent_validator import find_violations

from src.moves.models import ApprovedMove, MoveType


def inputs(**kw):
    base = dict(
        stores=(store("D"), store("R")),
        items=(item(),),
        positions=(
            pos("D", on_hand=100),
            pos("R", on_hand=5),
            pos("WH-KOL", on_hand=50),
        ),
        sku_velocity={("R", "SKU1"): 2.0},
        style_velocity={("D", "STY1"): 1.0},
        style_cover={("D", "STY1"): 100.0},
    )
    base.update(kw)
    return make_inputs(**base)


def move(**kw):
    base = dict(
        move_type=MoveType.S2S, from_location="D", to_location="R", sku_id="SKU1",
        style_id="STY1", qty=10, value_mrp=10_000, route_days=2,
        dispatch_date=date(2026, 11, 1), arrival_date=date(2026, 11, 3),
        requires_human_approval=False, reason="x", receiver_cover=1.0,
        velocity=2.0, donor_cover=100.0,
    )
    base.update(kw)
    return ApprovedMove(**base)


W2S = dict(
    move_type=MoveType.W2S, from_location="WH-KOL", qty=20, value_mrp=20_000,
    route_days=3, arrival_date=date(2026, 11, 4), donor_cover=None,
)


def test_clean():
    assert find_violations(inputs(), [move(), move(**W2S)]) == []


def has(rule, inp, moves):
    assert any(rule in m for m in find_violations(inp, moves)), rule


def test_r1():
    has("R1", inputs(), [move(qty=70, value_mrp=70_000)])


def test_r2():
    has("R2", inputs(stores=(store("D"), store("R", stock_capacity_units=30))),
        [move(), move(**W2S)])


def test_r3():
    has("R3", inputs(flagship=frozenset({("D", "STY1")})), [move()])


def test_r4():
    has("R4", inputs(positions=(pos("D", on_hand=100), pos("R", on_hand=5, in_transit=3))), [move()])


def test_r5():
    has("R5", inputs(style_cover={("D", "STY1"): 31.0}), [move()])
    has("R5", inputs(style_cover={}), [move()])


def test_r6():
    has("R6", inputs(), [move(value_mrp=1)])
    has("R6", inputs(), [move(requires_human_approval=True)])


def test_other():
    has("QTY", inputs(), [move(qty=0, value_mrp=0)])
    has("SUPPLY", inputs(), [move(**{**W2S, "qty": 60, "value_mrp": 60_000})])
    has("QUARANTINE", inputs(positions=(pos("D", on_hand=100, quarantined=True), pos("R", on_hand=5))), [move()])
    has("QUARANTINE", inputs(positions=(pos("D", on_hand=100), pos("R", on_hand=5, quarantined=True))), [move()])
    has("DISPATCH", inputs(), [move(dispatch_date=date(2026, 11, 2), arrival_date=date(2026, 11, 4))])
    has("ARRIVAL", inputs(), [move(arrival_date=date(2026, 11, 9))])


def test_no_src_import():
    tree = ast.parse((Path(__file__).parent / "independent_validator.py").read_text())
    for n in ast.walk(tree):
        names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""] if isinstance(n, ast.ImportFrom) else []
        assert not any(x.split(".")[0] == "src" for x in names)
