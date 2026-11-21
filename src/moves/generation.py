from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from src.moves.config import (
    DISPATCH_DATE,
    DONOR_SURPLUS_DAYS,
    S2S_CROSS_ZONE_DAYS,
    S2S_SAME_CITY_DAYS,
    S2S_SAME_ZONE_DAYS,
    W2S_DAYS_BY_ZONE,
    WH_LOCATION,
    display_category,
)
from src.moves.inputs import EngineInputs
from src.moves.ledger import InventoryLedger
from src.moves.models import CandidateMove, MoveType, UnfulfilledDeficit
from src.moves.validation import ConstraintValidationService


@dataclass(frozen=True)
class Deficit:
    store_id: str
    style_id: str
    T: int
    viable: bool


@dataclass(frozen=True)
class Need:
    store_id: str
    style_id: str
    sku_id: str
    T: int
    need: int
    viable: bool
    quarantined: bool
    revenue_loss: float


def _s2s_days(donor_id: str, receiver_id: str, inputs: EngineInputs) -> int:
    d, r = inputs.store(donor_id), inputs.store(receiver_id)
    if d.city == r.city:
        return S2S_SAME_CITY_DAYS
    if d.zone == r.zone:
        return S2S_SAME_ZONE_DAYS
    return S2S_CROSS_ZONE_DAYS


def route_days(source_location: str, receiver_store_id: str, inputs: EngineInputs) -> int:
    if source_location == WH_LOCATION:
        return W2S_DAYS_BY_ZONE[inputs.store(receiver_store_id).zone]
    return _s2s_days(source_location, receiver_store_id, inputs)


def arrival_date(days: int) -> date:
    return DISPATCH_DATE + timedelta(days=days)


def _style_category(style_id: str, inputs: EngineInputs) -> str:
    return display_category(inputs.item(inputs.skus_of_style(style_id)[0]).category)


def current_cover(
    store_id: str, style_id: str, ledger: InventoryLedger, inputs: EngineInputs
) -> Optional[float]:
    """Snapshot style cover minus days of stock already sent out in this batch (D-22)."""
    cover = inputs.cover(store_id, style_id)
    out = ledger.style_units_out(store_id, style_id)
    if cover is None or out == 0:
        return cover
    vel = inputs.style_vel(store_id, style_id)
    return cover - out / vel if vel > 0 else None


def is_eligible_donor(
    store_id: str, style_id: str, ledger: InventoryLedger, inputs: EngineInputs
) -> bool:
    cover = current_cover(store_id, style_id, ledger, inputs)
    if cover is None or cover <= DONOR_SURPLUS_DAYS:
        return False
    cat = _style_category(style_id, inputs)
    st = inputs.store(store_id)
    return ledger.category_on_hand(store_id, cat) > inputs.min_display[(st.tier, cat)]


def detect_deficits(inputs: EngineInputs, ledger: InventoryLedger) -> List[Deficit]:
    stores = sorted(inputs.stores, key=lambda s: s.store_id)
    styles = sorted(inputs._styles)
    out: List[Deficit] = []
    for r in stores:
        wh_days = W2S_DAYS_BY_ZONE[r.zone]  # unknown zone -> KeyError (D-23)
        for style in styles:
            cover = inputs.cover(r.store_id, style)
            if cover is None:
                continue
            skus = inputs.skus_of_style(style)
            viable = []
            if any(ledger.available(WH_LOCATION, k) > 0 for k in skus):
                viable.append(wh_days)
            for d in stores:
                if d.store_id != r.store_id and is_eligible_donor(d.store_id, style, ledger, inputs) \
                        and any(ledger.available(d.store_id, k) > 0 for k in skus):
                    viable.append(_s2s_days(d.store_id, r.store_id, inputs))
            if viable:
                t, ok = max(viable), True
            else:
                t, ok = max([wh_days] + [_s2s_days(d.store_id, r.store_id, inputs)
                                         for d in stores if d.store_id != r.store_id]), False
            if cover < t:
                out.append(Deficit(r.store_id, style, t, ok))
    return out


