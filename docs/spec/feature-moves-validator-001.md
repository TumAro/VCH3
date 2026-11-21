# Track 3: Move Generation & Hard Constraints Engine
- Status: Implemented
- Created: 2026-11-21

## 1. Spec

### Goal & context
Build the core move generation and constraint validation engine for the Daily Stock Move Recommender. The engine identifies inventory imbalances, proposes Warehouse-to-Store allocations and Store-to-Store rebalancing moves, checks every move against 6 non-negotiable retail constraints individually and cumulatively, flags high-value moves ($> ₹1,00,000\text{ MRP}$), and generates deterministic, data-backed 1-line reason strings.

### Scope

**In Scope:**
- Proposing Warehouse-to-Store moves: allocating available `WH-KOL` on-hand inventory to stores with cover below lead time, prioritized by highest sales loss avoided ($\text{velocity} \times \text{MRP}$).
- Proposing Store-to-Store moves: matching surplus donor stores ($> 45\text{ days}$ cover) with deficit receiver stores ($< \text{lead time}$) within route lead times.
- Calculating dispatch and arrival dates using the route lead-times matrix from `lead_times`:
  - WH-KOL to East: 3 days, North: 4 days, South: 6 days.
  - Store to store: same city 2 days, same zone 4 days, cross zone 7 days.
- Centralized validation of the 6 non-negotiable hard rules:
  1. *Minimum display*: donor store retains $\ge \text{min\_display}$ units for its tier and category (with Safa, Mala, and Stole aggregated under Accessories).
  2. *Capacity ceiling*: receiver on-hand $+$ in-transit $+$ cumulative proposed moves $\le \text{stock\_capacity\_units}$.
  3. *Flagship protection*: zero outbound moves for top-20 styles at S++ stores listed in `flagship_protected.csv`.
  4. *In-transit deduplication*: never propose a move to a store that already has the SKU in transit.
  5. *Donor safety*: store-to-store move must leave donor with $\ge 30\text{ days}$ cover for that style.
  6. *High-value approval gate*: moves with value $> ₹1,00,000\text{ MRP}$ ($\text{qty} \times \text{MRP}$) are flagged with `requires_human_approval = True`.
- Cumulative batch validation pass: re-evaluates the combined impact of all approved moves to prevent multi-move breaches of capacity or minimum display.
- Generating deterministic, data-backed 1-line reason strings per move from computed attributes.
- Recording rejected candidate moves in a structured audit log detailing the broken rule.

**Explicitly Out of Scope:**
- CSV file loading and repository management (Track 1).
- Velocity and cover calculation (Track 2).
- Dashboard presentation, API routes, and file export (Track 4).
- Transport cost optimization.

### Requirements
- **REQ-1:** Generate Warehouse-to-Store replenishment moves:
  - Allocate only from `WH-KOL` on-hand stock.
  - Target stores with cover $<$ route lead time.
  - Rank and allocate in descending order of expected revenue loss ($\text{daily velocity} \times \text{MRP}$).
- **REQ-2:** Generate Store-to-Store rebalancing moves:
  - Eligible donors: stores with style cover $> 45\text{ days}$ and on-hand $>$ minimum display.
  - Eligible receivers: stores with style cover $<$ route lead time.
  - Prioritize shortest transit lead time routes (same city first, then same zone, then cross zone).
- **REQ-3:** Assign dispatch date (`2026-11-01`) and arrival date strictly by adding route transit days from `lead_times`.
- **REQ-4:** Enforce the 6 hard rules on every candidate move:
  - Rule 1: Donor remaining category stock $\ge \text{min\_display}$ for store tier.
  - Rule 2: Receiver post-move total units $\le \text{stock\_capacity\_units}$.
  - Rule 3: Zero outbound moves of protected styles from S++ stores for all sizes of the style.
  - Rule 4: Receiver existing `in_transit == 0` for that SKU.
  - Rule 5: Donor style cover post-move $\ge 30\text{ days}$.
  - Rule 6: If $\text{qty} \times \text{MRP} > ₹1,00,000$, set `requires_human_approval = True`.
- **REQ-5:** Execute a cumulative batch validation pass:
  - Track simulated post-move inventory across all stores.
  - Drop or trim any candidate move that cumulatively breaches store capacity or minimum display.
- **REQ-6:** Generate a deterministic 1-line reason string for every approved move:
  - Format: `"Send {qty}: {sku} has {receiver_cover}d cover at {receiver}, sells {velocity}/d; donor {donor} retains {donor_cover}d cover"`.
- **REQ-7:** Record every rejected candidate move in a `RejectedMoveLog` with: `move_type`, `from_location`, `to_location`, `sku_id`, `qty`, `rule_violated`, and `rejection_reason`.

### Acceptance criteria
- **AC-1 (REQ-4):** Zero rule violations exist in the final approved move list across all 6 constraints (verified by an independent validator).
- **AC-2 (REQ-4, Rule 3):** No style listed in `flagship_protected.csv` is ever transferred out of an S++ store.
- **AC-3 (REQ-4, Rule 6):** 100% of moves with value $> ₹1,00,000\text{ MRP}$ have `requires_human_approval == True`.
- **AC-4 (REQ-5):** No receiving store exceeds physical `stock_capacity_units` after accounting for all proposed inbound moves combined.
- **AC-5 (REQ-6):** Every approved move has a valid 1-line reason string where numerical values reconcile with underlying store and SKU metrics.
- **AC-6 (REQ-7):** Rejected moves are captured in the rejected moves log with the exact violated rule.

### Edge cases & failure modes
- **Warehouse Stock Exhaustion:** If warehouse supply is depleted, allocation stops cleanly and leaves deficit stores eligible for store-to-store balancing.
- **Tied Priorities:** Deterministic tie-breaking by revenue loss $\to$ SKU ID $\to$ store ID ensures identical output across runs.
- **Zero Viable Donors:** If no donor satisfies Rule 1 and Rule 5, the deficit is logged as unfulfilled without generating an invalid move.

### Assumptions & open questions
- As-of date is `2026-10-31`, dispatch date is `2026-11-01`.
- Categories Safa, Mala, and Stole map to `Accessories (Safa/Mala/Stole)` for `min_display`.

## 2. Plan

### 2.1 Grounding
- Track 1 code now exists (`src/domain/`, `src/infrastructure/`, `tests/test_ingestion.py`); Track 3 does not import it (D-9). There is no `src/moves/`, no `pyproject.toml` and no requirements file, and pytest is not installed for the system Python 3.10. This plan is grounded in docs, data and the user decisions in 2.10.
- Stack and names come from `docs/architecture.md`: Python, pipeline entry `python -m src.cli`, services `MoveGenerationService`, `ConstraintValidationService`, `ExplanationService` (sections 2, 3, 5.3, 5.4). Track 1 repositories (`IStoreRepository`, `IStockRepository`, `IRulesRepository`) are not consumed directly; Track 3 owns its input contract (2.3, D-9).
- Design rules come from `AGENTS.md`: Repository Pattern, SOLID (SRP and OCP non-negotiable), DRY, services tested against fakes.
- Data facts come from `data/csv/` and `docs/problemStatement.md`:
  - `stores.csv` gives `city`, `zone`, `tier`, `stock_capacity_units` (routing, Rule 1, Rule 2, Rule 3).
  - `items.csv` gives `style_id`, `category`, `mrp` (Rule 1 category, Rule 6 value, REQ-1 ranking).
  - `stock_snapshot.csv` gives `on_hand`, `in_transit` per `location_id` (store or `WH-KOL`) and SKU.
  - `min_display.csv` is keyed by tier and display category; `flagship_protected.csv` by `store_id` and `style_id` (80 rows, 4 S++ stores).
  - `lead_times.csv` holds 6 routes as free-text labels; their day values are mirrored as constants in `src/moves/config.py` (D-12).

