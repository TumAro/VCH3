from __future__ import annotations

from fakes import item, make_inputs, pos, store
from src.moves.ledger import InventoryLedger
from src.moves.models import CandidateMove, HardRule, MoveType
from src.moves.rules import (
    ApprovalRule, CapacityRule, DonorSafetyRule, FlagshipRule,
    InTransitRule, MinDisplayRule, default_rules,
)


def s2s(qty, sku="SKU1", style="STY1", src="D", dst="R"):
    return CandidateMove(MoveType.S2S, src, dst, sku, style, qty, 2)


def w2s(qty, sku="SKU1", style="STY1"):
    return CandidateMove(MoveType.W2S, "WH-KOL", "R", sku, style, qty, 3)


def build(**kw):
    base = dict(
        stores=(store("D", tier="B"), store("R", stock_capacity_units=100)),
        items=(item(),),
        positions=(pos("D", on_hand=50),),
    )
    base.update(kw)
    inp = make_inputs(**base)
    return inp, InventoryLedger.from_inputs(inp)


def test_default_rules_order():
    inp, _ = build()
    assert [r.rule for r in default_rules(inp)] == list(HardRule)


def test_rule_min_display_boundary():  # B / Kurta Set min = 25
    inp, led = build()
    r = MinDisplayRule(inp)
    assert r.max_allowed_qty(s2s(25), led) == 25
    assert r.max_allowed_qty(s2s(26), led) == 25
    assert "25" in r.describe(s2s(26), led)


def test_rule_min_display_blocks_when_at_min():
    inp, led = build(positions=(pos("D", on_hand=25),))
    assert MinDisplayRule(inp).max_allowed_qty(s2s(1), led) == 0


def test_rule_min_display_accessories_aggregation():
    inp, led = build(
        items=(item("A1", "ST1", "Safa"), item("A2", "ST2", "Mala")),
        positions=(pos("D", "A1", 3), pos("D", "A2", 3)),  # B min 4 -> room 2
    )
    r = MinDisplayRule(inp)
    assert r.max_allowed_qty(s2s(5, "A1", "ST1"), led) == 2


def test_rule_min_display_on_hand_only():
    inp, led = build(positions=(pos("D", on_hand=26, in_transit=100),))
    assert MinDisplayRule(inp).max_allowed_qty(s2s(5), led) == 1


def test_rule_min_display_w2s_n_a():
    inp, led = build()
    assert MinDisplayRule(inp).max_allowed_qty(w2s(7), led) == 7


def test_rule_capacity_boundary():
    inp, led = build(positions=(pos("D", on_hand=50), pos("R", on_hand=90)))
    r = CapacityRule(inp)
    assert r.max_allowed_qty(s2s(10), led) == 10
    assert r.max_allowed_qty(s2s(11), led) == 10
    assert r.max_allowed_qty(w2s(11), led) == 10
    assert "100" in r.describe(s2s(11), led)


def test_rule_capacity_full_blocks():
    inp, led = build(positions=(pos("D", on_hand=50), pos("R", on_hand=100)))
    assert CapacityRule(inp).max_allowed_qty(s2s(1), led) == 0


def test_rule_capacity_no_outbound_credit():
    inp, led = build(positions=(pos("D", on_hand=50), pos("R", on_hand=100)))
    # R sends out 30 elsewhere; its load must not drop
    led.apply(CandidateMove(MoveType.S2S, "R", "D", "SKU1", "STY1", 30, 2))
    assert CapacityRule(inp).max_allowed_qty(s2s(5), led) == 0


def test_rule_flagship():
    inp, led = build(
        items=(item("SKU1", "STY1"), item("SKU2", "STY1"), item("SKU3", "STY2")),
        positions=(pos("D", "SKU1", 50), pos("D", "SKU2", 50), pos("D", "SKU3", 50)),
        flagship=frozenset({("D", "STY1")}),
    )
    r = FlagshipRule(inp)
    assert r.max_allowed_qty(s2s(1, "SKU1", "STY1"), led) == 0
    assert r.max_allowed_qty(s2s(40, "SKU2", "STY1"), led) == 0
    assert r.max_allowed_qty(s2s(5, "SKU3", "STY2"), led) == 5
    assert r.max_allowed_qty(w2s(5, "SKU1", "STY1"), led) == 5
    assert "D" in r.describe(s2s(1), led)


def test_rule_in_transit():
    inp, led = build(positions=(pos("D", on_hand=50), pos("R", in_transit=1)))
    r = InTransitRule(inp)
    assert r.max_allowed_qty(s2s(5), led) == 0
    assert r.max_allowed_qty(w2s(5), led) == 0
    inp, led = build(positions=(pos("D", on_hand=50), pos("R", in_transit=0)))
    assert InTransitRule(inp).max_allowed_qty(s2s(5), led) == 5


def test_rule_in_transit_ignores_accepted_inbound():
    inp, led = build()
    led.apply(s2s(3))
    assert InTransitRule(inp).max_allowed_qty(s2s(3), led) == 3


def test_rule_donor_safety_exact_30():
    inp, led = build(style_velocity={("D", "STY1"): 2.0}, style_cover={("D", "STY1"): 40.0})
    r = DonorSafetyRule(inp)  # 40 - u/2 >= 30 -> u <= 20
    assert r.max_allowed_qty(s2s(20), led) == 20
    assert r.max_allowed_qty(s2s(21), led) == 20
    assert r.max_allowed_qty(s2s(10), led) == 10


def test_rule_donor_safety_counts_prior_outbound():
    inp, led = build(style_velocity={("D", "STY1"): 2.0}, style_cover={("D", "STY1"): 40.0})
    led.apply(s2s(15))
    assert DonorSafetyRule(inp).max_allowed_qty(s2s(10), led) == 5


def test_rule_donor_safety_none_and_zero_velocity_block():
    inp, led = build(style_velocity={("D", "STY1"): 2.0})  # cover missing -> None
    assert DonorSafetyRule(inp).max_allowed_qty(s2s(1), led) == 0
    inp, led = build(style_velocity={("D", "STY1"): 0.0}, style_cover={("D", "STY1"): 99.0})
    assert DonorSafetyRule(inp).max_allowed_qty(s2s(1), led) == 0


def test_rule_donor_safety_float_boundary():
    inp, led = build(style_velocity={("D", "STY1"): 0.3}, style_cover={("D", "STY1"): 31.0})
    r = DonorSafetyRule(inp)
    q = r.max_allowed_qty(s2s(100), led)
    assert 31.0 - q / 0.3 >= 30 and not 31.0 - (q + 1) / 0.3 >= 30


def test_rule_donor_safety_w2s_n_a():
    inp, led = build()
    assert DonorSafetyRule(inp).max_allowed_qty(w2s(9), led) == 9


def test_rule_approval():
    r = ApprovalRule(build()[0])
    assert r.requires_approval(100, 1000) is False  # == 100000
    assert r.requires_approval(100, 1001) is True
    assert r.requires_approval(1, 100001) is True
    assert r.max_allowed_qty(s2s(500), build()[1]) == 500
