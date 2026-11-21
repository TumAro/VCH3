# Track 3: Move Generation & Hard Constraints Engine
- Status: Approved (Gate 1)
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
- No source code exists in the repo yet (no `src/`, no `pyproject.toml`, no tests). This plan is grounded only in docs and data.
- Stack and names come from `docs/architecture.md`: Python, pipeline entry `python -m src.cli`, services `MoveGenerationService`, `ConstraintValidationService`, `ExplanationService`, repository abstractions `IStoreRepository`, `IStockRepository`, `IRulesRepository` (sections 2, 3, 5.3, 5.4).
- Design rules come from `AGENTS.md`: Repository Pattern always, SOLID (SRP and OCP non-negotiable), DRY, services tested against fake repositories.
- Data facts come from `data/csv/` and `docs/problemStatement.md`:
  - `stores.csv` gives `city`, `zone`, `tier`, `stock_capacity_units` (needed for routing, Rule 1, Rule 2, Rule 3).
  - `items.csv` gives `style_id`, `category`, `mrp` (Rule 1 category, Rule 6 value, REQ-1 ranking).
  - `stock_snapshot.csv` gives `on_hand`, `in_transit` per `location_id` (store or `WH-KOL`) and SKU.
  - `min_display.csv` is keyed by tier and display category; `flagship_protected.csv` by `store_id` and `style_id` (80 rows, 4 S++ stores).
  - `lead_times.csv` holds 6 routes as free-text labels (e.g. `"Store to store, same city"`), not structured keys.

### 2.2 Architecture and modules
Proposed layout (pending Q-1). One package, one job per file.

| File | Responsibility | REQ |
|---|---|---|
| `src/moves/models.py` | Value types: `MoveType` (W2S, S2S), `HardRule` enum (R1..R6 codes), `CandidateMove`, `ApprovedMove`, `RejectedMove` (`RejectedMoveLog` entry), `UnfulfilledDeficit`, `EngineResult`. | REQ-3, REQ-6, REQ-7 |
| `src/moves/ledger.py` | `InventoryLedger`: simulated per-location SKU on-hand / in-transit, per-store category on-hand (display category), per-store total load, per-store style stock. Built from the inputs, mutated by `apply(move)`. Copyable for isolated checks. | REQ-5 |
| `src/moves/rules.py` | One class per hard rule behind a small `HardRuleCheck` protocol: `check(move, ledger) -> pass / fail / max_allowed_qty`. Six implementations, so the protocol is justified (OCP, per `docs/architecture.md` 2). Rule 6 only sets the flag, it never fails. | REQ-4 |
| `src/moves/generation.py` | `MoveGenerationService`: deficit detection, W2S allocation, S2S donor/receiver matching, route resolution, dispatch and arrival dates. | REQ-1, REQ-2, REQ-3 |
| `src/moves/validation.py` | `ConstraintValidationService`: per-candidate check (all applicable rules) and cumulative batch pass (replay, trim, drop). Writes `RejectedMoveLog`. | REQ-4, REQ-5, REQ-7 |
| `src/moves/explain.py` | `ExplanationService`: fills the REQ-6 template from the same ledger and metric values the decision used. | REQ-6 |
| `src/moves/engine.py` | `MoveEngine.run(inputs) -> EngineResult`: orchestrates generation, validation, batch pass, explanation. The only entry point Track 4 calls. | all |

Stdlib only (`dataclasses`, `datetime`, `enum`). No new runtime dependency.

### 2.3 Inputs consumed (contract required from Track 1 and Track 2)
The engine depends on abstractions only (DIP). Exact interface names and method signatures are not known to this spec (Q-2). Minimum data the engine needs:

| Data | Source | Used by |
|---|---|---|
| Store: `store_id`, `city`, `zone`, `tier`, `stock_capacity_units` | Track 1 `IStoreRepository` | routing, R1, R2, R3 |
| Item: `sku_id`, `style_id`, `category`, `mrp`; packaging already excluded | Track 1 | R1, R6, REQ-1 rank |
| Position per location x SKU: `on_hand`, `in_transit`; quarantined rows excluded or flagged (Q-9) | Track 1 `IStockRepository` | ledger, R2, R4 |
| `min_display` (tier x display category), flagship (store, style), lead-time route days | Track 1 `IRulesRepository` | R1, R3, REQ-3 |
| Category to display-category map (Safa, Mala, Stole to Accessories) | single shared definition (Q-3) | R1 |
| SKU daily velocity and SKU cover per store; style velocity and style cover per store | Track 2 | REQ-1, REQ-2, R5, REQ-6 |
| Cover formula (effective stock / velocity) and zero-velocity convention | Track 2 (reused, not re-implemented, Q-4) | R5 post-move cover |
| Thresholds: 45-day donor surplus, 30-day donor cover, ₹1,00,000 approval, dispatch date `2026-11-01` | config (Q-5) | REQ-2, R5, R6, REQ-3 |