### 2.2 Architecture and modules
Layout `src/moves/` and `tests/moves/` (D-8). One package, one job per file. Engine uses the Python stdlib only (`dataclasses`, `datetime`, `enum`, `math`); pytest is a dev-only dependency (D-8), declared in a new `requirements-dev.txt` (no project dependency file exists yet).

| File | Responsibility | REQ |
|---|---|---|
| `src/moves/config.py` | Frozen constants: donor surplus 45 d, donor safety 30 d, approval threshold ₹1,00,000, as-of `2026-10-31`, dispatch `2026-11-01`, route lead times (WH-KOL: East 3, North 4, South 6; S2S: same city 2, same zone 4, cross zone 7), category map Safa/Mala/Stole to `"Accessories (Safa/Mala/Stole)"`. Moves to a shared config once Track 1 defines one (D-12). | REQ-2, REQ-3, R1, R5, R6 |
| `src/moves/inputs.py` | Track 3's own input contract: frozen dataclasses for stores, items, positions (with `quarantined` flag), style cover and velocities, min display, flagship set (2.3, D-9). Track 1/2 write adapters to it later; tests build it directly. | all |
| `src/moves/models.py` | Value types: `MoveType` (W2S, S2S), `HardRule` enum (R1..R6), `CandidateMove` (proposed move before finalization), `ApprovedMove`, `RejectedMove` (`RejectedMoveLog` entry), `UnfulfilledDeficit`, `EngineResult`. | REQ-3, REQ-6, REQ-7 |
| `src/moves/ledger.py` | `InventoryLedger`: simulated per-location SKU on-hand, per-store category on-hand (display category), per-store capacity load (on-hand + in-transit + accepted inbound, no outbound credit, D-11), per-store style units moved out (for post-move style cover). Built from inputs, mutated by `apply(move)`. | REQ-5 |
| `src/moves/rules.py` | One class per hard rule behind a small `HardRuleCheck` protocol: `max_allowed_qty(move, ledger) -> int` (0 = blocked). Six implementations, so the protocol is justified (OCP). Rule 6 never blocks; it only sets the flag. | REQ-4 |
| `src/moves/generation.py` | `MoveGenerationService`: style-level deficit detection, per-SKU need sizing, W2S allocation, S2S donor matching, route resolution, dates. | REQ-1, REQ-2, REQ-3 |
| `src/moves/validation.py` | `ConstraintValidationService`: per-candidate rule check and cumulative batch pass (replay, trim, drop). Writes `RejectedMoveLog`. | REQ-4, REQ-5, REQ-7 |
| `src/moves/explain.py` | `ExplanationService`: fills the REQ-6 template from the values the decision used (D-6). | REQ-6 |
| `src/moves/engine.py` | `MoveEngine.run(inputs) -> EngineResult`: orchestrates generation, validation, batch pass, explanation. The only entry point Track 4 calls. | all |

### 2.3 Input contract (owned by Track 3, D-9)
One frozen `EngineInputs` dataclass, built by tests from fakes and later by Track 1/2 adapters. No file I/O, no Track 1/2 imports.

| Field | Content | Used by |
|---|---|---|
| `stores` | `store_id`, `city`, `zone`, `tier`, `stock_capacity_units` | routing, R1, R2, R3 |
| `items` | `sku_id`, `style_id`, `category`, `mrp` (packaging already excluded) | R1, R6, REQ-1 rank |
| `positions` | per `location_id` x `sku_id`: `on_hand`, `in_transit`, `quarantined: bool` | ledger, R2, R4, WH supply |
| `sku_velocity` | daily velocity per store x SKU | need sizing, REQ-1 rank, reason |
| `style_velocity`, `style_cover` | per store x style (cover in days, `None` when undefined) | deficit detection, donor eligibility, R5 |
| `wh_velocity` | optional daily velocity per SKU for `WH-KOL` cover in the reason; absent means `"n/a"`; no warehouse velocity is ever derived (D-16) | reason |
| `min_display` | tier x display category to min units | R1, donor eligibility |
| `flagship` | set of (`store_id`, `style_id`) | R3 |

Thresholds, dates, lead times and the category map come from `config.py`, not inputs. Absent keys and invalid positions follow the conventions in 3.3 (D-23).

Derived values (engine-side, no Track 2 code):
- Post-move donor style cover = `style_cover - units_moved_out_of_style / style_velocity`. This only assumes cover is linear in stock, so it is independent of Track 2's stock basis.
- Quarantined positions are never a source or receiver of a candidate move (D-9, D-15). A SKU with need > 0 whose receiver position is quarantined is reported as an `UnfulfilledDeficit` with a quarantine reason (D-21). They still count in category on-hand (R1) and capacity load (R2). Values are used as-is, except negative on-hand is clamped to 0 for R1/R2 counting only (D-15).

### 2.4 Outputs
`EngineResult` returned to Track 4 (no file I/O here):
- `approved_moves`: `ApprovedMove` with `move_type`, `from_location`, `to_location`, `sku_id`, `style_id`, `qty`, `value_mrp` (`qty x mrp`), `route_days`, `dispatch_date`, `arrival_date`, `requires_human_approval`, `reason`, plus the raw values behind the reason (`receiver_cover`, `velocity`, `donor_cover` or `None`) for AC-5 checks.
- `rejected_moves`: `RejectedMoveLog` entries with exactly the REQ-7 fields, for rejected candidates, batch-pass drops and batch-pass trims (D-4, D-11).
- `unfulfilled_deficits`: separate `UnfulfilledDeficit` list (`store_id`, `style_id`, `sku_id`, `needed_qty`, `unfilled_qty`, `reason`), never mixed into `RejectedMoveLog` (D-4).