def size_needs(deficit: Deficit, inputs: EngineInputs) -> List[Need]:
    out: List[Need] = []
    for sku in sorted(inputs.skus_of_style(deficit.style_id)):
        p = inputs.position(deficit.store_id, sku)
        vel = inputs.sku_vel(deficit.store_id, sku)
        n = math.ceil(vel * deficit.T) - p.on_hand - p.in_transit
        if n > 0:
            out.append(Need(deficit.store_id, deficit.style_id, sku, deficit.T, n,
                            deficit.viable, p.quarantined, vel * inputs.item(sku).mrp))
    return out


def sort_needs(needs: List[Need]) -> List[Need]:
    return sorted(needs, key=lambda n: (-n.revenue_loss, n.sku_id, n.store_id))


@dataclass(frozen=True)
class GenerationResult:
    accepted: List[CandidateMove]
    unfulfilled: List[UnfulfilledDeficit]


class MoveGenerationService:
    def __init__(self, inputs: EngineInputs, validator: ConstraintValidationService) -> None:
        self._inputs = inputs
        self._validator = validator

    def generate(self, ledger: InventoryLedger) -> GenerationResult:
        inp = self._inputs
        needs = sort_needs([n for d in detect_deficits(inp, ledger) for n in size_needs(d, inp)])
        accepted: List[CandidateMove] = []
        unfulfilled: List[UnfulfilledDeficit] = []

        def unful(n: Need, left: int, reason: str) -> None:
            unfulfilled.append(UnfulfilledDeficit(
                n.store_id, n.style_id, n.sku_id, n.need, left, reason))

        residual = {}
        for n in needs:
            if not n.viable:
                unful(n, n.need, f"no viable route; threshold {n.T}d")
            elif n.quarantined:
                unful(n, n.need, "receiver position quarantined")
            else:
                residual[(n.store_id, n.sku_id)] = n.need
        live = [n for n in needs if (n.store_id, n.sku_id) in residual]

        # Phase A: warehouse to store
        for n in live:
            wh = ledger.available(WH_LOCATION, n.sku_id)
            if wh <= 0:
                continue
            cand = CandidateMove(MoveType.W2S, WH_LOCATION, n.store_id, n.sku_id, n.style_id,
                                 min(residual[(n.store_id, n.sku_id)], wh),
                                 route_days(WH_LOCATION, n.store_id, inp))
            allowed = self._validator.check(cand, ledger)
            if allowed > 0:
                move = cand.with_qty(allowed)
                ledger.apply(move)
                accepted.append(move)
                residual[(n.store_id, n.sku_id)] -= allowed

        # Phase B: store to store (eligibility on the running ledger, D-22)
        stores = sorted(s.store_id for s in inp.stores)
        for n in live:
            key = (n.store_id, n.sku_id)
            donors = sorted(
                (d for d in stores
                 if d != n.store_id and is_eligible_donor(d, n.style_id, ledger, inp)
                 and ledger.available(d, n.sku_id) > 0),
                key=lambda d: (route_days(d, n.store_id, inp),
                               -current_cover(d, n.style_id, ledger, inp), d))
            for d in donors:
                if residual[key] <= 0:
                    break
                # donor list is fixed per need; only the donor's own cover changes per move
                cand = CandidateMove(MoveType.S2S, d, n.store_id, n.sku_id, n.style_id,
                                     min(residual[key], ledger.available(d, n.sku_id)),
                                     route_days(d, n.store_id, inp))
                allowed = self._validator.check(cand, ledger)
                if allowed > 0:
                    move = cand.with_qty(allowed)
                    ledger.apply(move)
                    accepted.append(move)
                    residual[key] -= allowed

        for n in live:
            left = residual[(n.store_id, n.sku_id)]
            if left > 0:
                unful(n, left, f"unfilled {left} of {n.need} after W2S and S2S")
        return GenerationResult(accepted, unfulfilled)