### 2.4 Outputs
`EngineResult` returned to Track 4 (no file I/O here):
- `approved_moves`: list of `ApprovedMove` with `move_type`, `from_location`, `to_location`, `sku_id`, `style_id`, `qty`, `value_mrp` (`qty x mrp`), `dispatch_date`, `arrival_date`, `requires_human_approval`, `reason`, plus the metric values used to build the reason (for AC-5 spot-checks). Field list pending Q-10.
- `rejected_moves`: `RejectedMoveLog` entries with exactly the REQ-7 fields.
- `unfulfilled_deficits`: store x SKU deficits left after both phases (edge case "Zero Viable Donors"; Q-8).

### 2.5 Pipeline order
1. **Build ledger** from positions (snapshot state, as-of `2026-10-31`).
2. **Detect deficits**: store x SKU where receiver cover < route lead time (REQ-1, REQ-2). W2S route = `WH-KOL` to receiver zone. S2S eligibility is per donor-receiver pair because the route depends on both.
3. **Phase A, W2S (REQ-1)**: sort deficits by tie-break key (2.7). For each, propose `qty = min(need, WH-KOL remaining on-hand)` (need sizing: Q-6). Validate the candidate (step 5 rules) against the running generation ledger; accepted moves decrement `WH-KOL` and raise receiver stock. When `WH-KOL` on-hand for the SKU reaches 0, allocation for that SKU stops; remaining deficits flow to Phase B (edge case "Warehouse Stock Exhaustion").
4. **Phase B, S2S (REQ-2)**: for each remaining deficit, list eligible donors (style cover > 45 days, on-hand > min display, Q-7), order by route lead time ascending (same city, same zone, cross zone), then tie-break. Size `qty` so the donor stays within R1 and R5 (`max_allowed_qty` from the rule checks). If no donor qualifies, record an unfulfilled deficit, emit no move.
5. **Per-candidate validation (REQ-4)**: every candidate passes through all applicable rules (matrix below). Any fail produces a `RejectedMove` with the rule code and a data-backed `rejection_reason`; the candidate is not applied.
6. **Cumulative batch pass (REQ-5)**: rebuild a fresh ledger from the snapshot, replay accepted moves in priority order (Phase A order, then Phase B order), re-run all rule checks against the running ledger. Quantity-bounded breaches (R1, R2, R5) trim `qty` to the largest legal value; trimmed to 0 means drop. Binary breaches (R3, R4) drop. Every drop or trim is logged (trim logging: Q-11). This is the same rule code as step 5 in a different ledger mode (DRY), and it is the guarantee behind AC-1 and AC-4.
7. **Finalize**: recompute `value_mrp` and R6 flag from the final `qty`, assign dates (REQ-3: `arrival = dispatch + route days`), then build the reason string (REQ-6) from final values.

Rule applicability:

| Rule | W2S | S2S | Mode |
|---|---|---|---|
| R1 min display (donor category on-hand after move >= min for tier) | n/a (WH has no tier) | yes | trim |
| R2 capacity (receiver on-hand + in-transit + all accepted inbound <= capacity) | yes | yes | trim |
| R3 flagship (no outbound of protected style, any size, from S++ store) | n/a | yes | drop |
| R4 in-transit dedup (receiver `in_transit == 0` for SKU) | yes | yes | drop |
| R5 donor style cover after move >= 30 days | n/a | yes | trim |
| R6 value > ₹1,00,000 sets `requires_human_approval = True` | yes | yes | flag only |

### 2.6 Requirement and acceptance traceability

| Item | Satisfied by | Verified by |
|---|---|---|
| REQ-1 | `generation.py` Phase A, source restricted to `WH-KOL` on-hand, rank by `velocity x mrp` | `test_generation_w2s`: ranking, exhaustion stop, no source other than `WH-KOL` |
| REQ-2 | `generation.py` Phase B, donor/receiver filters, lead-time ordering | `test_generation_s2s`: same city chosen over same zone over cross zone; ineligible donors skipped |
| REQ-3 | route resolution + `dispatch + days` | `test_routes_dates`: all 6 routes produce expected arrival dates |
| REQ-4 / AC-1 | `rules.py` + per-candidate validation | `test_rules_*` (one per rule, pass and fail); independent validator on full run |
| AC-2 | R3 | `test_rule_flagship` on fixtures for every size; validator asserts on real data run |
| AC-3 | R6 recomputed after trim | `test_rule_approval`: boundary at exactly ₹1,00,000 (not flagged) and ₹1,00,001 (flagged); trimmed move re-flagged |
| REQ-5 / AC-4 | batch pass | `test_batch_pass`: two moves each legal alone, illegal together, for R2 and R1; expect trim or drop |
| REQ-6 / AC-5 | `explain.py` from final values | `test_reason_reconciles`: parse reason, recompute each number from fixture inputs, compare |
| REQ-7 / AC-6 | `RejectedMoveLog` writes | `test_rejected_log`: one fixture per rule violated, assert exactly one log entry with that rule code and all REQ-7 fields |
| Tied priorities | sort keys (2.7) | `test_determinism`: run twice, outputs identical; shuffled input order gives identical output |