### 2.5 Pipeline order
1. **Build ledger** from positions (snapshot state, as-of `2026-10-31`).
2. **Detect deficits (style level, D-2, D-5, D-13, D-14)**: only store x style pairs with a defined `style_cover` are considered; `None` is never a deficit (D-14). A route into the store is viable if its source holds stock (D-13): the W2S route if `WH-KOL` has non-quarantined on-hand > 0 for any SKU of the style; an S2S route type (same city, same zone, cross zone) if at least one eligible donor (step 5 filters) of that route type holds non-quarantined on-hand > 0 of the style. `T` = max lead time over viable routes. The store x style is a deficit if `style_cover < T`. If no route is viable, `T` = the longest lead time of any route to that store (its W2S zone route and every S2S route type for which another store exists), and a deficit against that `T` is reported as `UnfulfilledDeficit` without candidates (D-13). Computed once from the snapshot.
3. **Size need per SKU (D-1, D-13)**: for each SKU of a deficit style at that store, `need = ceil(sku_velocity x T) - on_hand - in_transit` (snapshot values as-is, D-15). `need <= 0` means no candidate. The lead time used here is the same `T` (D-13). A need > 0 whose receiver position is quarantined gets no candidate and is reported as an `UnfulfilledDeficit` with reason `receiver position quarantined` (D-21).
4. **Phase A, W2S (REQ-1, D-3)**: sort needs by tie-break key (2.7). Supply = `WH-KOL` non-quarantined on-hand only; `warehouse_inbound` is ignored. `qty = min(need, WH remaining, R2 room)`; R4 and R2 can block (logged). WH remaining 0 is not a rejection: the need passes to Phase B unchanged (edge case "Warehouse Stock Exhaustion"). Accepted moves are applied to the running ledger.
5. **Phase B, S2S (REQ-2, D-2)**: for each remaining need (same sort), eligible donors are stores with `style_cover > 45` (`None` is never a donor, D-14) and category on-hand `> min_display` (D-5), non-quarantined SKU position. Both eligibility tests use the running ledger (current style cover `style_cover - style_units_out / style_velocity` and current category on-hand after earlier accepted moves); the snapshot is used only for viable-route detection in step 2 (D-22). Order donors by route days asc (same city, same zone, cross zone), then current style cover desc, then `store_id` asc (D-10). For each donor in order, `qty = min(residual need, donor SKU on-hand, R1 room, R2 room, R5 room)`; R3 and R4 block. Continue to the next donor until the need is met or donors run out. A residual need > 0 after Phase B becomes an `UnfulfilledDeficit` (D-4). One batch may send the same SKU to the same receiver more than once (W2S partial plus S2S top-up, or several donors), with the residual need reduced after each accepted move (D-17).
6. **Per-candidate validation (REQ-4)**: a candidate is a (need, source) pair. Caps above are sizing, not rejection. A candidate whose allowed qty is 0 because of a rule produces one `RejectedMove` with that rule code and a data-backed `rejection_reason`; it is not applied. When several rules block or limit the same candidate, `rule_violated` is the rule allowing the smallest qty, ties going to the lower rule number (D-19).
7. **Cumulative batch pass (REQ-5)**: rebuild a fresh ledger from the snapshot, replay accepted moves in acceptance order, re-run all rule checks. Quantity-bounded breaches (R1, R2, R5) trim `qty` to the largest legal value and log the trimmed-off units as a `RejectedMove` (qty = trimmed units, D-11); trimmed to 0 means drop, logged with the full qty. Binary breaches (R3, R4) drop and log. The logged rule is chosen as in step 6 (smallest allowed qty, ties to the lower rule number, D-19). Same rule code as step 6 (DRY); this is the guarantee behind AC-1 and AC-4.
8. **Finalize**: recompute `value_mrp` and the R6 flag from the final `qty`, assign `arrival = dispatch + route_days` (REQ-3), then build the reason (2.5.1).

#### 2.5.1 Reason string (REQ-6, D-6)
- `receiver_cover` = receiver snapshot style cover (D-18); `velocity` = receiver SKU velocity.
- S2S: `donor` = donor `store_id`, `donor_cover` = donor style cover after this move in batch order (the R5 value).
- W2S: `donor` = `"WH-KOL"`, `donor_cover` = WH remaining non-quarantined SKU on-hand after this move / `wh_velocity[sku]`, or `"n/a"` when `wh_velocity` is absent, lacks the SKU, or is 0 (D-16).
- When `donor_cover` is `"n/a"`, the reason renders `retains n/a cover` (no `d` suffix); otherwise the literal REQ-6 template is used (D-20).
- Cover and velocity are rounded to 1 decimal (`f"{x:.1f}"`); `qty` is an integer.

#### 2.5.2 Rule applicability

| Rule | W2S | S2S | Mode |
|---|---|---|---|
| R1 donor category on-hand (on-hand only, D-7; quarantined counted, negative clamped to 0, D-15) after move >= min for tier | n/a (WH has no tier) | yes | trim |
| R2 receiver on-hand + in-transit + all accepted inbound <= capacity; outbound never frees capacity (D-7); quarantined counted, negative on-hand clamped to 0 (D-15) | yes | yes | trim |
| R3 no outbound of a protected style, any size, from its S++ store | n/a | yes | drop |
| R4 receiver snapshot `in_transit == 0` for the SKU; accepted moves in the batch do not count (D-17) | yes | yes | drop |
| R5 donor style cover after move >= 30 days (D-5) | n/a | yes | trim |
| R6 `qty x mrp > 1,00,000` sets `requires_human_approval = True` | yes | yes | flag only |

Not a hard rule but always enforced: a move never sends more than the source's non-quarantined on-hand for the SKU.

### 2.6 Requirement and acceptance traceability

| Item | Satisfied by | Verified by |
|---|---|---|
| REQ-1 | Phase A, source `WH-KOL` on-hand only, rank by `sku_velocity x mrp` | `test_generation_w2s`: ranking, exhaustion stop and hand-off to Phase B, `warehouse_inbound` ignored, no other source |
| REQ-2 | Phase B, donor filters, route then surplus-cover ordering | `test_generation_s2s`: same city over same zone over cross zone; equal routes pick higher cover then lower `store_id`; ineligible donors skipped |
| D-1 sizing | `need = ceil(v x T) - on_hand - in_transit`, capped | `test_need_sizing`: ceil rounding, `need <= 0` skipped, caps by supply, R1, R2, R5 |
| D-2, D-13, D-14 eligibility | style cover vs `T` | `test_deficit_detection`: style cover across sizes, `T` = max viable route, no-viable-route threshold and unfulfilled report, `None` cover neither deficit nor donor |
| REQ-3 | route resolution + `dispatch + days` | `test_routes_dates`: all 6 routes give expected arrival dates |
| REQ-4 / AC-1 | `rules.py` + per-candidate validation | `test_rules_*` (one per rule, pass and fail); independent validator on full run |
| AC-2 | R3 | `test_rule_flagship` for every size of a protected style |
| AC-3 | R6 recomputed after trim | `test_rule_approval`: exactly ₹1,00,000 not flagged, ₹1,00,001 flagged; trimmed move re-flagged |
| REQ-5 / AC-4 | batch pass | `test_batch_pass`: two moves legal alone, illegal together, for R2 and R1; trim logged with trimmed units, drop logged with full qty |
| D-7 | R1 on-hand only, R2 no outbound credit | `test_rule_capacity_no_outbound_credit`, `test_rule_min_display_on_hand_only` |
| REQ-6 / AC-5 | `explain.py` | `test_reason_reconciles`: parse reason, recompute each number (1 decimal) from fixture inputs; W2S uses `"WH-KOL"` and `retains n/a cover` when `wh_velocity` absent (D-20) |
| REQ-7 / AC-6, D-19 | `RejectedMoveLog` writes | `test_rejected_log`: one fixture per rule, exactly one entry with that rule code and all REQ-7 fields; several binding rules log the smallest-qty rule, ties to the lower number |
| D-4 | `UnfulfilledDeficit` list | `test_unfulfilled`: no viable donor gives one unfulfilled entry and no `RejectedMoveLog` entry for the deficit itself |
| D-9, D-15, D-21 quarantine | candidate filter, ledger aggregates, unfulfilled report | `test_quarantine_excluded`: quarantined position is never source or receiver; quarantined receiver with need > 0 gives one `UnfulfilledDeficit` with a quarantine reason; `test_ledger`: still counted in R1/R2 aggregates, negative on-hand clamped to 0 |
| D-17 repeat moves | R4 on snapshot only | `test_generation_s2s`: W2S partial plus S2S top-up of one SKU to one receiver is allowed |
| Tied priorities | sort keys (2.7) | `test_determinism`: run twice and with shuffled input order, identical output |

