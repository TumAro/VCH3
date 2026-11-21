# Feature: Pipeline Bridge & Move Integration
- Status: Implemented
- Created: 2026-11-21

## 1. Spec

### Goal & context
Connect the four independently developed tracks into a unified end-to-end stock move recommender. The bridge adapts Track 1 repository data and Track 2 velocity/cover analytics into Track 3's `EngineInputs`, executes the `MoveEngine` to generate rule-compliant stock moves, stores the unified state in `DataContext`, and exposes the moves, problem findings, summary KPIs, approval actions, and CSV/Excel exports via FastAPI endpoints and a headless CLI runner.

### Scope

**In Scope:**
- **Pipeline Adapter:** Build an adapter function that maps Track 1 domain entities (`Store`, `Item`, `StockPosition`) and Track 2 analytics (`VelocityCoverResult`: SKU velocity, style velocity, style cover, position cover) into Track 3's `EngineInputs`.
- **End-to-End Orchestration:** Execute `MoveEngine().run(engine_inputs)` on real `data/csv/` datasets, producing approved moves, rejected candidate logs, and unfulfilled deficits.
- **Data Context Integration:** Update `LoadedData` and `DataContext` in `src/api/data_context.py` to compute and retain the move engine results, findings, and operational summary KPIs across startup and `POST /api/sync` re-runs.
- **REST Endpoints:** Expose the complete move dataset to the web dashboard via FastAPI:
  - `GET /api/moves`: returns ranked moves with query parameter filters (move type, store, category, decision, search query).
  - `POST /api/moves/{move_id}/decision`: toggles a move's status between `Approved` and `Rejected`.
  - `GET /api/findings`: returns detected problem pockets (stockout risks, ageing fashion traps, zero-sales classifications).
  - `GET /api/moves/summary`: returns high-level metrics (total moves, total units, total MRP value, stockout SKU count).
  - `GET /api/export/csv`: downloads the active approved move list as a standard CSV file.
  - `GET /api/export/xlsx`: downloads a multi-tab Excel workbook containing *Moves*, *Findings*, and *Rejected Moves* sheets.
- **Headless CLI Entry Point:** Implement `python -m src.cli` to execute the pipeline headlessly and write `moves.csv` and `moves.xlsx` to disk in under 30 seconds.
- **Real-Data Safety Verification:** Automated test running the independent validator on the actual real-data move recommendations to prove zero rule violations.

**Explicitly Out of Scope:**
- Modifying the underlying algorithms in `src/velocity_cover/` or `src/moves/`.
- Changing raw CSV files in `data/csv/`.
- Reworking UI styles or layout in `src/web/`.

### Requirements

#### Adapter & Pipeline Assembly
- **REQ-1:** Provide a bridge function `build_engine_inputs(repo: InMemoryRepositoryContainer, vc: VelocityCoverResult) -> EngineInputs`:
  - Maps Track 1 `Store` objects to Track 3 `Store` tuples.
  - Maps Track 1 `Item` objects to Track 3 `Item` tuples.
  - Maps Track 1 `StockPosition` objects to Track 3 `Position` tuples, marking quarantined rows with `quarantined = True`.
  - Maps Track 2 `sku_velocity` dictionary to `(store_id, sku_id) -> float`.
  - Maps Track 2 `style_velocity` dictionary to `(store_id, style_id) -> float`.
  - Maps Track 2 style cover dictionary to `(store_id, style_id) -> Optional[float]`.
  - Maps Track 1 min display rules and flagship protected style sets.
- **REQ-2:** Execute the full pipeline sequentially:
  1. Ingestion (`InMemoryRepositoryContainer`).
  2. Velocity & Cover (`VelocityCoverPipeline.run()`).
  3. Adapter mapping (`build_engine_inputs`).
  4. Move Generation & Validation (`MoveEngine.run()`).
  All steps must execute within 15 seconds on the provided 24-month dataset.

#### Context & State Management
- **REQ-3:** Extend `LoadedData` in `src/api/data_context.py` to retain:
  - `moves: List[ApprovedMove]`
  - `findings: List[Finding]`
  - `rejected_moves: List[RejectedMove]`
  - `unfulfilled_deficits: List[UnfulfilledDeficit]`
  - `summary: MoveSummary`
- **REQ-4:** Maintain in-memory approval decisions: allow the user to toggle an individual move between `Approved` and `Rejected`. Decisions must persist across filter queries until a fresh `POST /api/sync` re-run is executed.

#### API Endpoints
- **REQ-5:** Provide `GET /api/moves` accepting query filters:
  - `move_type`: filter by `Warehouse to store` or `Store to store`.
  - `store_id`: filter by destination or origin store.
  - `category`: filter by product category.
  - `decision`: filter by `Approved`, `Rejected`, or `Waiting`.
  - `search`: free-text search across SKU, style name, origin city, destination city.
