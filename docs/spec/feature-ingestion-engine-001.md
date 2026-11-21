# Track 1: Data Ingestion & Repository Layer
- Status: Implemented
- Created: 2026-11-21

## 1. Spec

### Goal & context
Build the data ingestion, sanitization, and repository layer for the Daily Stock Move Recommender. This layer reads all 10 tabular CSV datasets from `data/csv/`, enforces strict data types and schema validation, excludes non-product packaging SKUs, quarantines malformed or untrusted records into a structured `DataIssueLog`, and populates an in-memory repository implementing clean domain interfaces. It serves as the trusted foundation for Tracks 2, 3, and 4.

### Scope

**In Scope:**
- Ingesting 10 tabular CSVs from `data/csv/`: `stores`, `items`, `bills`, `bill_lines`, `stock_snapshot`, `stock_weekly`, `warehouse_inbound`, `rules`, `min_display`, `lead_times`, and `flagship_protected`.
- Type casting: all ID columns parsed strictly as strings (preserving leading zeroes), dates parsed as `YYYY-MM-DD`, and numeric columns cast explicitly.
- Filtering out packaging SKUs (`is_packaging = 1` or ₹0 MRP packaging materials) across all sales, stock, and item tables.
- Quarantine and issue logging: detecting negative stock, snapshot versus weekly closing mismatches, and store physical capacity breaches, logging them in a structured `DataIssueLog` without halting pipeline execution.
- Defining immutable domain models (`Store`, `Item`, `StockSnapshot`, `WeeklyStock`, `LeadTime`, `Rule`, `DataIssue`) and repository interfaces (`IStoreRepository`, `IItemRepository`, `IStockRepository`, `ISalesRepository`, `IRulesRepository`).
- Implementing an in-memory repository with O(1) dictionary and indexed lookups by store ID, SKU ID, style ID, and category.
- Providing an idempotent `sync()` method allowing the engine to reload data from the source directory on demand.

**Explicitly Out of Scope:**
- Velocity and cover calculations (Track 2).
- Problem detection and findings generation (Track 2).
- Move generation and constraint validation (Track 3).
- Web UI, REST endpoints, and spreadsheet export (Track 4).
- Modifying the raw CSV files on disk.

### Requirements
- **REQ-1:** Ingest the 10 source CSV tables from `data/csv/` using an adapter pattern (`CSVDataSourceAdapter`).
- **REQ-2:** Retain all entity identifiers (`store_id`, `sku_id`, `bill_id`, `salesperson_id`, `style_id`) as strings, and parse all dates as `YYYY-MM-DD`.
- **REQ-3:** Strip all packaging items (`is_packaging = 1`: `PKG-BAG`, `PKG-COVER`, `PKG-BOX`) from item definitions, sales lines, and inventory positions.
- **REQ-4:** Maintain a structured `DataIssueLog` where each anomaly records: `table`, `key`, `column`, `value_seen`, `rule_violated`, and `action_taken`.
- **REQ-5:** Quarantine known invalid stock rows:
  - Negative on-hand units (e.g. `KUR-02-M` at `MYS-02` with on-hand `-4`).
  - Discrepancy between `stock_snapshot.on_hand` and `stock_weekly.closing_on_hand` at 31 Oct 2026 (e.g. `SHW-02-L` at `KNP-03`).
  - Store total on-hand exceeding physical `stock_capacity_units`.
  Quarantined rows must be marked as untrusted and excluded from downstream stock-move candidate generation.
- **REQ-6:** Expose an `InMemoryRepository` implementing standard interfaces with typed retrieval methods:
  - `get_stores()` -> list of `Store`
  - `get_store(store_id)` -> `Store`
  - `get_items()` -> list of `Item`
  - `get_item(sku_id)` -> `Item`
  - `get_snapshot_positions()` -> list of `StockPosition`
  - `get_weekly_stock(store_id, sku_id)` -> list of `WeeklyStock`
  - `get_clean_sales_lines()` -> list of `SalesLine`
  - `get_lead_times_matrix()` -> dict of transit days
  - `get_min_display(tier, category)` -> int
  - `get_flagship_protected(store_id)` -> set of `style_id`
  - `get_data_issues()` -> list of `DataIssue`

### Acceptance criteria
- **AC-1 (REQ-1, 2):** Ingestion loads exactly 20 stores, 382 non-packaging SKUs, and all associated bills, stock, and rules. String IDs retain formatting.
- **AC-2 (REQ-3):** Zero packaging SKUs exist in domain items, sales lines, or stock positions.
- **AC-3 (REQ-4, 5):** `KUR-02-M` at `MYS-02` and `SHW-02-L` at `KNP-03` are captured in `DataIssueLog` with all 6 required fields, flagged as untrusted, and never returned as movable inventory.
- **AC-4 (REQ-6):** All repository lookup methods return typed dataclasses and execute in $< 1\text{ ms}$ per call.

### Edge cases & failure modes
- **Missing CSV File or Column:** Ingestion fails fast with a descriptive `DataIngestionError` detailing the missing resource.
- **Un-joinable Foreign Keys:** Sales lines with an unknown SKU or store are recorded in the issue log and discarded from clean sales lines.
- **New Store BLR-05:** Loaded with its opening date `2026-10-10` and flagged as `is_new_store = True` ($< 28\text{ days}$ history).

### Assumptions & open questions
- Source directory defaults to `data/csv/`.
- Snapshot as-of date is fixed at `2026-10-31`.

## 2. Plan