### 2.7 Deterministic tie-breaking
- Needs (Phase A and Phase B): revenue loss (`sku_velocity x mrp`) desc, then `sku_id` asc, then receiver `store_id` asc (spec edge case).
- Donors (Phase B): route days asc, then current donor style cover desc, then donor `store_id` asc (D-10).
- Every iteration over stores, SKUs or donors is over an explicitly sorted list; no reliance on dict or set order. No randomness.

### 2.8 Test and verification strategy
- pytest, dev-only (D-8). Tests live in `tests/moves/` and build `EngineInputs` fakes directly (D-9) via small builders in `tests/moves/fakes.py`; no real data in unit tests (AGENTS.md). Run from the repo root with `python3 -m pytest tests/moves -q`.
- **Independent validator (AC-1)**: `tests/moves/independent_validator.py` re-checks all 6 rules cumulatively on the final `approved_moves` plus the same inputs. It must not import from `src/moves/`; rule logic, thresholds and the Safa/Mala/Stole map are written again from the spec text and 2.10. The duplication is deliberate (an independent check cannot share the code it checks) and carries an inline comment per AGENTS.md. It also asserts no move exceeds source on-hand and no quarantined position is used.
- Integration test on `data/csv/` waits for Track 1/2 adapters to `EngineInputs`; it asserts zero validator violations (AC-1, AC-2, AC-4) and 100% R6 coverage (AC-3). Marked skip until the adapters exist.

### 2.9 Risks and trade-offs
- **Upstream adapters**: real-data verification waits for Track 1/2 to build `EngineInputs`. Mitigation: own contract plus fakes (D-9), so all unit work is unblocked.
- **Contract drift**: Track 1/2 may shape data differently; adapters absorb it. `config.py` duplicates `lead_times.csv` day values until a shared config exists (D-12).
- **Single threshold `T`**: a receiver is a deficit against the longest viable route but is served shortest-route-first; a near donor may over-serve relative to its own transit time. Accepted per D-2.
- **Mixed granularity**: deficit and R5 use style cover while moves and need use SKU values (D-5). A style can be a deficit while a given size needs nothing (skipped), or the reverse (not served). Accepted per D-5.
- **Float comparisons**: thresholds compare raw floats; rounding happens only in the reason (1 decimal). R5 guarantees donor cover >= 30.0, so the reason never shows a value below the threshold.
- **Greedy allocation**: priority-ordered greedy is deterministic and explainable but not globally optimal. Transport cost optimization is out of scope.
- **Batch pass vs generation**: generation already uses a running ledger, so the batch pass should rarely change anything. It stays as defense in depth because REQ-5 requires it and AC-1 depends on it.

### 2.10 Decisions (user-confirmed)
- **D-1 Move qty (Q-6)**: fill to lead-time cover, `qty = ceil(velocity x lead_time) - on_hand - in_transit` on the SKU basis, capped by supply, donor limits (R1, R5) and receiver capacity (R2). One move per SKU.
- **D-2 Eligibility (Q-14)**: receiver is a deficit if cover < max viable route lead time (single threshold, not literal per-route). Then shortest-route donor first: same city, same zone, cross zone.
- **D-3 WH supply (Q-15)**: `WH-KOL` on-hand only (REQ-1). `warehouse_inbound` is ignored.
- **D-4 Unfulfilled (Q-8)**: separate `UnfulfilledDeficit` list. `RejectedMoveLog` is only for rejected candidate moves (REQ-7).
- **D-5 Cover granularity (Q-4, Q-7)**: style cover (across sizes at a store) for deficit detection, donor eligibility and R5. Moves are per SKU. R1 and donor eligibility use category on-hand.
- **D-6 Reason (Q-10)**: `receiver_cover` is pre-move. W2S `donor = "WH-KOL"`, `donor_cover` = post-move warehouse cover in days or `"n/a"` if undefined. Cover and velocity rounded to 1 decimal.
- **D-7 R1/R2 basis (Q-16)**: R1 donor stock is on-hand only. A store's own outbound moves never free capacity for its inbound moves in the same batch.
- **D-8 Layout and tooling (Q-1, Q-13)**: `src/moves/`, `tests/moves/`. Engine is Python stdlib only; pytest is a dev dependency only.
- **D-9 Inputs (Q-2, Q-9)**: Track 3 defines its own small input contract (snapshot, velocity, cover, quarantine flags). Tests use fakes; Track 1/2 adapt later. Quarantined rows are excluded from candidates.
- **D-10 Donor ties (Q-12)**: equal lead time ordered by highest surplus cover, then `store_id`.
- **D-11 Trim logging (Q-11)**: batch-pass trims log the trimmed-off units in `RejectedMoveLog`; full drops are logged too.
- **D-12 Config (Q-3, Q-5)**: single `src/moves/config.py` with frozen constants (45 d, 30 d, ₹1,00,000, dispatch `2026-11-01`, as-of `2026-10-31`, lead times, Safa/Mala/Stole map). Moves to shared config when Track 1 defines one.

- **D-13 Viable route and sizing lead time (R-OQ-1)**: a route is viable if its source holds stock (`WH-KOL` on-hand for the style, or an eligible donor on that route type). `T` = longest lead time among viable routes, used for both deficit detection and the qty formula. A store x style with no viable route is reported as unfulfilled, evaluated against the longest lead time of any route to that store.
- **D-14 Zero or undefined style velocity (R-OQ-2)**: `style_cover = None` is not a deficit and not an eligible donor.
- **D-15 Quarantined rows (R-OQ-3)**: excluded from candidates (as receiver or donor positions) but still counted in category on-hand (R1) and capacity load (R2). Values are used as-is, except negative on-hand is clamped to 0 for R1/R2 counting.
- **D-16 Warehouse cover velocity (R-OQ-4)**: `wh_velocity` is an optional input; post-move warehouse cover in the reason is `"n/a"` when absent. No velocity is invented.
- **D-17 Repeat moves in one batch (R-OQ-5)**: one batch may send the same SKU to the same receiver more than once; R4 checks snapshot `in_transit` only.
- **D-18 Pre-move receiver cover (R-OQ-6)**: `receiver_cover` in the reason is the snapshot style cover.
- **D-19 Rule code when several rules bind (OQ-T1)**: when several rules block or limit the same candidate (per-candidate check or batch-pass trim/drop), `rule_violated` is the rule allowing the smallest qty; ties go to the lower rule number.
- **D-20 Undefined donor cover rendering (OQ-T2)**: when W2S donor cover is `"n/a"`, the reason renders `retains n/a cover` (no `d` suffix); otherwise the literal REQ-6 template.
- **D-21 Quarantined receiver with need (OQ-T3)**: a SKU with need > 0 whose receiver position is quarantined gets no candidate and is reported in `UnfulfilledDeficit` with a quarantine reason.
- **D-22 Phase B donor eligibility basis (OQ-T4)**: S2S donor eligibility (cover > 45 d, category on-hand > min display) is evaluated on the running ledger; the snapshot is used only for viable-route detection.
- **D-23 Input conventions (OQ-T5)**: the 3.3 conventions are confirmed as written: missing positions and velocities = 0, missing `style_cover` = `None`, missing `min_display` entry or unknown zone raises `KeyError`, a position for a SKU not in `items` or at an unknown location raises `ValueError`.