- **REQ-6:** Provide `POST /api/moves/{move_id}/decision` accepting `{"decision": "Approved" | "Rejected"}`.
- **REQ-7:** Provide `GET /api/findings` returning the structured problem findings categorized by `STOCKOUT_RISK`, `AGEING_RISK`, and `ZERO_SALES_DIAGNOSIS`.
- **REQ-8:** Provide `GET /api/moves/summary` returning total proposed moves count, total units, total MRP value, and count of SKUs requiring human sign-off ($> ₹1,00,000$).
- **REQ-9:** Provide export endpoints:
  - `GET /api/export/csv`: streams `moves.csv`.
  - `GET /api/export/xlsx`: streams `moves.xlsx` with three sheets: *Moves*, *Findings*, *Rejected Moves*. Excludes moves flagged as `Rejected` from the primary *Moves* sheet.

#### CLI & Automation
- **REQ-10:** Provide a CLI entry point runnable via `python -m src.cli` that runs the full pipeline from `data/csv/`, writes `moves.csv` and `moves.xlsx` to the root directory, and logs execution statistics.

### Acceptance Criteria & Integration Test Suite

- **AC-1 (Bridge Transformation Test):**
  - `test_bridge_adapter_on_real_data`: Verifies that `build_engine_inputs` converts the full repository without missing key errors. Asserts 20 stores, 382 items, non-empty position tuples, correct flag on quarantined positions (`KUR-02-M` at `MYS-02` and `SHW-02-L` at `KNP-03`), and valid velocity/cover mappings.
- **AC-2 (Move Engine Real-Data Execution Test):**
  - `test_move_engine_real_data_execution`: Runs `MoveEngine().run(engine_inputs)` on real data. Asserts:
    - Pipeline completes in $< 15\text{ seconds}$.
    - Approved moves list is non-empty and contains both Warehouse-to-Store and Store-to-Store moves.
    - Every approved move contains a deterministic data-backed reason string.
- **AC-3 (Zero Rule Violations Independent Validator Test):**
  - `test_zero_rule_violations_on_real_moves`: Passes 100% of generated real approved moves to `IndependentValidator` from `tests/moves/independent_validator.py`. Asserts `find_violations(real_moves) == []` across all 6 hard constraints.
- **AC-4 (High-Value Approval Threshold Test):**
  - `test_approval_threshold_compliance`: Confirms that for 100% of real moves, `requires_human_approval == True` if and only if $\text{qty} \times \text{MRP} > 1,00,000$.
- **AC-5 (DataContext & Decision State Test):**
  - `test_data_context_moves_integration`: Verifies that `DataContext` populates moves, findings, and summaries on startup. Toggling a move to `Rejected` updates state; re-running via `rerun()` cleanly reloads state thread-safely.
- **AC-6 (REST API Endpoints Test):**
  - `test_api_endpoints_integration`: Using FastAPI `TestClient`, tests:
    - `GET /api/moves` with filters (`move_type`, `store_id`, `category`, `decision`, `search`).
    - `POST /api/moves/{id}/decision` updates approval state and returns HTTP 200.
    - `GET /api/findings` returns all three finding categories.
    - `GET /api/moves/summary` returns accurate KPI aggregates.
- **AC-7 (Export Streaming Test):**
  - `test_export_csv_and_xlsx_integration`: Verifies `GET /api/export/csv` streams valid CSV headers/rows, and `GET /api/export/xlsx` streams a valid Excel workbook with sheets *Moves*, *Findings*, and *Rejected Moves*. Moves marked `Rejected` are omitted from the active *Moves* sheet.
- **AC-8 (CLI End-to-End Runner Test):**
  - `test_cli_runner_execution`: Executes `python -m src.cli`, asserts exit code 0, verifies `moves.csv` and `moves.xlsx` exist on disk, contain valid data, and run completes in $< 30\text{ seconds}$.

### Edge cases & failure modes
- **Zero Viable Moves:** If inventory is fully balanced or donors are unavailable, the engine returns empty approved moves and logs unfulfilled deficits without crashing.
- **Concurrent Re-runs:** Thread-safe state swap ensures an in-flight API query never observes partial or corrupted pipeline data during a sync re-run.

### Assumptions & open questions
- As-of date is fixed at `2026-10-31`, dispatch date is `2026-11-01`.
- Move ID is deterministically indexed as `{move_type}_{from}_{to}_{sku_id}` or integer index `1..N`.

## 2. Plan

