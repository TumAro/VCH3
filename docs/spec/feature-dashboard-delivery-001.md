# Track 4: Web Dashboard, API & Export
- Status: Draft
- Created: 2026-11-21

## 1. Spec

### Goal & context
Build the delivery and presentation layer for the Daily Stock Move Recommender. This layer encompasses a single-command CLI orchestrator, spreadsheet exporters (`moves.csv` and multi-tab `moves.xlsx`), and a high-performance FastAPI web dashboard. The dashboard enables a merchandiser to complete the 10-minute review: inspecting ranked moves, filtering by approval threshold, toggling approve/reject decisions, reviewing problem findings, and downloading distribution-ready exports.

### Scope

**In Scope:**
- Orchestrating the end-to-end pipeline: Ingestion $\to$ Velocity $\to$ Moves $\to$ Output.
- Headless CLI runner (`python -m src.cli`) producing `moves.csv` and `moves.xlsx` from local files.
- Export service generating:
  - `moves.csv`: flat list of approved moves.
  - `moves.xlsx`: multi-tab workbook with sheets: *Moves*, *Findings*, and *Rejected Moves*.
- FastAPI web backend with REST endpoints:
  - `GET /api/moves`: returns ranked moves with query filters (`move_type`, `store_id`, `category`, `requires_approval`).
  - `POST /api/moves/{move_id}/decision`: toggles move state (`Approved` vs `Rejected`).
  - `GET /api/findings`: returns detected problem pockets (stockouts, ageing clusters, zero-sales).
  - `GET /api/summary`: returns high-level KPIs (total moves, units moved, capital at risk, stockout SKUs).
  - `GET /api/export`: triggers download of current `moves.xlsx` or `moves.csv`.
  - `POST /api/sync`: triggers pipeline re-run from `data/csv/`.
- Embedded Web Dashboard (Single-page Vanilla HTML5/CSS3/JavaScript):
  - Fast, responsive approval table with sorting and filtering.
  - Interactive approve/reject button per move.
  - Visual badge for moves requiring human approval ($> ₹1,00,000\text{ MRP}$).
  - Findings panel with drill-down by problem type.
  - Summary KPI cards.
  - Direct download links for Excel and CSV.

**Explicitly Out of Scope:**
- Ingestion logic (Track 1).
- Velocity and cover math (Track 2).
- Move generation algorithms and rule validation (Track 3).
- Browser-based file upload.
- Multi-user authentication or role management.

### Requirements
- **REQ-1:** Provide a CLI entry point (`python -m src.cli`) that executes the full pipeline end-to-end in $< 30\text{ seconds}$ and writes `moves.csv` and `moves.xlsx`.
- **REQ-2:** Generate a multi-tab Excel workbook (`moves.xlsx`) containing:
  - Sheet 1: *Moves* (type, from, to, SKU, style, qty, MRP value, dispatch date, arrival date, approval flag, reason).
  - Sheet 2: *Findings* (problem type, store, SKU, metric value, diagnosis).
  - Sheet 3: *Rejected Moves* (candidate move, rule violated, rejection reason).
- **REQ-3:** Build a FastAPI web server serving REST endpoints for moves, findings, summary KPIs, approval actions, and exports.
- **REQ-4:** Maintain decision state: toggling a move to `Rejected` updates the in-memory record and excludes the move from the active approved export.
- **REQ-5:** Build a single-page web dashboard (`index.html`) using vanilla HTML/JS/CSS served directly by FastAPI:
  - Loads initial state in $< 2\text{ seconds}$.
  - Supports live client-side filtering by move type, store, category, and approval requirement.
  - Highlights high-value moves ($> ₹1,00,000\text{ MRP}$) with prominent approval badges.
  - Displays summary KPI cards: Total Moves, Total Units, Value at Stake, and Stockout SKUs.
  - Provides a Findings tab displaying hidden problem pockets.
  - Provides one-click buttons to download `moves.xlsx` and `moves.csv`.
- **REQ-6:** Expose a `POST /api/sync` endpoint and UI button allowing the merchandiser to re-trigger ingestion and recalculate recommendations without server restart.

### Acceptance criteria
- **AC-1 (REQ-1, 2):** Running `python -m src.cli` produces valid `moves.csv` and multi-tab `moves.xlsx` on disk matching all required column schemas.
- **AC-2 (REQ-3, 5):** The web dashboard runs on `http://localhost:8000`, renders moves within 2 seconds, and allows sorting and filtering without page reloads.
- **AC-3 (REQ-4):** Toggling a move to `Rejected` updates its status dynamically in the UI and reflects in the exported spreadsheet.
- **AC-4 (REQ-5):** High-value moves ($> ₹1,00,000\text{ MRP}$) are visibly tagged with human-approval warnings.
- **AC-5 (REQ-6):** Clicking the "Sync / Re-run" button triggers the pipeline and refreshes dashboard data.

### Edge cases & failure modes
- **Large Result Sets:** Efficient DOM rendering ensures smooth scrolling and filtering across hundreds of rows.
- **Missing Output Directory:** Export service automatically creates output directories if they do not exist.

### Assumptions & open questions
- Application runs locally on port 8000 via Uvicorn.
- Modern desktop browser (Chrome, Edge, Firefox) is used.

## 2. Plan
_To be written after Gate 1 approval._

## 3. Tasks
_To be written after Gate 1 approval._