### 2.11 Remaining open questions
None remaining (R-OQ-1..R-OQ-6 resolved as D-13..D-18, OQ-T1..OQ-T5 resolved as D-19..D-23).

## 3. Tasks
Gate 2 approved: the user approved this task list and decided OQ-T1..OQ-T5 (D-19..D-23).

### 3.1 Dependency order
| Wave | Tasks (parallel within a wave) | Depends on |
|---|---|---|
| 1 | T-1 | none |
| 2 | T-2, T-3 | T-1 |
| 3 | T-4; T-10; T-12 | T-4: T-2, T-3. T-10: T-3. T-12: T-3 |
| 4 | T-5; T-7 | T-4 |
| 5 | T-6 | T-5 |
| 6 | T-8 | T-6, T-7 |
| 7 | T-9 | T-8 (same file) |
| 8 | T-11 | T-6, T-9, T-10 |
| 9 | T-13 | T-11, T-12 |
| 10 | T-14 | T-1..T-13 |
| Deferred | T-15 | Track 1/2 adapters, T-11, T-12 |

### 3.2 Execution protocol
- Each task runs in a NEW subagent (Sonnet 5.5, medium effort) with a fresh context. Its brief is Section 1, Section 2 and its own task entry of this file. It reads no other file under `docs/spec/`.
- A task edits only the files listed under its "Files". It never edits other tracks' code or specs (`src/domain/`, `src/infrastructure/`, `tests/test_ingestion.py`, other files in `docs/spec/`). In this file it changes only its own checkbox (`- [ ]` to `- [x]`) with a one-line exact edit; if the edit fails because a parallel task changed the file, re-read and retry.
- Test-first: write the listed tests, run them and see them fail, implement, run them and see them pass.
- Tick the checkbox only after "Done when" holds, with real command output.
- Report back: files changed, command output summary, deviations from the Plan, anything left undone.
- Anything ambiguous or missing is returned as a question to the orchestrator, never guessed. No invented thresholds, velocities, fields or adapters.
- No commits, no dependency other than pytest, no file I/O in `src/moves/`, stdlib only in `src/moves/`.
- Header Status changes (`In Progress`, `Blocked`, `Implemented`), the `Stopped at:` note and the Spec memory file are the orchestrator's job, not a task's.

### 3.3 Shared conventions (all tasks)
- Python 3.10, `from __future__ import annotations`, type hints, frozen dataclasses. Imports as `from src.moves.<module> import ...`. Run everything from the repo root with `python3 -m pytest`.
- `tests/moves/` has no `__init__.py`; pytest's default import mode puts it on `sys.path`, so tests import helpers as `from fakes import ...` and `from independent_validator import ...`.
- Every iteration over stores, styles, SKUs, needs or donors is over an explicitly sorted list (2.7).
- Absent-key conventions (D-23): missing position = `on_hand 0`, `in_transit 0`, not quarantined; missing `sku_velocity` or `style_velocity` = `0.0`; missing `style_cover` = `None` (D-14). Missing `min_display` entry or unknown zone raises `KeyError`. A position whose `sku_id` is not in `items`, or whose `location_id` is neither a store nor `WH-KOL`, raises `ValueError` when `EngineInputs` is built.

### 3.4 Task list
- [x] **T-1 Dev tooling and package skeleton** (D-8)
  - Files: create `requirements-dev.txt` (one line `pytest==8.3.5`) and an empty `src/moves/__init__.py`. If `requirements-dev.txt` already exists, add the pytest line only if pytest is absent; if a different pytest pin exists, stop and ask. Create no `pyproject.toml`, no `tests/moves/__init__.py`, no pytest config.
  - Install: `python3 -m pip install --user -r requirements-dev.txt`.
  - Done when: `python3 -m pytest --version` prints 8.3.5 and `python3 -c "import src.moves"` exits 0.

- [x] **T-2 Config constants** (2.2 config row, D-12; REQ-2, REQ-3, REQ-4 R1/R5/R6)
  - Files: `src/moves/config.py`, `tests/moves/test_config.py`.
  - Behavior: `AS_OF_DATE = date(2026, 10, 31)`, `DISPATCH_DATE = date(2026, 11, 1)`, `WH_LOCATION = "WH-KOL"`, `DONOR_SURPLUS_DAYS = 45`, `DONOR_SAFETY_DAYS = 30`, `APPROVAL_THRESHOLD_MRP = 100_000`, `W2S_DAYS_BY_ZONE` (East 3, North 4, South 6), `S2S_SAME_CITY_DAYS = 2`, `S2S_SAME_ZONE_DAYS = 4`, `S2S_CROSS_ZONE_DAYS = 7`, `ACCESSORIES_CATEGORY = "Accessories (Safa/Mala/Stole)"`, `CATEGORY_MAP` (Safa, Mala, Stole to it). Mappings are read-only (`types.MappingProxyType`). One function `display_category(category) -> str` (mapped, else unchanged). Comment that day values mirror `data/csv/lead_times.csv` until a shared config exists (D-12).
  - Tests first: every value; mappings reject assignment (`TypeError`); `display_category` for Safa, Mala, Stole and an unchanged case (`Kurta Set`).
  - Done when: `python3 -m pytest tests/moves/test_config.py -q` passes.

- [x] **T-3 Input contract, models, test builders** (2.3, 2.4, 3.3; D-9, D-15, D-16, D-23; REQ-3, REQ-6, REQ-7)
  - Files: `src/moves/inputs.py`, `src/moves/models.py`, `tests/moves/fakes.py`, `tests/moves/test_inputs_models.py`.
  - `inputs.py`: frozen `Store(store_id, city, zone, tier, stock_capacity_units: int)`, `Item(sku_id, style_id, category, mrp: int)`, `Position(location_id, sku_id, on_hand: int, in_transit: int, quarantined: bool = False)`, `EngineInputs(stores, items, positions` as tuples; `sku_velocity: Mapping[(store_id, sku_id), float]`, `style_velocity: Mapping[(store_id, style_id), float]`, `style_cover: Mapping[(store_id, style_id), float | None]`, `min_display: Mapping[(tier, display_category), int]`, `flagship: frozenset[(store_id, style_id)]`, `wh_velocity: Mapping[sku_id, float] | None = None)`. No `warehouse_inbound` field (D-3). Lookup helpers implementing 3.3 (`store`, `item`, `skus_of_style` sorted by `sku_id`, `position`, `sku_vel`, `style_vel`, `cover`), indexed lazily (`functools.cached_property` dicts). `__post_init__` raises `ValueError` for duplicate (`location_id`, `sku_id`) positions, for a position whose `sku_id` is not in `items`, and for a position whose `location_id` is neither a store nor `WH-KOL` (3.3, D-23). Lookups of a missing `min_display` entry or an unknown zone raise `KeyError` (D-23).
  - `models.py`: `MoveType(str, Enum)` W2S, S2S; `HardRule(str, Enum)` values `"R1"`..`"R6"`; frozen `CandidateMove(move_type, from_location, to_location, sku_id, style_id, qty: int, route_days: int)` with `with_qty(qty)`; frozen `ApprovedMove` with exactly the 2.4 fields (`receiver_cover: float`, `velocity: float`, `donor_cover: float | None` included); `RejectedMove` with exactly the REQ-7 fields (`rule_violated: HardRule`); `UnfulfilledDeficit(store_id, style_id, sku_id, needed_qty, unfilled_qty, reason)`; `EngineResult(approved_moves, rejected_moves, unfulfilled_deficits)` as tuples.
  - `fakes.py`: keyword-default builders `store(...)`, `item(...)`, `pos(...)`, and `make_inputs(**overrides)` with empty mappings and a default `min_display` literal equal to the 24 rows of `data/csv/min_display.csv` (typed in, not read from disk).
  - Tests first: frozen instances; 3.3 conventions and `ValueError` cases; `skus_of_style` order; `RejectedMove` field names equal the REQ-7 list exactly (`dataclasses.fields`).
  - Done when: `python3 -m pytest tests/moves/test_inputs_models.py -q` passes.

