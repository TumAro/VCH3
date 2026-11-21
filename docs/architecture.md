# Daily Stock Move Recommender & Dashboard: System Architecture

## 1. System Overview

The Daily Stock Move Recommender is an enterprise decision-support platform designed for Vedant Fashions (Manyavar). The system automates daily inventory rebalancing across 20 retail stores and 1 central warehouse (`WH-KOL`).

Its primary objective is to evaluate daily sales velocity and current inventory positions, isolate stockout risks and surplus ageing pockets, generate legally valid stock transfers (Warehouse $\to$ Store and Store $\to$ Store), and present an auditable, ranked proposal list to a merchandiser for review within a 10-minute approval window.

---

## 2. Architectural Design Principles

The architecture strictly adheres to three structural paradigms:

1. **Repository Pattern**:
   - High-level business engines (Velocity, Cover, Move Generation, Rule Validation) depend solely on domain abstractions (`IStoreRepository`, `IStockRepository`, `ISalesRepository`, `IRulesRepository`).
   - Data access is isolated behind concrete adapters (`CSVDataSourceAdapter`), allowing underlying data sources to be swapped (e.g. from CSVs to SQL or S3) without modifying domain calculations.
2. **SOLID Principles**:
   - **Single Responsibility (SRP)**: Ingestion, velocity estimation, constraint checking, and presentation are completely decoupled into distinct modules.
   - **Open/Closed (OCP)**: New validation rules or move strategies can be added by implementing standard interfaces without altering the orchestrator.
   - **Liskov Substitution (LSP)**: Repositories and adapters adhere to strict contracts ensuring interchangeability.
   - **Interface Segregation (ISP)**: Clients consume targeted interfaces rather than monolithic data objects.
   - **Dependency Inversion (DIP)**: Core calculation services depend on abstract repository interfaces, not concrete CSV reading operations.