### Files and components to add or change
- `src/domain/models.py`: Defines immutable domain models (`Store`, `Item`, `StockPosition`, `WeeklyStock`, `SalesLine`, `WarehouseInbound`, `LeadTimeRule`, `DataIssue`).
- `src/domain/repositories.py`: Defines abstract interfaces (`IStoreRepository`, `IItemRepository`, `IStockRepository`, `ISalesRepository`, `IRulesRepository`) following the Repository Design Pattern.
- `src/infrastructure/csv_adapter.py`: Implements `CSVDataSourceAdapter` to parse CSVs, enforce string IDs, parse ISO dates, drop packaging SKUs (`is_packaging = 1`), and quarantine untrusted records into `DataIssueLog`.
- `src/infrastructure/in_memory_repository.py`: Implements the abstract repository interfaces using fast in-memory dictionary and set indices. Provides a `sync()` method for on-demand re-ingestion.
- `tests/test_ingestion.py`: Comprehensive test suite verifying entity counts, string formatting, packaging exclusion, quarantine logic, and retrieval speeds.

### Data models, interfaces, and contracts
- Domain Models:
  - `Store`: `store_id: str`, `city: str`, `state: str`, `zone: str`, `tier: str`, `stock_capacity_units: int`, `opened_on: date`, `is_new_store: bool`
  - `Item`: `sku_id: str`, `style_id: str`, `style_name: str`, `category: str`, `size: str`, `mrp: float`, `cost_price: float`, `launch_date: Optional[date]`, `is_core_style: bool`
  - `StockPosition`: `location_id: str`, `sku_id: str`, `on_hand: int`, `in_transit: int`, `in_transit_arrives_on: Optional[date]`, `oldest_stock_received_on: Optional[date]`, `is_untrusted: bool`
  - `WeeklyStock`: `week_ending: date`, `store_id: str`, `sku_id: str`, `closing_on_hand: int`, `days_in_stock: int`
  - `SalesLine`: `bill_id: str`, `bill_date: date`, `store_id: str`, `salesperson_id: str`, `sku_id: str`, `qty: int`, `mrp: float`, `selling_price: float`
  - `WarehouseInbound`: `expected_date: date`, `sku_id: str`, `qty: int`, `status: str`
  - `LeadTimeRule`: `route: str`, `days: int`
  - `DataIssue`: `table: str`, `key: str`, `column: str`, `value_seen: str`, `rule_violated: str`, `action_taken: str`
- Repository Interfaces:
  - `IStoreRepository`, `IItemRepository`, `IStockRepository`, `ISalesRepository`, `IRulesRepository`.

### Dependencies
- Standard library modules only: `csv`, `dataclasses`, `datetime`, `pathlib`, `typing`, `logging`. Zero third-party dependencies required for this layer, ensuring maximum portability, speed, and zero build fragility.

### Risks and trade-offs
- **Memory footprint**: Loading ~260,000 sales lines and ~61,000 weekly rows into Python dataclasses takes approximately 35 MB of RAM, well within limits.
- **Quarantine safety**: Quarantined records must remain accessible for data auditing (`get_data_issues()`) but explicitly excluded from active inventory positions used for move generation.

### Test strategy
- Unit test suite in `tests/test_ingestion.py`:
  - `test_store_loading`: Verifies 20 stores loaded, string IDs preserved, `BLR-05` tagged as `is_new_store = True` (REQ-1, REQ-2, REQ-3, AC-1).
  - `test_packaging_exclusion`: Verifies 382 non-packaging items loaded and 0 packaging SKUs in items, sales, or stock (REQ-3, AC-2).
  - `test_quarantine_negative_stock`: Verifies `KUR-02-M` at `MYS-02` is flagged untrusted in `DataIssueLog` (REQ-4, REQ-5, AC-3).
  - `test_quarantine_snapshot_mismatch`: Verifies `SHW-02-L` at `KNP-03` is flagged untrusted in `DataIssueLog` (REQ-4, REQ-5, AC-3).
  - `test_repository_performance`: Verifies ID lookups execute in $< 1\text{ ms}$ (REQ-6, AC-4).
  - `test_missing_file_error`: Verifies clear `DataIngestionError` raised on missing file.

## 3. Tasks

- [x] 1. Define immutable domain models in `src/domain/models.py` (`Store`, `Item`, `StockPosition`, `WeeklyStock`, `SalesLine`, `WarehouseInbound`, `LeadTimeRule`, `DataIssue`). Satisfies: REQ-2, REQ-4. Done when: `python -c "import src.domain.models"` executes without error and exports all models.
- [x] 2. Define abstract repository interfaces in `src/domain/repositories.py` (`IStoreRepository`, `IItemRepository`, `IStockRepository`, `ISalesRepository`, `IRulesRepository`). Satisfies: REQ-6. Done when: `python -c "import src.domain.repositories"` executes without error and exports all interfaces.
- [x] 3. Implement `CSVDataSourceAdapter` in `src/infrastructure/csv_adapter.py` to ingest 10 CSV tables, enforce string IDs, parse ISO dates, drop packaging SKUs, and populate `DataIssueLog` for untrusted records. Satisfies: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5. Done when: Adapter parses CSV directory and outputs sanitized raw structures and issue log.
- [x] 4. Implement `InMemoryRepository` in `src/infrastructure/in_memory_repository.py` holding indexed dictionaries for stores, items, stock positions, weekly stock, sales, and rules, with a callable `sync()` method. Satisfies: REQ-6. Done when: All repository interface methods are implemented and return typed records in $< 1\text{ ms}$.
- [x] 5. Implement automated test suite in `tests/test_ingestion.py` verifying all acceptance criteria (AC-1 through AC-4 and edge cases). Satisfies: AC-1, AC-2, AC-3, AC-4. Done when: `pytest tests/test_ingestion.py` runs and all tests pass with 100% success.