- [x] **T-4 Inventory ledger** (2.2 ledger row, 2.5 step 1, 2.5.2; D-7, D-15, D-17, D-23; REQ-5)
  - Files: `src/moves/ledger.py`, `tests/moves/test_ledger.py`.
  - A (`location_id`, `sku_id`) with no position reads as `on_hand 0`, `in_transit 0`, not quarantined (3.3, D-23).
  - `InventoryLedger.from_inputs(inputs)` and:
    - `available(location_id, sku_id) -> int`: `max(0, snapshot on_hand - accepted outbound)` for a non-quarantined position; 0 if quarantined (D-15).
    - `category_on_hand(store_id, display_category) -> int`: sum of `max(0, on_hand)` over all the store's positions of that display category, quarantined included (D-15), minus accepted outbound units of that category. Accepted inbound is not added (D-7, on-hand only).
    - `capacity_load(store_id) -> int`: sum of `max(0, on_hand) + in_transit` over all the store's positions, quarantined included (D-15), plus accepted inbound units. Outbound is never subtracted (D-7).
    - `style_units_out(store_id, style_id) -> int`; `snapshot_in_transit(store_id, sku_id) -> int` (never changed by `apply`, D-17); `is_quarantined(location_id, sku_id) -> bool`.
    - `apply(move: CandidateMove)`: records outbound at the source and inbound at the receiver. `WH-KOL` positions count toward no store aggregate.
  - Tests first (`test_ledger`): a quarantined row and a row with on-hand -4 are counted in R1/R2 aggregates, clamped to 0; S2S apply lowers donor `available` and `category_on_hand`, raises receiver `capacity_load`, leaves donor `capacity_load` unchanged; W2S apply lowers WH `available`; `snapshot_in_transit` unchanged after apply; quarantined `available == 0`; a missing position gives `available == 0`, `snapshot_in_transit == 0`, `is_quarantined == False`.
  - Done when: `python3 -m pytest tests/moves/test_ledger.py -q` passes.

- [x] **T-5 Hard rules R1..R6** (2.2 rules row, 2.5.2; D-5, D-7, D-14, D-15, D-17; REQ-4; AC-2, AC-3)
  - Files: `src/moves/rules.py`, `tests/moves/test_rules.py`.
  - `HardRuleCheck` Protocol: `rule: HardRule`; `max_allowed_qty(move, ledger) -> int` in `[0, move.qty]`, the largest qty of this move that keeps the rule given the ledger state before the move; `describe(move, ledger) -> str`, a one-line rejection reason with the numbers used. Rules take `EngineInputs` in their constructor. A rule not applicable to the move type (2.5.2) returns `move.qty`.
    - `MinDisplayRule` R1 (S2S): room = `category_on_hand(donor, cat) - min_display[(tier, cat)]`.
    - `CapacityRule` R2 (both): room = `capacity - capacity_load(receiver)`.
    - `FlagshipRule` R3 (S2S): 0 if `(from_location, style_id) in flagship`.
    - `InTransitRule` R4 (both): 0 if `snapshot_in_transit(receiver, sku) != 0`.
    - `DonorSafetyRule` R5 (S2S): 0 if cover is `None` or style velocity `<= 0` (D-14). Else the largest `u` in `[0, qty]` with `cover - (style_units_out + u) / velocity >= 30`, evaluated with exactly that float expression (start at `floor((cover - 30) * velocity - out)`, adjust by 1 until the predicate holds for `u` and fails for `u + 1`), so float rounding cannot disagree with the independent validator.
    - `ApprovalRule` R6: never limits qty; `requires_approval(qty, mrp) -> bool` = `qty * mrp > APPROVAL_THRESHOLD_MRP`.
    - `default_rules(inputs)` returns the six in R1..R6 order.
  - Tests first, one pass and one fail per rule: R1 boundary (post-move == min passes, one below fails) and Accessories aggregation; `test_rule_min_display_on_hand_only` (in-transit does not count); R2 boundary and `test_rule_capacity_no_outbound_credit`; `test_rule_flagship` for every size of a protected style (AC-2), unprotected style passes; R4 `in_transit` 1 blocks, 0 passes; R5 to exactly 30.0 passes, `None` cover and zero velocity block; `test_rule_approval` `qty x mrp == 100000` not flagged, `100001` flagged (AC-3); W2S is unaffected by R1, R3, R5.
  - Done when: `python3 -m pytest tests/moves/test_rules.py -q` passes.

- [x] **T-6 Constraint validation: per-candidate check and batch pass** (2.5 steps 6-7; D-11, D-19; REQ-4, REQ-5, REQ-7; AC-4, AC-6)
  - Files: `src/moves/validation.py`, `tests/moves/test_validation.py`.
  - `ConstraintValidationService(inputs, rules=None)` (default `default_rules(inputs)`), with `rejected: list[RejectedMove]` in write order.
  - `check(candidate, ledger) -> int`: allowed = min(`ledger.available(source, sku)`, each rule's `max_allowed_qty`). If a rule makes it 0, append one `RejectedMove` (qty = candidate qty, `rule_violated` = the rule allowing the smallest qty, ties to the lower rule number (D-19), `rejection_reason` = that rule's `describe`) and return 0. A 0 caused only by source availability is not logged (not a hard rule). `0 < allowed < qty` is sizing and not logged (2.5 step 6). Never mutates the ledger.
  - `batch_pass(moves) -> list[CandidateMove]`: fresh `InventoryLedger.from_inputs`, replay in the given order; same allowed computation without the step-6 logging. Equal: keep. `0 < allowed < qty`: keep the trimmed copy, log a `RejectedMove` with qty = trimmed-off units and the binding rule (D-11). 0: drop, log the full qty. In both cases the logged rule is the one allowing the smallest qty, ties to the lower rule number (D-19). Apply kept moves. If source availability alone would bind, raise `RuntimeError` (generation makes it impossible). Return kept moves in order.
  - Tests first: `test_rejected_log` (AC-6): one fixture per rule R1..R5, exactly one entry with that rule code and all REQ-7 fields filled; a candidate blocked by R2 and R4 together logs R2 (tie, lower number); a batch-pass trim bound by two rules logs the one allowing the smaller qty (D-19); a trim inside `check` logs nothing; `test_batch_pass` (AC-4): two moves legal alone and illegal together, for R2 and for R1, trim logged with trimmed units, drop logged with full qty; an already legal list comes back unchanged with no log entries.
  - Done when: `python3 -m pytest tests/moves/test_validation.py -q` passes.