### 2.7 Deterministic tie-breaking
- W2S: revenue loss (`velocity x mrp`) desc, then `sku_id` asc, then `store_id` asc (spec edge case).
- S2S: route lead-time days asc, then revenue loss desc, then `sku_id` asc, then receiver `store_id` asc, then donor `store_id` asc (donor order: Q-12).
- Every iteration over stores, SKUs, or donors is over an explicitly sorted list; no reliance on dict or set order. No randomness.

### 2.8 Test and verification strategy
- Unit tests run against fake in-memory repositories and hand-built ledgers (AGENTS.md: services tested against fakes, not real data).
- **Independent validator (AC-1)**: a test-only module (proposed `tests/moves/independent_validator.py`, Q-1) that takes the final `approved_moves` plus the same input data and re-checks all 6 rules cumulatively. It must not import anything from `src/moves/`; rule logic and the Safa/Mala/Stole map are written again from the spec text. This duplication is deliberate (an independent check cannot share the code it checks) and will carry an inline comment per AGENTS.md. It also asserts no move sends more than the source's available on-hand.
- Integration test: full run on `data/csv/` through Track 1 and Track 2 once they exist; assert validator reports zero violations (AC-1, AC-2, AC-4) and 100% R6 coverage (AC-3).
- Test runner: pytest is proposed (Q-13); nothing is installed yet.

### 2.9 Risks and trade-offs
- **Upstream dependency**: integration tests and real-data verification are blocked until Track 1 and Track 2 interfaces exist. Mitigation: unit tests on fakes first; contract in 2.3 to be confirmed.
- **Need sizing undefined**: without a target cover (Q-6), quantities are unknown; this blocks REQ-1 and REQ-2 implementation.
- **Literal eligibility rule**: receiver cover < route lead time means a receiver with 5 days cover qualifies only for a 7-day cross-zone route, which arrives after it runs out, and is never served by a 2-day same-city donor. Implemented as written unless changed (Q-14).
- **Float comparisons**: cover and revenue-loss values are floats; thresholds compare with the raw value, display rounding happens only in the reason string (Q-10). Two different rounding points could make a reason read "30d" for 29.96 days; tests cover this.
- **Greedy allocation**: priority-ordered greedy is deterministic and explainable but not globally optimal. Accepted; transport cost optimization is out of scope.
- **Batch pass vs generation**: generation already uses a running ledger, so the batch pass should rarely change anything. It stays as defense in depth because REQ-5 requires it and AC-1 depends on it.

### 2.10 Open questions (need user decision before Tasks)
- **Q-1 Module layout**: confirm `src/moves/` and `tests/moves/` (no existing convention in the repo).
- **Q-2 Track 1/2 interfaces**: exact repository and service names, method signatures, and entity shapes this engine consumes (2.3). Track 1/2 specs were not read for this plan.
- **Q-3 Category map ownership**: where the single Safa/Mala/Stole to Accessories mapping lives (Track 1, a shared module, or this engine).
- **Q-4 Cover reuse**: does Track 2 expose a cover function for post-move recomputation (R5)? What is cover when velocity is 0 (infinite, null, excluded)? Is cover computed at SKU level, style level, or both?
- **Q-5 Config**: which config file holds 45 days, 30 days, ₹1,00,000 and dispatch date, and who owns it (`docs/scope.md` NFR requires one config file).
- **Q-6 Quantity sizing**: how many units a move sends (e.g. bring receiver to a target cover in days, to lead time, to a fixed number). Not defined in the spec.
- **Q-7 Cover level for eligibility**: REQ-1 and REQ-2 receiver "cover" is SKU cover or style cover? REQ-2 donor "on-hand > minimum display": style on-hand or category on-hand compared with the category minimum?
- **Q-8 Unfulfilled deficits**: log them in `RejectedMoveLog` (with which `rule_violated` value) or in a separate list, as 2.4 proposes?
- **Q-9 Quarantined positions**: how Track 1 exposes quarantined rows (e.g. `KUR-02-M` at `MYS-02` on-hand -4, `SHW-02-L` at `KNP-03` over capacity) so the engine excludes them.
- **Q-10 Reason format details**: is `receiver_cover` pre-move or post-move? Rounding for cover and velocity? What fills `donor`/`donor_cover` for W2S moves (warehouse has no cover)? Final `ApprovedMove` field list.
- **Q-11 Trim logging**: when the batch pass trims a move, log the trimmed-off units in `RejectedMoveLog` or only full drops?
- **Q-12 Donor choice**: among donors with equal lead time, pick by donor `store_id` (proposed) or by most surplus cover?
- **Q-13 Test runner**: approve pytest as the dev dependency.
- **Q-14 Eligibility literalness**: keep receiver eligibility as cover < route lead time per route (see 2.9), or use a single threshold per receiver?
- **Q-15 Warehouse inbound**: REQ-1 allocates only `WH-KOL` on-hand; `docs/problemStatement.md` ("Warehouse supply") says to include planned `warehouse_inbound` after its `expected_date`. Confirm on-hand only for this track.
- **Q-16 R1 stock basis and R2 outbound credit**: R1 uses donor on-hand only (proposed) or on-hand + in-transit? Does a store's own outbound moves free capacity for its inbound moves under R2 (proposed: no credit)?

## 3. Tasks
_To be written after Gate 1 approval._
