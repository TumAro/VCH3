# Spec Memory: Track 2 Velocity & Cover Intelligence Engine
- Spec: `docs/spec/feature-velocity-cover-001.md`
- Implemented: 2026-11-21

## 1. Summary of steps taken
- Added immutable Track 2 result models and `FindingType` in `src/velocity_cover/models.py`.
- Added a repository protocol in `src/velocity_cover/repositories.py` over the existing Track 1 store, item, stock, sales, and rules repositories.
- Implemented 12-week stockout-aware store-SKU velocity, peer fallback, and style/category rollups in `src/velocity_cover/velocity_service.py`.
- Implemented effective stock, three-state cover calculation, and stock age in `src/velocity_cover/position_cover_service.py`.
- Implemented stockout, ageing, and zero-sales findings in `src/velocity_cover/problem_detection_service.py`.
- Added fixed-order pipeline assembly in `src/velocity_cover/pipeline.py`.
- Added focused unit and real-repository integration tests in `tests/test_velocity_cover.py`.

## 2. Decisions & rationale
- Sales quantities come from clean bill lines in the 12-week window; denominators come from `stock_weekly.days_in_stock`, preserving stockout-aware velocity.
- Style and category rollups sum quantity sold and stock days before dividing, avoiding arithmetic averages of SKU velocities.
- New-store fallback uses the existing `is_new_store` domain flag, exact city/tier peers first, then closest Bengaluru tiers A, S+, S++, and finally city-wide established peers.
- The 999.0 value is retained explicitly for zero-velocity positive-stock positions instead of converting it to an unbounded float.
- Findings remain data-only at this stage; presentation and move generation consume later pipeline tracks.

## 3. Deviations from the spec
- The original peer tier order in the spec did not mention Tier A fallback explicitly. BLR-05 is Tier B; implementation follows the approved order: exact tier, Tier A, Tier S+, Tier S++, then city-wide established peers.
- Sales-positive plus zero stock-days is not emitted as a guessed velocity; it returns 0.0 rather than inventing a denominator. This follows the safe division behavior while the spec only defines sales-zero plus zero-days.

## 4. Verification evidence
- `python3 -m pytest tests/test_ingestion.py tests/test_velocity_cover.py -q`
- Result: `15 passed in 3.76s`
- `python3 -m compileall -q src tests`
- Result: no compile errors.
- Real-repository pipeline verification:
  - 96 BLR-05 SKU velocities, 88 non-zero, 96 peer-derived.
  - 3,405 trusted inventory positions.
  - 3 stockout findings, 1,234 ageing findings, 2,986 zero-sales findings.

## 5. Failures & dead ends
- Initial stockout test fixture used one weekly row, which incorrectly classified the synthetic store as a new store fallback under the store-level `is_new_store` rule. Changed the fixture to represent established 12-week history and reran successfully.
- Initial BLR-05 assertion expected `(4/84 + 6/84)` rather than an arithmetic mean. Corrected the expected value to `((4/84 + 6/84) / 2)`.

## 6. Known issues & follow-ups
- The repository currently has no persisted sales window config separate from `stock_weekly`; the window is derived dynamically from the distinct weekly dates.