- [x] **T-7 Generation core: routes, dates, deficits, need sizing** (2.5 steps 2-3, 2.7; D-1, D-2, D-5, D-13, D-14, D-15; REQ-2, REQ-3)
  - Files: create `src/moves/generation.py`, `tests/moves/test_generation_core.py`.
  - Behavior (module functions; T-8 and T-9 add the phases to the same file):
    - `route_days(source_location, receiver_store_id, inputs) -> int`: `WH-KOL` gives `W2S_DAYS_BY_ZONE[receiver zone]`; a store gives same city 2, same zone 4, else 7 (config constants).
    - `arrival_date(route_days) -> date` = `DISPATCH_DATE + timedelta(days=route_days)` (REQ-3).
    - `is_eligible_donor(store_id, style_id, ledger, inputs) -> bool`: cover not `None` and `> 45`, and `category_on_hand(store, display category of the style) > min_display[(tier, cat)]` (REQ-2, D-5, D-14).
    - `detect_deficits(inputs, ledger) -> list[Deficit]` on a fresh (snapshot) ledger: per store x style (sorted) with defined cover, viable routes per D-13 (W2S if `available("WH-KOL", sku) > 0` for any SKU of the style; an S2S route type if some eligible donor of that type other than the receiver has `available > 0` for any SKU of the style). `T` = max viable days; with none viable, `T` = longest route of any type to the store (its W2S zone days and every S2S type for which another store with that relation exists) and `viable = False`. Deficit if `cover < T`.
    - `size_needs(deficit, inputs) -> list[Need]`: per SKU of the style (sorted), `need = ceil(sku_velocity x T) - on_hand - in_transit` (snapshot as-is, D-15); keep `need > 0`. `Need` carries `store_id`, `style_id`, `sku_id`, `T`, `need`, `viable`, receiver `quarantined`, `revenue_loss = sku_velocity x mrp`.
    - `sort_needs(needs)`: key `(-revenue_loss, sku_id, store_id)` (2.7).
    - `Deficit`, `Need`: small frozen dataclasses in this file.
  - Tests first: `test_routes_dates`: the 6 routes give arrivals 2026-11-04 (East), 2026-11-05 (North), 2026-11-07 (South), 2026-11-03 (same city), 2026-11-05 (same zone), 2026-11-08 (cross zone); `test_deficit_detection`: style cover across sizes, `T` = max viable (WH North 4 plus same city donor 2 gives 4), a route whose source holds no stock is not viable, no-viable store gets the longest route and `viable = False`, `None` cover is neither deficit nor donor, donor cover exactly 45 not eligible; `test_need_sizing`: ceil (velocity 0.3, `T` 4 gives 2), on-hand and in-transit subtracted, `need <= 0` dropped; `sort_needs` tie order.
  - Done when: `python3 -m pytest tests/moves/test_generation_core.py -q` passes.

- [x] **T-8 Phase A: Warehouse-to-Store allocation** (2.5 steps 3-4; D-1, D-3, D-4, D-13, D-15, D-21; REQ-1; edge case "Warehouse Stock Exhaustion")
  - Files: edit `src/moves/generation.py`; create `tests/moves/test_generation_w2s.py`.
  - `MoveGenerationService(inputs, validator).generate(ledger) -> GenerationResult(accepted: list[CandidateMove], unfulfilled: list[UnfulfilledDeficit])`: detect, size, sort, then:
    - Non-viable needs (D-13): `UnfulfilledDeficit(needed_qty = unfilled_qty = need, reason = f"no viable route; threshold {T}d")`, no candidate.
    - Needs whose receiver position is quarantined (checked after the non-viable case; one entry per need): `UnfulfilledDeficit(needed_qty = unfilled_qty = need, reason = "receiver position quarantined")`, no candidate, no `RejectedMove` (D-21).
    - Phase A, per need in sorted order: `wh = ledger.available("WH-KOL", sku)`; `wh <= 0` skips (not a rejection, need unchanged). Else W2S candidate with `qty = min(residual, wh)` and `route_days(...)`; `allowed = validator.check(candidate, ledger)`; if `> 0`, accept `candidate.with_qty(allowed)`, `ledger.apply`, reduce residual.
    - Residual `> 0` at the end: `UnfulfilledDeficit(needed_qty = need, unfilled_qty = residual, reason = f"unfilled {residual} of {need} after W2S and S2S")` (T-9 inserts Phase B before this step).
  - Tests first (`test_generation_w2s`): limited WH stock goes to the higher `sku_velocity x mrp` need first; exhaustion stops cleanly with the remaining need left over, no rejection logged; only `WH-KOL` is a source; R4 (receiver `in_transit > 0`) and R2 (no room) each log one entry; partial R2 room trims qty without a log; quarantined WH position is never a source (`test_quarantine_excluded`, W2S part); quarantined receiver position with need > 0 gives one `UnfulfilledDeficit` with reason `receiver position quarantined` and no `RejectedMove` (D-21); non-viable need reported as unfulfilled.
  - Done when: `python3 -m pytest tests/moves/test_generation_core.py tests/moves/test_generation_w2s.py -q` passes.

- [x] **T-9 Phase B: Store-to-Store matching** (2.5 step 5, 2.7; D-2, D-4, D-5, D-10, D-14, D-15, D-17, D-22; REQ-2; edge case "Zero Viable Donors")
  - Files: edit `src/moves/generation.py`; create `tests/moves/test_generation_s2s.py`.
  - Behavior: after Phase A, for each need with residual `> 0` (same order): donors = stores other than the receiver with `is_eligible_donor` evaluated on the running ledger (current cover `cover - style_units_out / style_velocity > 45` and current `category_on_hand > min_display`, after earlier accepted moves; D-22) and `ledger.available(donor, sku) > 0`. Order by route days asc, current donor style cover desc (`cover - style_units_out / style_velocity`), `store_id` asc (D-10). Per donor: S2S candidate `qty = min(residual, available)`; `allowed = validator.check(...)`; accept if `> 0`, apply, reduce residual; stop at 0. Residual left goes to unfulfilled as in T-8 (D-4). A SKU may get both W2S and S2S moves to one receiver (D-17).
  - Tests first (`test_generation_s2s`): same city over same zone over cross zone; equal routes pick higher current cover, then lower `store_id`; ineligible donors skipped (cover 45, category on-hand equal to min display, `None` cover); a donor eligible in the snapshot but at cover <= 45 after an earlier accepted move in the batch is skipped (D-22); protected style at an S++ donor logs R3 and the next donor is used; several donors fill one need; W2S partial plus S2S top-up of one SKU to one receiver; quarantined donor position never used (`test_quarantine_excluded`, S2S part); `test_unfulfilled`: no viable donor gives one `UnfulfilledDeficit` and no `RejectedMove` for the deficit itself.
  - Done when: `python3 -m pytest tests/moves/test_generation_core.py tests/moves/test_generation_w2s.py tests/moves/test_generation_s2s.py -q` passes.

- [x] **T-10 Explanation service** (2.5.1; D-6, D-16, D-18, D-20; REQ-6; AC-5)
  - Files: `src/moves/explain.py`, `tests/moves/test_explain.py`.
  - `ExplanationService.reason(qty, sku_id, receiver, receiver_cover, velocity, donor, donor_cover: float | None) -> str` fills exactly `"Send {qty}: {sku} has {receiver_cover}d cover at {receiver}, sells {velocity}/d; donor {donor} retains {donor_cover}d cover"`, covers and velocity as `f"{x:.1f}"`, `qty` as int. `None` donor cover renders the tail as `retains n/a cover` (no `d` suffix); otherwise the literal template (D-20). Pure formatting, no lookups.
  - Tests first: exact strings for one S2S and one W2S example; rounding matches `f"{x:.1f}"`; `None` donor cover gives a string ending `retains n/a cover`.
  - Done when: `python3 -m pytest tests/moves/test_explain.py -q` passes.