3. **DRY (Don't Repeat Yourself)**:
   - Centralized rule definitions, category mappings (e.g. mapping Safa, Mala, and Stole to Accessories), and lead-time transit matrices ensure zero duplication of domain business logic.

---

## 3. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph DataSources["Data Sources (Configured Storage)"]
        CSV["CSV Files (data/csv/)<br/>stores, items, bills, stock_snapshot,<br/>stock_weekly, rules, lead_times"]
    end

    subgraph IngestionLayer["Ingestion & Hygiene Engine"]
        Adapter["CSVDataSourceAdapter<br/>(implements IDataSourceAdapter)"]
        Hygiene["Hygiene & Sanitization<br/>- Text ID casting<br/>- Date parsing (YYYY-MM-DD)<br/>- Packaging filter (is_packaging = 1)"]
        Ledger["Data Issue Ledger<br/>- Negative stock quarantine<br/>- Snapshot mismatch quarantine"]
    end

    subgraph DomainState["In-Memory Domain Repository Layer"]
        MemRepo["In-Memory Domain Repository<br/>- Store Entities<br/>- Item Entities<br/>- Clean Line-Sales Records<br/>- Stock Positions & In-Transit<br/>- Rules & Lead Time Matrices"]
    end

    subgraph ServiceLayer["Core Calculation & Business Services"]
        VelocitySvc["VelocityService<br/>- Stockout-aware units/day (sales / days_in_stock)<br/>- Peer-store fallback for new stores (BLR-05)"]
        CoverSvc["PositionCoverService<br/>- Effective stock (on-hand + in-transit)<br/>- Cover days (stock / velocity)<br/>- Inventory age tracking"]
        DetectSvc["ProblemDetectionService<br/>- Imminent stockout pockets (cover < lead time)<br/>- Ageing fashion inventory<br/>- Zero-sales diagnosis (no stock vs no demand)"]
        MoveGenSvc["MoveGenerationService<br/>- Warehouse-to-Store allocations (loss-prioritized)<br/>- Store-to-Store rebalancing (surplus to deficit)"]
        ValidateSvc["ConstraintValidationService (Safety Gatekeeper)<br/>- Min display check (donor)<br/>- Physical capacity check (receiver)<br/>- S++ flagship protection check<br/>- 30-day donor cover retention check<br/>- In-transit deduplication<br/>- ₹1,00,000 MRP human-approval flag<br/>- Cumulative batch evaluation pass"]
        ExplainSvc["ExplanationService<br/>- Deterministic data-backed reason templates"]
    end

    subgraph PresentationLayer["Delivery & Presentation Layer"]
        CLI["CLI Entry Point (python -m src.cli)<br/>Generates moves.csv & moves.xlsx"]
        FastAPI["FastAPI Web Server<br/>REST APIs: /api/moves, /api/findings, /api/sync"]
        UI["Web Dashboard (HTML5 / Vanilla JS)<br/>- Ranked 10-minute approval table<br/>- Approve / Reject action toggles<br/>- Findings view<br/>- KPI summary cards<br/>- CSV / Excel export"]
    end

    CSV --> Adapter
    Adapter --> Hygiene
    Hygiene --> Ledger
    Hygiene --> MemRepo

    MemRepo --> VelocitySvc
    MemRepo --> CoverSvc
    VelocitySvc --> CoverSvc
    CoverSvc --> DetectSvc
    CoverSvc --> MoveGenSvc
    DetectSvc --> MoveGenSvc
    MoveGenSvc --> ValidateSvc
    ValidateSvc --> ExplainSvc

    ExplainSvc --> CLI
    ExplainSvc --> FastAPI
    FastAPI --> UI
```

---

## 4. End-to-End System Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Merchandiser as "Merchandiser / Operator"
    participant UI as "Web Dashboard / CLI"
    participant API as "FastAPI / CLI Runner"
    participant Ingestion as "IngestionEngine"
    participant Repo as "InMemoryRepository"
    participant Velocity as "VelocityService"
    participant Cover as "PositionCoverService"
    participant Problems as "ProblemDetectionService"
    participant MoveGen as "MoveGenerationService"
    participant Validator as "ConstraintValidationService"
    participant Exporter as "ExportService"

    %% Ingestion on startup / sync
    Note over API, Ingestion: System Startup or On-Demand Re-Sync
    API->>Ingestion: run_ingestion(source_path)
    activate Ingestion
    Ingestion->>Ingestion: Read CSV tables (data/csv/)
    Ingestion->>Ingestion: Cast all IDs to strings, parse YYYY-MM-DD
    Ingestion->>Ingestion: Drop packaging SKUs (is_packaging = 1)
    Ingestion->>Ingestion: Isolate invalid rows in DataIssueLog
    Ingestion->>Repo: populate(stores, items, sales, stock, rules)
    deactivate Ingestion

    %% Calculation pipeline execution
    Merchandiser->>UI: Open Dashboard / Request Recommendations
    UI->>API: GET /api/moves (or trigger CLI run)
    API->>Velocity: compute_daily_velocity(Repo)
    activate Velocity
    Velocity->>Velocity: Divide units sold by days_in_stock
    Velocity->>Velocity: Fallback to peer-store velocity for BLR-05
    Velocity-->>API: Store-SKU Daily Velocity Index
    deactivate Velocity

    API->>Cover: compute_positions_and_cover(Repo, velocities)
    activate Cover
    Cover->>Cover: effective_stock = on_hand + in_transit
    Cover->>Cover: cover_days = effective_stock / daily_velocity
    Cover->>Cover: Compute stock age from oldest_stock_received_on
    Cover-->>API: Position & Cover Catalog
    deactivate Cover

    API->>Problems: detect_problem_pockets(positions, lead_times)
    activate Problems
    Problems->>Problems: Flag low-cover stores (cover < route lead time)
    Problems->>Problems: Flag high-cover ageing fashion inventory
    Problems->>Problems: Classify zero-sales ("no stock" vs "no demand")
    Problems-->>API: Findings Summary
    deactivate Problems

    API->>MoveGen: generate_candidate_moves(positions, inbound, lead_times)
    activate MoveGen
    MoveGen->>MoveGen: Step 1: Warehouse-to-Store (highest sales loss first)
    MoveGen->>MoveGen: Step 2: Store-to-Store (surplus to deficit)
    MoveGen->>MoveGen: Assign arrival date from route lead-times matrix
    MoveGen-->>API: Proposed Candidate Moves
    deactivate MoveGen

    API->>Validator: validate_and_filter(candidate_moves, positions, rules)
    activate Validator
    loop For each candidate move
        Validator->>Validator: Rule 1: Donor retains >= min_display (tier x category)
        Validator->>Validator: Rule 2: Receiver capacity ceiling respected
        Validator->>Validator: Rule 3: No transfers of protected S++ flagship styles
        Validator->>Validator: Rule 4: Donor maintains >= 30 days cover post-move
        Validator->>Validator: Rule 5: Deduplicate against existing in-transit stock
        Validator->>Validator: Rule 6: Flag moves > 1,00,000 INR for human approval
    end
    Validator->>Validator: Cumulative Batch Pass (verify combined stock impacts)
    Validator-->>API: Validated Moves + Rejected Move Audit Log
    deactivate Validator

    API->>Exporter: build_output(validated_moves, findings, rejected_log)
    activate Exporter
    Exporter->>Exporter: Build deterministic 1-line reason templates
    Exporter->>Exporter: Format moves.csv & multi-tab moves.xlsx
    Exporter-->>API: Export Artifacts & KPI Metrics
    deactivate Exporter

    API-->>UI: JSON Payload (Ranked Moves, Findings, Summary KPIs)
    UI-->>Merchandiser: Render Approval Table, Findings Panel, and Export Buttons
```

---

## 5. Detailed Component Specifications

### 5.1 Ingestion & Hygiene Engine
- **Decoupled Source**: Reads strictly from `data/csv/` using standard path configurations. No client-side upload is permitted in the UI, guaranteeing clean data isolation and reproducible pipeline execution.
- **Type Enforcement**: All entity identifiers (`store_id`, `sku_id`, `bill_id`, `salesperson_id`) are parsed as strings to prevent loss of leading zeros or corruption of alphanumeric keys.
- **Packaging Elimination**: Items with `is_packaging = 1` (`PKG-BAG`, `PKG-COVER`, `PKG-BOX`) are stripped from sales velocity, basket metrics, and inventory positions.
- **Quarantine Ledger**: Untrusted records (e.g. `KUR-02-M` at `MYS-02` with on-hand `-4`, `SHW-02-L` at `KNP-03` with 300 units vs 250 store capacity) are logged into a structured `DataIssueLog` and quarantined from move proposals.

### 5.2 Stockout-Aware Velocity Engine
- **Standard Velocity Pitfall**: Traditional velocity divides sales by calendar days ($\frac{\text{units}}{90}$), artificially depressing velocity for items that were out of stock for weeks.
- **Stockout-Aware Formula**:
  $$\text{Daily Velocity} = \frac{\sum \text{quantity sold}}{\sum \text{days in stock}}$$
  Using `stock_weekly.days_in_stock` (range 0 to 7 per week) correctly reflects true customer run-rate.
- **Cold-Start Handling**: Stores with $< 28\text{ days}$ of history (`BLR-05`) have insufficient data; their velocity is borrowed from peer stores of identical tier and city.

### 5.3 Move Generation & Hard Constraints Engine
- **Hierarchy of Replenishment**:
  1. *Warehouse to Store*: Draws from available `WH-KOL` on-hand stock and allocates to stores facing imminent stockouts ($\text{cover} < \text{route lead time}$). Prioritizes stores with the highest expected revenue loss ($\text{velocity} \times \text{MRP}$).
  2. *Store to Store*: Transfers excess inventory from donor stores with surplus cover ($> 45\text{ days}$) to needy stores ($< \text{lead time}$).
- **The 6 Non-Negotiable Hard Rules**:
  1. *Minimum Display*: Donor store must remain $\ge \text{min\_display}$ for its tier and category (with Safa, Mala, and Stole combined under Accessories).
  2. *Physical Capacity*: Total on-hand $+$ in-transit $+$ all newly proposed inbound moves must not exceed `stock_capacity_units` at the receiver.
  3. *Flagship Protection*: No style listed in `flagship_protected.csv` for an S++ store may ever be transferred out of that store in any size.
  4. *In-Transit Deduplication*: Existing in-transit stock counts as arriving inventory; duplicate replenishment is blocked.
  5. *Donor Safety*: A store-to-store move must never leave the donor store with $< 30\text{ days}$ of cover for that style.
  6. *Human Approval Gate*: Any single move valued $> ₹1,00,000\text{ MRP}$ ($\text{quantity} \times \text{MRP}$) is flagged with `requires_human_approval = True`.
- **Cumulative Batch Pass**: Evaluates the entire proposed move list together before finalizing to guarantee that multiple simultaneous moves do not breach capacity or minimum display thresholds cumulatively.

### 5.4 Explainability Engine
- Every approved move contains a deterministic, template-based one-line explanation string constructed from calculated attributes.
- Example: `"Send 12: KUR-05-L has 3 days cover at LKO-02, sells 4/day; donor LKO-01 retains 42 days cover"`.
- Template values are directly bound to underlying row calculations to ensure 100% spot-check auditability.

### 5.5 Presentation Layer (Web Dashboard & CLI)
- **CLI Runner**: `python -m src.cli` executes the entire pipeline headless and outputs `moves.csv` and `moves.xlsx`.
- **FastAPI Backend**: Provides lightweight REST endpoints:
  - `GET /api/moves`: Returns ranked moves with filter parameters (type, store, category, approval flag).
  - `POST /api/moves/{move_id}/decision`: Updates approval status (`Approved` or `Rejected`).
  - `GET /api/findings`: Returns hidden problem clusters (stockouts, ageing, store imbalances).
  - `GET /api/summary`: Returns operational KPIs (total units, moves count, ageing value, stockout count).
  - `GET /api/export`: Downloads the current move list in CSV or Excel format.
  - `POST /api/sync`: Re-executes the ingestion and calculation pipeline from `data/csv/`.
- **Dashboard UI**: Single-page vanilla HTML5, CSS3, and JavaScript interface served directly by FastAPI. Zero build steps, instant load times, and responsive across desktop resolutions.
