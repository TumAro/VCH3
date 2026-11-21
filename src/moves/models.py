from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum
from typing import Optional, Tuple


class MoveType(str, Enum):
    W2S = "W2S"
    S2S = "S2S"


class HardRule(str, Enum):
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"
    R5 = "R5"
    R6 = "R6"


@dataclass(frozen=True)
class CandidateMove:
    move_type: MoveType
    from_location: str
    to_location: str
    sku_id: str
    style_id: str
    qty: int
    route_days: int

    def with_qty(self, qty: int) -> "CandidateMove":
        return replace(self, qty=qty)


@dataclass(frozen=True)
class ApprovedMove:
    move_type: MoveType
    from_location: str
    to_location: str
    sku_id: str
    style_id: str
    qty: int
    value_mrp: int
    route_days: int
    dispatch_date: date
    arrival_date: date
    requires_human_approval: bool
    reason: str
    receiver_cover: float
    velocity: float
    donor_cover: Optional[float]


@dataclass(frozen=True)
class RejectedMove:
    move_type: MoveType
    from_location: str
    to_location: str
    sku_id: str
    qty: int
    rule_violated: HardRule
    rejection_reason: str


@dataclass(frozen=True)
class UnfulfilledDeficit:
    store_id: str
    style_id: str
    sku_id: str
    needed_qty: int
    unfilled_qty: int
    reason: str


@dataclass(frozen=True)
class EngineResult:
    approved_moves: Tuple[ApprovedMove, ...]
    rejected_moves: Tuple[RejectedMove, ...]
    unfulfilled_deficits: Tuple[UnfulfilledDeficit, ...]