- [x] **T-11 Engine orchestration and finalize** (2.2 engine row, 2.4, 2.5 steps 1-8; D-6, D-16, D-18, D-20; REQ-3, REQ-6; AC-3, AC-5)
  - Files: `src/moves/engine.py`, `tests/moves/test_engine.py`.
  - `MoveEngine().run(inputs) -> EngineResult`: ledger from inputs; `validator = ConstraintValidationService(inputs)`; `MoveGenerationService(inputs, validator).generate(ledger)`; `final = validator.batch_pass(accepted)`; `approved = finalize(inputs, final)`; `rejected_moves = tuple(validator.rejected)`; unfulfilled from generation.
  - `finalize(inputs, moves) -> tuple[ApprovedMove, ...]` (module function, so tests can pass a trimmed list): replay on a fresh ledger in order; per move, after `apply`: `value_mrp = qty x mrp`; `requires_human_approval = ApprovalRule.requires_approval(qty, mrp)`; `dispatch_date = DISPATCH_DATE`; `arrival_date = arrival_date(route_days)`; `receiver_cover` = snapshot style cover (D-18); `velocity` = receiver SKU velocity; S2S `donor_cover = cover - style_units_out / style_velocity`; W2S `donor_cover = available("WH-KOL", sku) / wh_velocity[sku]`, or `None` if `wh_velocity` is `None`, lacks the SKU or is 0 (D-16); `reason` from `ExplanationService` with donor `store_id` or `"WH-KOL"`.
  - Tests first: end-to-end fixture with one W2S and one S2S move (dates, value, flag); `test_reason_reconciles` (AC-5): parse every reason with a regex and recompute each number (1 decimal) from the fixture inputs inside the test; W2S shows `WH-KOL`, `retains n/a cover` without `wh_velocity` (D-20) and `retains {x:.1f}d cover` with it; `finalize` on a trimmed move recomputes `value_mrp` and the flag (AC-3).
  - Done when: `python3 -m pytest tests/moves -q` passes.

- [x] **T-12 Independent validator (test-only)** (2.8; AC-1..AC-4; D-7, D-13..D-17)
  - Files: `tests/moves/independent_validator.py`, `tests/moves/test_independent_validator.py`.
  - `find_violations(inputs, approved_moves) -> list[str]` (empty = clean). Must not import from `src` at all; reads inputs and moves by attribute. Thresholds (30 d, ₹1,00,000, dispatch `2026-11-01`, route days, Safa/Mala/Stole map) are typed again from Section 1 and 2.10, with an inline comment that the duplication is deliberate (independent check). Cumulative checks over the whole list:
    - R1: per S2S donor and display category, `sum(max(0, on_hand))` over all its positions (quarantined included) minus all outbound units `>= min_display`.
    - R2: per receiver, `sum(max(0, on_hand) + in_transit)` (quarantined included) plus all inbound `<= capacity`.
    - R3: no S2S with `(from_location, style_id)` in `flagship`.
    - R4: snapshot `in_transit` of (receiver, sku) `== 0`.
    - R5: per S2S donor and style, cover defined, velocity `> 0`, `cover - total_out / velocity >= 30`.
    - R6: `value_mrp == qty x mrp` and `requires_human_approval == (qty x mrp > 100000)`.
    - Also: `qty > 0`; units sent per (source, sku) `<=` non-quarantined source on-hand; no quarantined source or receiver position; `dispatch_date == 2026-11-01`; `arrival_date` = dispatch + route days recomputed from store city and zone.
    - Each message names the rule and the move.
  - Tests first: clean list gives `[]`; one hand-built violating list per check gives a message for that rule (the test file may build moves with `src.moves.models.ApprovedMove`); an `ast` test that `independent_validator.py` has no `Import`/`ImportFrom` of `src`.
  - Done when: `python3 -m pytest tests/moves/test_independent_validator.py -q` passes.

- [x] **T-13 Determinism and edge-case tests** (2.6 tied priorities, 2.7, Section 1 edge cases; AC-1, AC-4)
  - Files: `tests/moves/test_determinism.py`, `tests/moves/test_edge_cases.py`. Test-only: if a test exposes an engine bug, stop and report it; do not edit `src/moves/` in this task.
  - `test_determinism`: a fixture with at least 6 stores over 3 zones, 2 styles, W2S and S2S moves, at least one rejection and one unfulfilled deficit; two runs give equal `EngineResult`; the same inputs with tuples and mapping insertion order shuffled (`random.Random(0)`) give an equal result.
  - `test_edge_cases`: WH exhaustion (WH stock below total need: allocation stops, remaining need served by S2S, no rejection logged for exhaustion); tied priorities (equal revenue loss ordered by `sku_id`, then `store_id`; equal route and cover donors ordered by `store_id`); zero viable donors (unfulfilled deficit, no invalid move, no `RejectedMove` for the deficit).
  - Every engine result in both files also asserts `find_violations(inputs, result.approved_moves) == []` (AC-1).
  - Done when: `python3 -m pytest tests/moves -q` passes.

- [x] **T-14 Final verification** (REQ-1..REQ-7, AC-1..AC-6)
  - Files: none, except this task's checkbox.
  - Run `python3 -m pytest tests/moves -q` and `python3 -m pytest -q` (whole repo; report Track 1 failures, do not fix them). `git status --porcelain` shows changes only under `src/moves/`, `tests/moves/`, `requirements-dev.txt` and this spec file (ignore `__pycache__/`, `.pytest_cache/`). `grep -n import tests/moves/independent_validator.py` shows no `src` import.
  - Checklist, each with its proving test and real output: AC-1 (`find_violations == []` in T-13 tests), AC-2 (`test_rule_flagship`), AC-3 (`test_rule_approval`, `finalize` trim re-flag), AC-4 (`test_batch_pass`, validator R2), AC-5 (`test_reason_reconciles`), AC-6 (`test_rejected_log`).
  - Done when: all `tests/moves` tests pass and every checklist item is reported pass with output.

- [ ] **T-15 Real-data integration test** (2.8; AC-1..AC-4). DEFERRED.
  - Deferred by user decision (2026-11-21): no Track 1/2 adapter builds EngineInputs from data/csv/ (Track 2 velocity/cover has no code); real-data check moves to a later spec once Track 2 exists. Not part of this spec's delivered scope.
  - Do not start until Track 1/2 name the adapter module and function that build `EngineInputs` from `data/csv/`; do not guess the name.
  - Files: `tests/moves/test_integration_real_data.py`.
  - Behavior: `pytest.importorskip("<adapter module>")`, build inputs, `MoveEngine().run`, assert `find_violations == []` (AC-1, AC-2, AC-4) and every move with `value_mrp > 100000` flagged (AC-3).
  - Done when: `python3 -m pytest tests/moves/test_integration_real_data.py -q` passes, not skipped, with the adapters present.

### 3.5 Remaining open questions
None remaining (OQ-T1..OQ-T5 resolved as D-19..D-23).
