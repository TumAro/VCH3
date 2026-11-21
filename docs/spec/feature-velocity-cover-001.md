# Track 2: Velocity & Cover Intelligence Engine
- Status: Implemented
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
### Implementation approach
- Add a dedicated Track 2 package under `src/velocity_cover/` for immutable result models, repository-backed calculation services, typed findings, and an application entry point used by later tracks.
- Keep CSV parsing and data quarantine outside this track. The services will consume the typed repository contracts defined by `docs/spec/feature-ingestion-engine-001.md` and will exclude snapshots or weekly rows that Track 1 marks untrusted.
- Represent one SKU result for one store with one record containing daily velocity, effective stock, cover days, stock age, and zero-sales diagnosis. Represent style and category rollups as separate aggregate records keyed by store and style/category.
- Use a protocol-oriented service boundary so unit tests use fake repositories and do not require a database or filesystem.

### Data model and contracts
- Add domain values for `DailyVelocity`, `InventoryPosition`, `Finding`, and `FindingType` under `src/velocity_cover/models.py`.
- `Finding` will use a discriminated `finding_type` field with `STOCKOUT_RISK`, `AGEING_RISK`, or `ZERO_SALES_DIAGNOSIS`, plus store, SKU, style, metric, diagnosis, and optional MRP/revenue-loss fields.
- Add repository-facing read methods to `VelocityCoverRepository` under `src/velocity_cover/repositories.py`:
  - store and item lookups;
  - trusted snapshot positions;
  - 12-week `WeeklyStock` rows;
  - clean sales quantities for the matching 12-week window;
  - route lead times.
- The existing Track 1 repository remains the source of truth for packaging exclusion and untrusted-row filtering. Track 2 will not silently reinterpret quarantined positions or packaging rows.

### Formula implementation
- Define the 12-week sales window from the 12 `stock_weekly.week_ending` dates. Sum bill-line quantity for each store and SKU in the corresponding 12-week window, join it to the sum of `days_in_stock` for the same store and SKU.
- Compute `velocity = total_quantity_sold / total_days_in_stock` when the denominator is positive. For `denominator == 0` and sales zero, return `0.0`; the spec has no sales-positive/zero-days result, so that row is rejected into an explicit validation issue rather than guessed.
- Roll up store SKU velocities to style and category using sum of SKU quantity sold divided by sum of corresponding SKU stock days, not an average of SKU velocities. This preserves the stockout-aware meaning of the rollup.
- Mark `BLR-05` and every store with fewer than 28 days of usable 12-week history as new. For a missing store-SKU baseline, use established peers in the same city, preferring the closest tier in this order: exact tier, S+, S++, then city-wide established stores. For BLR-05 Tier B, the first available Tier-S+ peer group is used. A SKU may only enter the fallback mean if it has a positive usable denominator in each included peer store; record a zero only for true denominator-zero/sales-zero results.
- Compute effective stock only for trusted, non-packaging snapshot rows as `on_hand + in_transit`.
- Compute cover as stock divided by velocity for positive velocity, `999.0` for zero velocity with positive stock, and `0.0` for zero velocity with zero stock.
- Use `2026-10-31` as the fixed as-of date and return age 0 for missing or null `oldest_stock_received_on`.
- Use the warehouse route from the store zone for low-cover findings. When a route lead-time lookup is unavailable, no stockout finding is emitted and the missing route is logged.

### Finding rules
- Create `STOCKOUT_RISK` findings for trusted store-SKU positions whose cover is below the applicable warehouse/store lead time. Sort descending by `velocity * item.mrp`, then store ID, then SKU ID for deterministic ties.
- Create `AGEING_RISK` for non-core styles where age is greater than 90 days and cover is greater than 60 days.
- Create `ZERO_SALES_DIAGNOSIS` for every zero-sales SKU, using `no stock` when total `days_in_stock == 0` and `no demand` when total `days_in_stock > 0`.

### Files and components
- `src/velocity_cover/models.py`: immutable domain values and finding type.
- `src/velocity_cover/repositories.py`: repository-facing protocol and aggregate data structures.
- `src/velocity_cover/velocity_service.py`: store-SKU velocity, peer fallback, and style/category rollups.
- `src/velocity_cover/position_cover_service.py`: effective stock, cover, and stock-age calculations.
- `src/velocity_cover/problem_detection_service.py`: stockout, ageing, and zero-sales findings.
- `src/velocity_cover/pipeline.py`: fixed dependency order and deterministic result assembly for later CLI/API tracks.
- `tests/test_velocity_cover.py`: formulas, rollups, fallback, cover, age, findings, sorting, and orphan/invalid edge cases.

