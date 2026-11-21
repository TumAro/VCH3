# Track 2: Velocity & Cover Intelligence Engine
- Status: Draft
- Created: 2026-11-21

## 1. Spec

### Goal & context
Build the analytical intelligence engine that measures true customer demand and inventory runway across all Manyavar stores. The engine calculates stockout-aware daily sales velocity, applies peer-store fallbacks for new stores, computes effective inventory positions and forward cover days, evaluates stock age, and isolates hidden problem pockets (imminent stockout risks, ageing fashion traps, and zero-sales classification).

### Scope

**In Scope:**
- Computing stockout-aware daily velocity per store $\times$ SKU over the 12-week stock history:
  $$\text{velocity} = \frac{\sum \text{quantity sold}}{\sum \text{days in stock}}$$
- Rolling up SKU velocities to style level and category level per store.
- Cold-start peer fallback: For new stores with $< 28\text{ days}$ of history (`BLR-05`), inherit average velocity from peer stores of the same tier and city.
- Effective inventory position calculation: $\text{effective stock} = \text{on-hand} + \text{in-transit}$.
- Forward cover days calculation: $\frac{\text{effective stock}}{\text{daily velocity}}$.
- Stock age tracking in days relative to `2026-10-31` using `oldest_stock_received_on`.
- Generating structured "Findings" problem pockets:
  - Low-cover stockout risks: Stores where cover days are lower than the inbound route lead time.
  - High-cover ageing risks: Fashion styles (`is_core_style = 0`) exceeding 90 days age with $> 60\text{ days}$ cover.
  - Zero-sales diagnosis: Classifying every zero-sales SKU as either "no stock" (`days_in_stock == 0`) or "no demand" (`days_in_stock > 0`).

**Explicitly Out of Scope:**
- Raw CSV reading and data sanitization (Track 1).
- Move generation and constraint validation (Track 3).
- Presentation, API endpoints, and exports (Track 4).
- Machine learning or non-deterministic forecasting.

### Requirements
- **REQ-1:** Calculate daily sales velocity per store $\times$ SKU strictly dividing sales by `days_in_stock` from `stock_weekly`:
  - If $\sum \text{days in stock} > 0$: $\text{velocity} = \frac{\sum \text{qty sold}}{\sum \text{days in stock}}$.
  - If $\sum \text{days in stock} == 0$ and sales $== 0$: $\text{velocity} = 0.0$.
- **REQ-2:** Roll up daily velocity to style and category levels for each store.
- **REQ-3:** Detect new stores ($< 28\text{ days}$ of history, specifically `BLR-05`), and calculate their daily velocity as the arithmetic mean of established peer stores in the same city and tier.
- **REQ-4:** Compute effective stock ($\text{on\_hand} + \text{in\_transit}$) for every store $\times$ non-packaging SKU. Untrusted records flagged by Track 1 are excluded.
- **REQ-5:** Compute forward cover days:
  - If $\text{daily velocity} > 0$: $\text{cover} = \frac{\text{effective stock}}{\text{daily velocity}}$.
  - If $\text{daily velocity} == 0$ and $\text{effective stock} > 0$: $\text{cover} = 999.0\text{ days}$ (infinite cover).
  - If $\text{daily velocity} == 0$ and $\text{effective stock} == 0$: $\text{cover} = 0.0\text{ days}$.
- **REQ-6:** Compute stock age in days as $(\text{as\_of\_date} - \text{oldest\_stock\_received\_on})$. If the date is missing or null, age is 0.
- **REQ-7:** Detect and classify problem pockets into typed `Finding` objects:
  - `STOCKOUT_RISK`: store $\times$ SKU where effective cover $<$ route lead time from warehouse or donor stores, sorted by potential revenue loss ($\text{velocity} \times \text{MRP}$).
  - `AGEING_RISK`: store $\times$ SKU where `is_core_style == 0`, age $> 90\text{ days}$, and cover $> 60\text{ days}$.
  - `ZERO_SALES_DIAGNOSIS`: flag zero-sales items with explicit reason: `"no stock"` vs `"no demand"`.

### Acceptance criteria
- **AC-1 (REQ-1):** On any SKU that suffered a stockout (`days_in_stock < 7` in a sales week), the calculated velocity is verified to be strictly higher than $\frac{\text{sales}}{7}$.
- **AC-2 (REQ-3):** `BLR-05` has non-zero peer-derived velocities matching its Tier A Bangalore peer baseline.
- **AC-3 (REQ-4, 5):** Effective stock and cover days accurately reflect in-transit units.
- **AC-4 (REQ-7):** Every zero-sales SKU is accurately labeled "no stock" when `days_in_stock == 0` and "no demand" when `days_in_stock > 0`.
- **AC-5 (REQ-7):** Stockout risk findings are sorted in descending order of potential revenue loss.

### Edge cases & failure modes
- **Division by Zero:** Stores with 0 days in stock and 0 sales safely yield 0.0 velocity.
- **Infinite Cover:** SKUs with stock but zero velocity are capped at 999.0 days cover to prevent overflow.
- **Orphan / Discontinued SKUs:** Handled safely with 0 velocity and 0 cover.

### Assumptions & open questions
- As-of date is `2026-10-31`.
- Weekly history window spans the 12 weeks provided in `stock_weekly.csv`.

## 2. Plan
_To be written after Gate 1 approval._

## 3. Tasks
_To be written after Gate 1 approval._
