"""Independent re-check of the 6 hard rules on final approved moves.

Deliberate duplication: thresholds, dates, route days and the Safa/Mala/Stole map
are typed again here (from the spec) and nothing is imported from src, so this
check shares no code with the engine it checks.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

DISPATCH = date(2026, 11, 1)
SAFETY_DAYS = 30
APPROVAL_MRP = 100000
WH = "WH-KOL"
W2S_DAYS = {"East": 3, "North": 4, "South": 6}
ACC = "Accessories (Safa/Mala/Stole)"
ACC_SRC = ("Safa", "Mala", "Stole")


def _cat(c):
    return ACC if c in ACC_SRC else c


def find_violations(inputs, approved_moves):
    out = []
    stores = {s.store_id: s for s in inputs.stores}
    items = {i.sku_id: i for i in inputs.items}
    pos = {(p.location_id, p.sku_id): p for p in inputs.positions}

    def P(loc, sku):
        return pos.get((loc, sku))

    def oh(loc, sku):
        p = P(loc, sku)
        return p.on_hand if p else 0

    def label(m):
        return f"{m.move_type.value} {m.from_location}->{m.to_location} {m.sku_id} qty={m.qty}"

    sent = defaultdict(int)       # (source, sku)
    out_cat = defaultdict(int)    # (donor, display category), S2S only
    out_style = defaultdict(int)  # (donor, style), S2S only
    inbound = defaultdict(int)    # receiver
    for m in approved_moves:
        it = items[m.sku_id]
        sent[(m.from_location, m.sku_id)] += m.qty
        inbound[m.to_location] += m.qty
        is_s2s = m.move_type.value == "S2S"
        if is_s2s:
            out_cat[(m.from_location, _cat(it.category))] += m.qty
            out_style[(m.from_location, m.style_id)] += m.qty

        if m.qty <= 0:
            out.append(f"QTY: qty must be > 0: {label(m)}")
        for loc in (m.from_location, m.to_location):
            p = P(loc, m.sku_id)
            if p and p.quarantined:
                out.append(f"QUARANTINE: {loc} position used: {label(m)}")
        if (m.to_location, m.sku_id) in pos and pos[(m.to_location, m.sku_id)].in_transit != 0:
            out.append(f"R4: receiver has in-transit stock: {label(m)}")
        if is_s2s and (m.from_location, m.style_id) in inputs.flagship:
            out.append(f"R3: flagship-protected style moved: {label(m)}")
        if m.value_mrp != m.qty * it.mrp:
            out.append(f"R6: value_mrp {m.value_mrp} != qty x mrp {m.qty * it.mrp}: {label(m)}")
        if m.requires_human_approval != (m.qty * it.mrp > APPROVAL_MRP):
            out.append(f"R6: approval flag wrong: {label(m)}")
        if m.dispatch_date != DISPATCH:
            out.append(f"DISPATCH: {m.dispatch_date} != {DISPATCH}: {label(m)}")
        rcv = stores[m.to_location]
        if is_s2s:
            src = stores[m.from_location]
            days = 2 if src.city == rcv.city else 4 if src.zone == rcv.zone else 7
        else:
            days = W2S_DAYS[rcv.zone]
        if m.arrival_date != DISPATCH + timedelta(days=days):
            out.append(f"ARRIVAL: expected {DISPATCH + timedelta(days=days)}: {label(m)}")

    for (src, sku), n in sorted(sent.items()):
        p = P(src, sku)
        avail = 0 if (p is None or p.quarantined) else max(0, p.on_hand)
        if n > avail:
            out.append(f"SUPPLY: {src} {sku} sends {n} > available {avail}")

    for (d, cat), n in sorted(out_cat.items()):
        total = sum(max(0, p.on_hand) for p in inputs.positions
                    if p.location_id == d and _cat(items[p.sku_id].category) == cat)
        need = inputs.min_display[(stores[d].tier, cat)]
        if total - n < need:
            out.append(f"R1: donor {d} {cat} left {total - n} < min display {need}")

    for r, n in sorted(inbound.items()):
        if r == WH:
            continue
        load = sum(max(0, p.on_hand) + p.in_transit for p in inputs.positions if p.location_id == r)
        if load + n > stores[r].stock_capacity_units:
            out.append(f"R2: receiver {r} load {load}+{n} > capacity {stores[r].stock_capacity_units}")

    for (d, sty), n in sorted(out_style.items()):
        cover = inputs.style_cover.get((d, sty))
        vel = inputs.style_velocity.get((d, sty), 0.0)
        if cover is None or vel <= 0:
            out.append(f"R5: donor {d} style {sty} cover/velocity undefined")
        elif cover - n / vel < SAFETY_DAYS:
            out.append(f"R5: donor {d} style {sty} post-move cover {cover - n / vel:.1f} < {SAFETY_DAYS}")
    return out
