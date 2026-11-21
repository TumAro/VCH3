from __future__ import annotations

import pytest

from fakes import item, make_inputs, pos, store
from src.moves.config import DISPATCH_DATE  # noqa: F401
from src.moves.ledger import InventoryLedger
from src.moves.models import CandidateMove, HardRule, MoveType
from src.moves.validation import ConstraintValidationService


def build(donor_oh=100, cover=100.0, recv_cap=1000, recv_oh=0, recv_it=0,
          flagship=False, extra_recv=()):
    stores = [store("D", tier="A"), store("R", stock_capacity_units=recv_cap)]
    stores += [store(r, stock_capacity_units=recv_cap) for r in extra_recv]
    positions = [pos("D", "SKU1", donor_oh), pos("R", "SKU1", recv_oh, recv_it)]
    return make_inputs(
        stores=tuple(stores), items=(item(),), positions=tuple(positions),
        style_velocity={("D", "STY1"): 1.0},
        style_cover={("D", "STY1"): cover},
        flagship=frozenset({("D", "STY1")} if flagship else ()),
    )


def mv(qty, to="R"):
    return CandidateMove(MoveType.S2S, "D", to, "SKU1", "STY1", qty, 2)


def svc(inputs):
    return ConstraintValidationService(inputs), InventoryLedger.from_inputs(inputs)


@pytest.mark.parametrize("kw,rule", [
    (dict(donor_oh=35), HardRule.R1),
    (dict(recv_cap=10, recv_oh=10), HardRule.R2),
    (dict(flagship=True), HardRule.R3),
    (dict(recv_it=3), HardRule.R4),
    (dict(cover=30.0), HardRule.R5),
])
def test_rejected_log(kw, rule):
    s, led = svc(build(**kw))
    assert s.check(mv(10), led) == 0
    assert len(s.rejected) == 1
    r = s.rejected[0]
    assert r.rule_violated is rule
    assert (r.move_type, r.from_location, r.to_location, r.sku_id, r.qty) == (
        MoveType.S2S, "D", "R", "SKU1", 10)
    assert r.rejection_reason


def test_rejected_log_tie_lower_rule():
    s, led = svc(build(recv_cap=10, recv_oh=10, recv_it=2))  # R2 and R4 both 0
    assert s.check(mv(5), led) == 0
    assert [r.rule_violated for r in s.rejected] == [HardRule.R2]


def test_check_trim_not_logged_and_no_mutation():
    s, led = svc(build(donor_oh=40))  # R1 room 5
    assert s.check(mv(10), led) == 5
    assert s.rejected == []
    assert led.available("D", "SKU1") == 40 and led.capacity_load("R") == 0


def quarantined_donor():
    # quarantined donor stock: available 0, but R1..R5 all allow the move
    inp = build()
    return make_inputs(
        stores=inp.stores, items=inp.items,
        positions=(pos("D", "SKU1", 100, quarantined=True), pos("R", "SKU1")),
        style_velocity=inp.style_velocity, style_cover=inp.style_cover,
        min_display={("A", "Kurta Set"): 0})


def test_check_availability_zero_not_logged():
    inp = quarantined_donor()
    s, led = svc(inp)
    assert s.check(mv(3), led) == 0
    assert s.rejected == []


def test_batch_pass_unchanged_when_legal():
    inp = build()
    s = ConstraintValidationService(inp)
    moves = [mv(3), mv(4)]
    assert s.batch_pass(moves) == moves
    assert s.rejected == []


def test_batch_pass_r2_trim():
    s = ConstraintValidationService(build(recv_cap=10))
    out = s.batch_pass([mv(6), mv(6)])
    assert [m.qty for m in out] == [6, 4]
    assert [(r.qty, r.rule_violated) for r in s.rejected] == [(2, HardRule.R2)]


def test_batch_pass_r2_drop():
    s = ConstraintValidationService(build(recv_cap=6))
    out = s.batch_pass([mv(6), mv(6)])
    assert [m.qty for m in out] == [6]
    assert [(r.qty, r.rule_violated) for r in s.rejected] == [(6, HardRule.R2)]


def test_batch_pass_r1_trim_and_drop():
    s = ConstraintValidationService(build(donor_oh=40))  # room 5
    out = s.batch_pass([mv(3), mv(3)])
    assert [m.qty for m in out] == [3, 2]
    assert [(r.qty, r.rule_violated) for r in s.rejected] == [(1, HardRule.R1)]
    s = ConstraintValidationService(build(donor_oh=40))
    out = s.batch_pass([mv(5), mv(3)])
    assert [m.qty for m in out] == [5]
    assert [(r.qty, r.rule_violated) for r in s.rejected] == [(3, HardRule.R1)]


def test_batch_pass_trim_smaller_rule_wins():
    # R1 room 5, R5 room 1 (cover 31) -> R5 allows less
    s = ConstraintValidationService(build(donor_oh=40, cover=31.0))
    out = s.batch_pass([mv(4)])
    assert [m.qty for m in out] == [1]
    assert [(r.qty, r.rule_violated) for r in s.rejected] == [(3, HardRule.R5)]


def test_batch_pass_binary_drop():
    s = ConstraintValidationService(build(flagship=True))
    assert s.batch_pass([mv(2)]) == []
    assert [(r.qty, r.rule_violated) for r in s.rejected] == [(2, HardRule.R3)]


def test_batch_pass_availability_binding_raises():
    with pytest.raises(RuntimeError):
        ConstraintValidationService(quarantined_donor()).batch_pass([mv(5)])
