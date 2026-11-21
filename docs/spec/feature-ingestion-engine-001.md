# Track 1: Data Ingestion & Repository Layer
- Status: Draft
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
_To be written after Gate 1 approval._

## 3. Tasks
_To be written after Gate 1 approval._
