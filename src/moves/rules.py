from __future__ import annotations

import math
from typing import Protocol

from src.moves.config import (
    APPROVAL_THRESHOLD_MRP, DONOR_SAFETY_DAYS, display_category,
)
from src.moves.inputs import EngineInputs
from src.moves.ledger import InventoryLedger
from src.moves.models import CandidateMove, HardRule, MoveType


class HardRuleCheck(Protocol):
    rule: HardRule

    def max_allowed_qty(self, move: CandidateMove, ledger: InventoryLedger) -> int: ...

    def describe(self, move: CandidateMove, ledger: InventoryLedger) -> str: ...


def _clamp(room: int, qty: int) -> int:
    return max(0, min(qty, room))


class _Rule:
    def __init__(self, inputs: EngineInputs) -> None:
        self._in = inputs


class MinDisplayRule(_Rule):
    rule = HardRule.R1

    def _room(self, move, ledger):
        if move.move_type is not MoveType.S2S:
            return None
        tier = self._in.store(move.from_location).tier
        cat = display_category(self._in.item(move.sku_id).category)
        on_hand = ledger.category_on_hand(move.from_location, cat)
        return cat, on_hand, self._in.min_display[(tier, cat)]

    def max_allowed_qty(self, move, ledger):
        r = self._room(move, ledger)
        return move.qty if r is None else _clamp(r[1] - r[2], move.qty)

    def describe(self, move, ledger):
        _, on_hand, mn = self._room(move, ledger)
        cat = self._room(move, ledger)[0]
        return (f"{move.from_location} {cat} on-hand {on_hand} - {move.qty} "
                f"would fall below min display {mn}")


class CapacityRule(_Rule):
    rule = HardRule.R2

    def max_allowed_qty(self, move, ledger):
        cap = self._in.store(move.to_location).stock_capacity_units
        return _clamp(cap - ledger.capacity_load(move.to_location), move.qty)

    def describe(self, move, ledger):
        cap = self._in.store(move.to_location).stock_capacity_units
        load = ledger.capacity_load(move.to_location)
        return (f"{move.to_location} load {load} + {move.qty} "
                f"exceeds capacity {cap}")


class FlagshipRule(_Rule):
    rule = HardRule.R3

    def _blocked(self, move):
        return (move.move_type is MoveType.S2S
                and (move.from_location, move.style_id) in self._in.flagship)

    def max_allowed_qty(self, move, ledger):
        return 0 if self._blocked(move) else move.qty

    def describe(self, move, ledger):
        return (f"style {move.style_id} is flagship-protected at "
                f"{move.from_location}")


class InTransitRule(_Rule):
    rule = HardRule.R4

    def max_allowed_qty(self, move, ledger):
        return 0 if ledger.snapshot_in_transit(move.to_location, move.sku_id) else move.qty

    def describe(self, move, ledger):
        n = ledger.snapshot_in_transit(move.to_location, move.sku_id)
        return f"{move.to_location} already has {n} in transit for {move.sku_id}"


class DonorSafetyRule(_Rule):
    rule = HardRule.R5

    def max_allowed_qty(self, move, ledger):
        if move.move_type is not MoveType.S2S:
            return move.qty
        cover = self._in.cover(move.from_location, move.style_id)
        vel = self._in.style_vel(move.from_location, move.style_id)
        if cover is None or vel <= 0:
            return 0
        out = ledger.style_units_out(move.from_location, move.style_id)

        def ok(u):
            return cover - (out + u) / vel >= DONOR_SAFETY_DAYS

        u = max(0, min(move.qty, math.floor((cover - DONOR_SAFETY_DAYS) * vel - out)))
        while u > 0 and not ok(u):
            u -= 1
        while u < move.qty and ok(u + 1):
            u += 1
        return u

    def describe(self, move, ledger):
        cover = self._in.cover(move.from_location, move.style_id)
        vel = self._in.style_vel(move.from_location, move.style_id)
        if cover is None or vel <= 0:
            return (f"{move.from_location} style {move.style_id} cover undefined "
                    f"(cover={cover}, velocity={vel})")
        out = ledger.style_units_out(move.from_location, move.style_id)
        after = cover - (out + move.qty) / vel
        return (f"{move.from_location} style {move.style_id} cover would drop to "
                f"{after:.1f}d, below {DONOR_SAFETY_DAYS}d")


class ApprovalRule(_Rule):
    rule = HardRule.R6

    def max_allowed_qty(self, move, ledger):
        return move.qty

    def describe(self, move, ledger):
        return f"value above {APPROVAL_THRESHOLD_MRP} requires human approval"

    @staticmethod
    def requires_approval(qty: int, mrp: int) -> bool:
        return qty * mrp > APPROVAL_THRESHOLD_MRP


def default_rules(inputs: EngineInputs):
    return [c(inputs) for c in (MinDisplayRule, CapacityRule, FlagshipRule,
                                InTransitRule, DonorSafetyRule, ApprovalRule)]