### Dependencies
- No new third-party package is required. Use the Python standard library and typed dataclasses to match the repository pattern already described by the architecture.
- The implementation depends on Track 1 repository output. Because no Track 1 implementation is present in the repository, the first implementation task will require a test fake and the integration seam; the CSV-backed adapter remains a Track 1 deliverable rather than a velocity-track shortcut.

### Risks and mitigations
- The spec's sales denominator source is ambiguous because `stock_weekly.csv` contains no quantity-sold column. Mitigation: use the quantity numerator from clean bill lines and the stockout denominator from `stock_weekly`, with tests proving both joins.
- The peer fallback has no exact Tier B Bengaluru peer. Mitigation: use the user-approved nearest-tier policy, then city-wide fallback, and expose peer IDs/baselines in result data for auditability.
- Aggregating style/category values incorrectly could produce averages that overweight SKUs. Mitigation: aggregate totals of sales and stock days before division.
- A 999.0 cover sentinel can be mistaken for real age or route lead time. Mitigation: keep the sentinel explicit in the model and sort/filter rules before presentation logic.
- Snapshot mismatch and negative stock are handled upstream. Mitigation: Track 2 rejects only records reported as untrusted and never performs ad hoc quarantine.

### Test strategy
- `REQ-1/AC-1`: synthetic stockout week with 4 sales and 3 available days returns a velocity higher than 4/7 and a weekly denominator sum of 3.
- `REQ-1`: zero-sales/zero-days rows return 0.0; invalid sales-positive/zero-days rows do not produce a silent velocity.
- `REQ-2`: verify a style/category rollup by independently summing sales and stock days, including more than one SKU.
- `REQ-3/AC-2`: verify BLR-05 receives the arithmetic mean of established Bengaluru S+ peers (BLR-03 and BLR-04) for the selected SKU; if absent, follow the documented tier/city fallbacks.
- `REQ-4/5/AC-3`: verify on-hand plus in-transit effective stock and all three cover branches, including 999.0.
- `REQ-6`: verify age on 2026-10-31, including null/missing date returns 0.
- `REQ-7/AC-4/5`: verify no-stock/no-demand labels and descending potential-loss sort with deterministic tie-breaking.
- Integration: run the pipeline against a fake repository populated from the supplied CSV-shaped fixtures and verify packaging/untrusted records never enter the result set.

## 3. Tasks
- [x] 1. Add Track 2 typed result and repository contracts (REQ-1 through REQ-7).
  - Done when: `src/velocity_cover/models.py` and `src/velocity_cover/repositories.py` define immutable, testable types and protocols, and no service performs direct CSV or database access.
- [x] 2. Implement the 12-week stockout-aware velocity formula and store-SKU rollups (REQ-1, REQ-2).
  - Done when: quantity totals are joined to stock-day totals, positive denominators divide strictly, zero denominator with zero sales returns 0.0, style/category totals divide aggregated sales by aggregated stock days, and the REQ-1 tests pass.
- [x] 3. Implement new-store peer fallback for BLR-05 (REQ-3).
  - Done when: stores with fewer than 28 days of usable history use the arithmetic mean of established peers in exact city/tier first, then S+, S++, and city-wide fallback; deterministic baseline evidence is retained and REQ-3 tests pass.
- [x] 4. Implement effective stock, cover, and stock-age calculations (REQ-4, REQ-5, REQ-6).
  - Done when: trusted non-packaging positions add on-hand and in-transit stock, cover uses all three REQ-5 branches, null/missing receipt dates yield age 0, and the corresponding tests pass.
- [x] 5. Implement typed problem findings and zero-sales diagnosis (REQ-7).
  - Done when: stockout, ageing, and zero-sales results use `Finding` records, zero-sales reasons are exact, and no packaging or untrusted position is emitted.
- [x] 6. Add deterministic finding ranking and lead-time lookup (REQ-7).
  - Done when: stockout findings are sorted by descending `velocity * MRP`, then store ID, then SKU ID; zone/city routes are derived centrally; missing routes are reported without emitting an assumed finding.
- [x] 7. Assemble the Track 2 pipeline (REQ-1 through REQ-7).
  - Done when: `src/velocity_cover/pipeline.py` runs repositories -> velocity -> position/cover -> findings in fixed order and returns a reproducible result set.
- [x] 8. Add and run focused unit/integration verification (AC-1 through AC-5).
  - Done when: fake-repository tests cover stockout-aware math, BLR-05 fallback, in-transit cover, age, zero-sales labels, finding sorting, orphan inputs, and all test/build checks report passing.
