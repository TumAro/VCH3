from __future__ import annotations

from typing import Sequence, Tuple

from src.moves.config import DISPATCH_DATE, WH_LOCATION
from src.moves.explain import ExplanationService
from src.moves.generation import MoveGenerationService, arrival_date
from src.moves.inputs import EngineInputs
from src.moves.ledger import InventoryLedger
from src.moves.models import ApprovedMove, CandidateMove, EngineResult, MoveType
from src.moves.rules import ApprovalRule
from src.moves.validation import ConstraintValidationService


def finalize(inputs: EngineInputs, moves: Sequence[CandidateMove]) -> Tuple[ApprovedMove, ...]:
    ledger = InventoryLedger.from_inputs(inputs)
    explain = ExplanationService()
    out = []
    for m in moves:
        ledger.apply(m)
        mrp = inputs.item(m.sku_id).mrp
        rcv_cover = inputs.cover(m.to_location, m.style_id)
        vel = inputs.sku_vel(m.to_location, m.sku_id)
        if m.move_type is MoveType.S2S:
            cover = inputs.cover(m.from_location, m.style_id)
            sv = inputs.style_vel(m.from_location, m.style_id)
            donor_cover = cover - ledger.style_units_out(m.from_location, m.style_id) / sv
        else:  # D-16: no warehouse velocity means cover is undefined
            wv = (inputs.wh_velocity or {}).get(m.sku_id, 0)
            donor_cover = ledger.available(WH_LOCATION, m.sku_id) / wv if wv else None
        out.append(ApprovedMove(
            m.move_type, m.from_location, m.to_location, m.sku_id, m.style_id, m.qty,
            m.qty * mrp, m.route_days, DISPATCH_DATE, arrival_date(m.route_days),
            ApprovalRule.requires_approval(m.qty, mrp),
            explain.reason(m.qty, m.sku_id, m.to_location, rcv_cover, vel,
                           m.from_location, donor_cover),
            rcv_cover, vel, donor_cover))
    return tuple(out)


class MoveEngine:
    def run(self, inputs: EngineInputs) -> EngineResult:
        ledger = InventoryLedger.from_inputs(inputs)
        validator = ConstraintValidationService(inputs)
        gen = MoveGenerationService(inputs, validator).generate(ledger)
        final = validator.batch_pass(gen.accepted)
        return EngineResult(finalize(inputs, final), tuple(validator.rejected),
                            tuple(gen.unfulfilled))