### Files and components to add or change
- `src/services/bridge.py`: Adapter function `build_engine_inputs(repo: InMemoryRepositoryContainer, vc: VelocityCoverResult) -> EngineInputs` mapping Track 1 and Track 2 models to Track 3's `EngineInputs`.
- `src/services/export_service.py`: Generates `moves.csv` and multi-tab `moves.xlsx` (*Moves*, *Findings*, *Rejected Moves*) using `openpyxl` and standard library `csv`.
- `src/api/data_context.py`: Extends `LoadedData` and `DataContext` to orchestrate Track 2 and Track 3, retain moves, findings, rejected moves, unfulfilled deficits, and summary statistics, and provide decision toggling.
- `src/api/app.py`: Implements REST endpoints: `/api/moves`, `/api/moves/{move_id}/decision`, `/api/findings`, `/api/moves/summary`, `/api/export/csv`, `/api/export/xlsx`.
- `src/cli.py`: Headless CLI entry point executing the full pipeline and outputting `moves.csv` and `moves.xlsx`.
- `tests/test_integration_pipeline.py`: Comprehensive test suite implementing all 8 acceptance tests (AC-1 through AC-8).

### Data models, interfaces, and contracts
- `MoveDecisionRecord`: Tracks move ID, move payload, decision state (`Waiting`, `Approved`, `Rejected`), and update timestamp.
- `MoveSummary`: Dataclass holding total proposed moves, total units, total MRP value, and count of moves requiring human approval.
- Bridge translation contract:
  - `src.domain.models.Store` $\to$ `src.moves.inputs.Store(store_id, city, zone, tier, stock_capacity_units)`
  - `src.domain.models.Item` $\to$ `src.moves.inputs.Item(sku_id, style_id, category, int(round(mrp)))`
  - `src.domain.models.StockPosition` $\to$ `src.moves.inputs.Position(location_id, sku_id, on_hand, in_transit, quarantined)`
  - `sku_velocity` mapping from Track 2 `DailyVelocity`
  - `style_velocity` and `style_cover` mapping from Track 2 aggregates
  - Flagship set mapping `frozenset((store_id, style_id))`
  - Min display mapping `(tier, category) -> units` (with Accessories aggregated)

### Dependencies
- `fastapi`, `uvicorn`, `openpyxl`. `openpyxl` is installed for Excel export. Zero other new dependencies.

### Risks and trade-offs
- **Performance**: Executing Track 2 and Track 3 takes ~3.5 seconds. Caching results in `DataContext` guarantees sub-second response times for all API queries.
- **Decision Persistence**: Approval toggles are stored in an in-memory dictionary inside `DataContext`, persisting across tab switches and UI filtering.

### Test strategy
- Real-data integration tests in `tests/test_integration_pipeline.py`:
  - `test_bridge_adapter_on_real_data`: AC-1
  - `test_move_engine_real_data_execution`: AC-2
  - `test_zero_rule_violations_on_real_moves`: AC-3
  - `test_approval_threshold_compliance`: AC-4
  - `test_data_context_moves_integration`: AC-5
  - `test_api_endpoints_integration`: AC-6
  - `test_export_csv_and_xlsx_integration`: AC-7
  - `test_cli_runner_execution`: AC-8

## 3. Tasks

- [x] 1. Implement `src/services/bridge.py` mapping Track 1 (`InMemoryRepositoryContainer`) and Track 2 (`VelocityCoverResult`) to Track 3's `EngineInputs`. Satisfies: REQ-1. Done when: `test_bridge_adapter_on_real_data` passes.
- [x] 2. Implement `src/services/export_service.py` to write `moves.csv` and multi-tab `moves.xlsx` (*Moves*, *Findings*, *Rejected Moves*). Satisfies: REQ-9. Done when: Export service outputs valid CSV and Excel files.
- [x] 3. Update `src/api/data_context.py` to run `VelocityCoverPipeline` and `MoveEngine`, cache move results, findings, and summaries, and provide `set_decision(move_id, decision)`. Satisfies: REQ-2, REQ-3, REQ-4. Done when: `test_data_context_moves_integration` passes.
- [x] 4. Update `src/api/app.py` adding endpoints `/api/moves`, `/api/moves/{id}/decision`, `/api/findings`, `/api/moves/summary`, `/api/export/csv`, `/api/export/xlsx`. Satisfies: REQ-5, REQ-6, REQ-7, REQ-8, REQ-9. Done when: `test_api_endpoints_integration` passes.
- [x] 5. Implement `src/cli.py` headless CLI runner producing `moves.csv` and `moves.xlsx` in $< 30\text{ seconds}$. Satisfies: REQ-10. Done when: `python -m src.cli` executes successfully and writes files to disk.
- [x] 6. Implement automated integration test suite in `tests/test_integration_pipeline.py` verifying all 8 acceptance criteria (AC-1 to AC-8), including zero rule violations on real data. Satisfies: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8. Done when: `python -m pytest tests/test_integration_pipeline.py` passes 100%.
