from __future__ import annotations

import re
from datetime import date

from fakes import item, make_inputs, pos, store
from independent_validator import find_violations

from src.moves.engine import MoveEngine, finalize
from src.moves.models import CandidateMove, MoveType

PAT = re.compile(
    r"Send (\d+): (\S+) has (\S+)d cover at (\S+), sells (\S+)/d; "
    r"donor (\S+) retains (?:n/a cover|(\S+)d cover)$"
)


def inputs(wh_velocity=None):
    return make_inputs(
        stores=(store("R", "Kolkata", "East"), store("D", "Kolkata", "East")),
        items=(item("A", mrp=20000), item("B", mrp=1000)),
        positions=(
            pos("WH-KOL", "A", 6), pos("WH-KOL", "B", 20),
            pos("R", "A", 2), pos("D", "A", 100),
        ),
        sku_velocity={("R", "A"): 4.0, ("R", "B"): 2.0},
        style_velocity={("R", "STY1"): 6.0, ("D", "STY1"): 1.0},
        style_cover={("R", "STY1"): 1.0, ("D", "STY1"): 100.0},
        wh_velocity=wh_velocity,
    )


def test_end_to_end_w2s_and_s2s():
    res = MoveEngine().run(inputs())
    by = {(m.move_type, m.sku_id): m for m in res.approved_moves}
    assert set(by) == {(MoveType.W2S, "A"), (MoveType.S2S, "A"), (MoveType.W2S, "B")}
    w, s = by[(MoveType.W2S, "A")], by[(MoveType.S2S, "A")]
    assert (w.qty, w.value_mrp, w.requires_human_approval) == (6, 120000, True)
    assert (w.route_days, w.dispatch_date, w.arrival_date) == (3, date(2026, 11, 1), date(2026, 11, 4))
    assert (s.from_location, s.qty, s.value_mrp, s.requires_human_approval) == ("D", 4, 80000, False)
    assert (s.route_days, s.arrival_date) == (2, date(2026, 11, 3))
    assert s.donor_cover == 96.0 and s.receiver_cover == 1.0 and s.velocity == 4.0
    assert find_violations(inputs(), res.approved_moves) == []
    assert res.rejected_moves == () and res.unfulfilled_deficits == ()


def test_reason_reconciles():
    for wh_vel in (None, {"A": 3.0, "B": 2.0}):
        inp = inputs(wh_vel)
        res = MoveEngine().run(inp)
        assert res.approved_moves
        for m in res.approved_moves:
            g = PAT.match(m.reason)
            assert g, m.reason
            qty, sku, rc, rcv, vel, donor, dc = g.groups()
            assert int(qty) == m.qty and sku == m.sku_id and rcv == m.to_location
            assert rc == f"{inp.cover(m.to_location, m.style_id):.1f}"
            assert vel == f"{inp.sku_vel(m.to_location, m.sku_id):.1f}"
            assert donor == m.from_location
            if m.move_type is MoveType.S2S:
                out = sum(x.qty for x in res.approved_moves
                          if x.from_location == donor and x.style_id == m.style_id)
                assert dc == f"{inp.cover(donor, m.style_id) - out / inp.style_vel(donor, m.style_id):.1f}"
            elif wh_vel is None:
                assert dc is None and m.reason.endswith("retains n/a cover")
            else:
                left = inp.position("WH-KOL", m.sku_id).on_hand - m.qty
                assert dc == f"{left / wh_vel[m.sku_id]:.1f}"
                assert m.donor_cover == left / wh_vel[m.sku_id]


def test_finalize_trimmed_recomputes_value_and_flag():
    inp = inputs()
    full = CandidateMove(MoveType.W2S, "WH-KOL", "R", "A", "STY1", 6, 3)
    (a,) = finalize(inp, [full])
    assert a.requires_human_approval and a.value_mrp == 120000
    (a,) = finalize(inp, [full.with_qty(5)])  # 100000 is not above the threshold
    assert a.value_mrp == 100000 and not a.requires_human_approval
    assert "Send 5:" in a.reason
