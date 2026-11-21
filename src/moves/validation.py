from __future__ import annotations

from typing import List, Optional, Sequence

from src.moves.inputs import EngineInputs
from src.moves.ledger import InventoryLedger
from src.moves.models import CandidateMove, RejectedMove
from src.moves.rules import HardRuleCheck, default_rules


class ConstraintValidationService:
    def __init__(self, inputs: EngineInputs,
                 rules: Optional[Sequence[HardRuleCheck]] = None) -> None:
        self._inputs = inputs
        self._rules = list(rules) if rules is not None else default_rules(inputs)
        self.rejected: List[RejectedMove] = []

    def _binding(self, move: CandidateMove, ledger: InventoryLedger):
        """(binding rule, its allowed qty); first rule wins ties (D-19, R1..R6 order)."""
        best = min(((r.max_allowed_qty(move, ledger), i) for i, r in enumerate(self._rules)))
        return self._rules[best[1]], best[0]

    def _log(self, move: CandidateMove, rule: HardRuleCheck, qty: int,
             ledger: InventoryLedger) -> None:
        self.rejected.append(RejectedMove(
            move.move_type, move.from_location, move.to_location, move.sku_id,
            qty, rule.rule, rule.describe(move, ledger)))

    def check(self, candidate: CandidateMove, ledger: InventoryLedger) -> int:
        rule, rule_qty = self._binding(candidate, ledger)
        if rule_qty == 0:
            self._log(candidate, rule, candidate.qty, ledger)
            return 0
        return min(ledger.available(candidate.from_location, candidate.sku_id), rule_qty)

    def batch_pass(self, moves: Sequence[CandidateMove]) -> List[CandidateMove]:
        ledger = InventoryLedger.from_inputs(self._inputs)
        kept: List[CandidateMove] = []
        for m in moves:
            rule, rule_qty = self._binding(m, ledger)
            if ledger.available(m.from_location, m.sku_id) < rule_qty:
                raise RuntimeError(f"source availability binds batch move {m}")
            if rule_qty < m.qty:
                self._log(m, rule, m.qty - rule_qty, ledger)
            if rule_qty > 0:
                m = m.with_qty(rule_qty)
                ledger.apply(m)
                kept.append(m)
        return kept
