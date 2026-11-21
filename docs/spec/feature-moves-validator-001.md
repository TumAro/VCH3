# Track 3: Move Generation & Hard Constraints Engine
- Status: Draft
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
_To be written after Gate 1 approval._

## 3. Tasks
_To be written after Gate 1 approval._
