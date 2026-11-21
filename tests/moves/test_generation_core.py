from __future__ import annotations

from datetime import date

import pytest
from fakes import item, make_inputs, pos, store

from src.moves.generation import (
    Deficit,
    Need,
    arrival_date,
    detect_deficits,
    is_eligible_donor,
    route_days,
    size_needs,
    sort_needs,
)
from src.moves.ledger import InventoryLedger


def test_routes_dates():
    inp = make_inputs(stores=(
        store("E", "Kolkata", "East"), store("N", "Delhi", "North"), store("So", "Chennai", "South"),
        store("E2", "Kolkata", "East"), store("E3", "Patna", "East"), store("N2", "Mumbai", "North"),
    ))
    cases = [
        (("WH-KOL", "E"), date(2026, 11, 4)),
        (("WH-KOL", "N"), date(2026, 11, 5)),
        (("WH-KOL", "So"), date(2026, 11, 7)),
        (("E", "E2"), date(2026, 11, 3)),
        (("E", "E3"), date(2026, 11, 5)),
        (("E", "N"), date(2026, 11, 8)),
    ]
    for (src, dst), want in cases:
        assert arrival_date(route_days(src, dst, inp)) == want
    bad = make_inputs(stores=(store("X", zone="West"),))
    with pytest.raises(KeyError):
        route_days("WH-KOL", "X", bad)


def _fx(cover_r=3.0, donor_cover=50.0, donor_oh=100, wh=0, **kw):
    # R: East/Kolkata receiver; D: donor same city; style STY1 with two SKUs
    inp = make_inputs(
        stores=(store("R", "Kolkata", "East"), store("D", "Kolkata", "East")),
        items=(item("A", "STY1"), item("B", "STY1")),
        positions=(pos("WH-KOL", "A", wh), pos("D", "A", donor_oh), pos("R", "A", 1, 1)),
        sku_velocity={("R", "A"): 0.3, ("R", "B"): 1.0},
        style_velocity={("R", "STY1"): 1.3, ("D", "STY1"): 1.0},
        style_cover={("R", "STY1"): cover_r, ("D", "STY1"): donor_cover},
        **kw,
    )
    return inp, InventoryLedger.from_inputs(inp)


def test_deficit_detection():
    # only same-city donor viable: T = 2; cover 3 -> no deficit, 1 -> deficit
    inp, led = _fx(cover_r=3.0)
    assert detect_deficits(inp, led) == []
    inp, led = _fx(cover_r=1.0)
    assert detect_deficits(inp, led) == [Deficit("R", "STY1", 2, True)]
    # WH (East 3) plus same city donor (2): T = 3
    inp, led = _fx(cover_r=2.9, wh=5)
    assert detect_deficits(inp, led) == [Deficit("R", "STY1", 3, True)]
    # donor cover exactly 45 not eligible, WH empty -> no viable, longest route to R
    # (W2S East 3, same city 2) = 3, viable False
    inp, led = _fx(cover_r=2.0, donor_cover=45.0)
    assert not is_eligible_donor("D", "STY1", led, inp)
    assert detect_deficits(inp, led) == [Deficit("R", "STY1", 3, False)]
    # None cover: neither deficit nor donor
    inp, led = _fx(cover_r=None, donor_cover=None)
    assert not is_eligible_donor("D", "STY1", led, inp)
    assert detect_deficits(inp, led) == []
    # donor eligible but category on-hand not above min display (A tier, Kurta Set = 35)
    inp, led = _fx(cover_r=1.0, donor_oh=35)
    assert not is_eligible_donor("D", "STY1", led, inp)
    inp, led = _fx(cover_r=1.0, donor_oh=36)
    assert is_eligible_donor("D", "STY1", led, inp)


def test_no_viable_uses_longest_existing_route():
    inp = make_inputs(
        stores=(store("R", "Kolkata", "East"), store("F", "Mumbai", "North")),
        items=(item("A", "STY1"),),
        sku_velocity={("R", "A"): 1.0},
        style_cover={("R", "STY1"): 1.0},
    )
    led = InventoryLedger.from_inputs(inp)
    # W2S 3, cross-zone 7 exists (F); same city / same zone have no other store
    assert detect_deficits(inp, led) == [Deficit("R", "STY1", 7, False)]


def test_need_sizing():
    inp, _ = _fx()
    needs = size_needs(Deficit("R", "STY1", 4, True), inp)
    # A: ceil(0.3*4)=2 - 1 - 1 = 0 dropped; B: ceil(4.0)=4 - 0 - 0 = 4
    assert needs == [Need("R", "STY1", "B", 4, 4, True, False, 1.0 * 1000)]
    needs = size_needs(Deficit("R", "STY1", 4, True), make_inputs(
        stores=(store("R"),), items=(item("A", "STY1"),),
        sku_velocity={("R", "A"): 0.3}, positions=(pos("R", "A", quarantined=True),)))
    assert needs[0].need == 2 and needs[0].quarantined


def test_sort_needs():
    mk = lambda s, k, r: Need(s, "Y", k, 1, 1, True, False, r)
    ns = [mk("S2", "B", 5), mk("S1", "B", 5), mk("S1", "A", 5), mk("S9", "Z", 9)]
    assert [(n.sku_id, n.store_id) for n in sort_needs(ns)] == [
        ("Z", "S9"), ("A", "S1"), ("B", "S1"), ("B", "S2")]
