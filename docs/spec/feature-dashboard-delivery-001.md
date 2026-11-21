# Track 4: Web Dashboard, API & Export
- Status: In Progress
- Created: 2026-11-21
- Revised: 2026-11-21 (rev 2: top nav bar, dark mode, notifications, profile menu, Moves tab layout; Part A tasks T1-T7 already implemented under rev 1)

## 1. Spec

### Goal & context
Build the delivery and presentation layer for the Daily Stock Move Recommender. This layer encompasses a single-command CLI orchestrator, spreadsheet exporters (`moves.csv` and multi-tab `moves.xlsx`), and a high-performance FastAPI web dashboard. The dashboard enables a merchandiser to complete the 10-minute review: inspecting ranked moves, filtering by approval threshold, toggling approve/reject decisions, reviewing problem findings, and downloading distribution-ready exports.

The dashboard also gives the admin a network overview before the approval work: a personal greeting, monthly revenue trends by state, and a state-level revenue table that drills down to city, store, and each store's stock position.

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
  - `GET /api/revenue/monthly`: returns monthly revenue per state.
  - `GET /api/network`: returns the state -> city -> store hierarchy with revenue and stock figures.
  - `GET /api/notifications`: returns current notifications (data issues; moves needing sign-off once moves exist).
- Embedded Web Dashboard (Single-page Vanilla HTML5/CSS3/JavaScript):
  - Fast, responsive approval table with sorting and filtering.
  - Interactive approve/reject button per move.
  - Visual badge for moves requiring human approval ($> ₹1,00,000\text{ MRP}$).
  - Findings panel with drill-down by problem type.
  - Summary KPI cards.
  - Direct download links for Excel and CSV.
  - Hero section greeting the admin by name ("Namaskar {name}").
  - Monthly revenue trend chart per state, with a state filter.
  - State revenue table with expandable drill-down: state -> city -> store -> store stock.
  - "Last run" timestamp next to the Re-run button.
  - Top navigation bar with Overview / Moves tabs, dark mode toggle, notification bell, and profile menu.
  - Moves tab layout (filter bar, summary line, ranked table) built now with an empty state until Track 3 supplies moves.

**Explicitly Out of Scope:**
- Ingestion logic (Track 1).
- Velocity and cover math (Track 2).
- Move generation algorithms and rule validation (Track 3).
- Browser-based file upload.
- Multi-user authentication or role management. The admin name is a display preference only, not an identity.
- Revenue forecasting or targets.
- SKU-level drill-down inside a store (store stock is shown as totals per store).
- Push, email, or SMS notifications; notification history across re-runs (only the current load's notifications are shown).
- Sample or placeholder move data. The Moves tab shows real moves only.

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
- **REQ-6:** Expose a `POST /api/sync` endpoint and UI button allowing the merchandiser to re-trigger ingestion and recalculate recommendations without server restart. Edits made manually to files in `data/csv/` are reflected after the re-run. The dashboard shows the timestamp of the last successful run next to the button.
- **REQ-7 (Hero greeting):** The Overview tab opens with a hero section reading "Namaskar {name}". The hero contains no name-editing controls. On first visit a small dialog asks for the name once; the name is remembered in that browser and can be changed only from the profile menu (REQ-13). If no name is set, the greeting reads "Namaskar Admin".
- **REQ-8 (Revenue definition):** Revenue = sum of `qty x selling_price` over bill lines, joined to the store through the bill, excluding packaging SKUs. This single definition is used by every revenue figure on the dashboard.
- **REQ-9 (Revenue trend chart):** A line chart shows revenue per calendar month, one line per state, over the full date range in the sales data. A state filter lets the admin show any subset of states. Default: all states shown. States are derived from the store data, not hard-coded.
- **REQ-10 (State revenue table):** A table lists one row per state with: state name, number of stores, total revenue, and revenue share (% of total network revenue). Rows are sorted by revenue, highest first. A total row shows network totals; shares sum to 100% (+/- 0.1 for rounding).
- **REQ-11 (Drill-down):** Expanding a state row shows its cities (number of stores, revenue, share of state revenue). Expanding a city shows its stores with: store ID, tier, revenue, on-hand units, in-transit units, stock capacity, capacity utilisation (% of `stock_capacity_units`), and count of SKUs with zero on-hand stock. Stock figures come from the latest stock snapshot and exclude packaging SKUs.
- **REQ-12 (Refresh consistency):** After a successful re-run (REQ-6), the hero "last run" time, revenue chart, state table, drill-down, and notifications all reflect the newly loaded data without a page reload.
- **REQ-13 (Top navigation bar):** A bar fixed at the top of every view contains: product name, tabs *Overview* and *Moves*, a dark mode toggle, a notification bell, and a profile menu. Switching tabs does not reload the page, and the selected tab survives a reload. The profile menu shows the admin name and an option to edit it.
- **REQ-14 (Dark mode):** The dashboard has light and dark themes. By default it follows the operating system setting; the toggle overrides it and the choice is remembered in that browser. Every section, including the chart, table, badges, and dialogs, stays readable in both themes.
- **REQ-15 (Notifications):** The bell shows a count of unseen notifications. Opening it lists them. Notification sources:
  - (a) each data issue recorded by ingestion on the latest load, showing table, key, what was wrong, and the action taken;
  - (b) moves needing sign-off (MRP value over Rs 1,00,000 and decision still waiting), shown as one notification with the count. This source is empty until Track 3 supplies moves.
  Opening the list marks its current items as seen in that browser. An item is identified by its content, so the same issue after a re-run stays seen, and a new issue raises the count.
- **REQ-16 (Moves tab layout):** The Moves tab follows the reference layout supplied by the user:
  - **Filter bar:** Type, Store, Category (dropdowns); Value (All / Over Rs 1 lakh / Under Rs 1 lakh); Decision (Any / Waiting / Approved / Rejected); Find (free text over SKU, style, city).
  - **Summary line:** "Showing X of Y moves: N units, Rs Z MRP" for the filtered set.
  - **Table columns:** Rank; Move (type and sub-type, e.g. Transfer / store to store); Route (from city -> to city, with store IDs); Style and reason (style name, SKU, data-backed reason); Qty; MRP value with a "Needs sign-off" badge above Rs 1 lakh; Dispatch and arrival (dispatch date, arrival date, transit days); Decision (Approve / Reject buttons and current status). Rows needing sign-off have a coloured left edge.
  - **Until Track 3 supplies moves:** the tab shows the filter bar and column headers with an empty state stating that no moves are available yet because move generation is not built. Filters other than Store are disabled. The Store list is filled from store data.
  - Row data, sorting, filtering behaviour, and approve/reject actions are delivered with REQ-4 and REQ-5 in Part B.

### Acceptance criteria
- **AC-1 (REQ-1, 2):** Running `python -m src.cli` produces valid `moves.csv` and multi-tab `moves.xlsx` on disk matching all required column schemas.
- **AC-2 (REQ-3, 5):** The web dashboard runs on `http://localhost:8000`, renders moves within 2 seconds, and allows sorting and filtering without page reloads.
- **AC-3 (REQ-4):** Toggling a move to `Rejected` updates its status dynamically in the UI and reflects in the exported spreadsheet.
- **AC-4 (REQ-5):** High-value moves ($> ₹1,00,000\text{ MRP}$) are visibly tagged with human-approval warnings.
- **AC-5 (REQ-6):** Clicking the "Sync / Re-run" button triggers the pipeline and refreshes dashboard data. Adding a bill row to `data/csv/` and re-running changes the affected revenue figures, and the "last run" time updates.
- **AC-6 (REQ-7):** First visit opens the name dialog; after entering "Asha", reloading shows "Namaskar Asha" with no dialog. Editing the name in the profile menu updates the greeting. The hero has no name controls. Clearing browser data shows "Namaskar Admin" and the dialog again.
- **AC-7 (REQ-8, 10):** For each state, the table's revenue equals an independent calculation of `sum(qty x selling_price)` from the CSVs for that state's stores (packaging excluded), to the rupee. Store counts match `stores.csv` (UP 7, Bihar 6, Karnataka 7 on the current data).
- **AC-8 (REQ-9):** The chart initially shows one line per state for every month from Nov 2024 to Oct 2026. Deselecting a state hides its line; the sum of a state's monthly values equals its total in the state table.
- **AC-9 (REQ-11):** Expanding Uttar Pradesh shows Lucknow (4 stores) and Kanpur (3 stores); city revenues sum to the state's revenue. Expanding Lucknow lists LKO-01..LKO-04 with the stock columns, and each store's on-hand total matches `stock_snapshot.csv` (packaging excluded).
- **AC-10 (REQ-12):** After a re-run, all overview sections show updated values with no page reload.
- **AC-11 (REQ-13):** The nav bar is visible on both tabs. Switching between Overview and Moves does not reload the page. Reloading while on Moves stays on Moves.
- **AC-12 (REQ-14):** With the OS in dark mode, a first visit opens in dark theme. Toggling switches theme immediately and the choice persists across reloads. Chart axes, lines, table text, badges, and dialogs are readable in both themes.
- **AC-13 (REQ-15):** On the current data the bell shows 4, and the list includes the snapshot mismatch for `KNP-03/SHW-02-L`. Opening the list clears the count; it stays 0 after reload. Adding a negative on-hand row to `stock_snapshot.csv` and re-running raises the count to 1.
- **AC-14 (REQ-16):** The Moves tab shows the filter bar and all column headers listed in REQ-16, an empty-state message, disabled filters except Store, and a Store list containing all 20 stores.

### Edge cases & failure modes
- **Large Result Sets:** Efficient DOM rendering ensures smooth scrolling and filtering across hundreds of rows.
- **Missing Output Directory:** Export service automatically creates output directories if they do not exist.
- **Re-run fails** (e.g. a malformed CSV edited by hand): the dashboard keeps showing the last good data, shows an error message, and the "last run" time does not change.
- **State with no sales in a month:** the chart plots 0 for that month rather than leaving a gap.
- **Store with no sales:** appears in the drill-down with revenue 0 (e.g. a newly opened store).
- **Store with no snapshot rows:** stock columns show 0 and the store is still listed.
- **All states deselected in the chart filter:** the chart shows an empty-state message instead of blank axes.
- **Name input:** empty or whitespace-only names fall back to "Admin"; the name is displayed as plain text (never interpreted as HTML).
- **Browser storage unavailable** (private mode): greeting shows "Namaskar Admin", no name dialog is shown, the theme follows the OS, the bell counts all current notifications as unseen, and the dashboard still works.
- **Name dialog dismissed or left empty:** greeting stays "Namaskar Admin" and the dialog does not reappear; the name can still be set from the profile menu.
- **No notifications:** bell shows no count; the list says there are no notifications.
- **Notifications fail to load:** the bell shows no count and the rest of the dashboard works.

### Assumptions & open questions
- Application runs locally on port 8000 via Uvicorn.
- Modern desktop browser (Chrome, Edge, Firefox) is used.
- Revenue uses `selling_price` (what the customer paid), not `mrp`.
- The Moves tab reference layout came from a screenshot of a different dataset (Kochi, Jaipur, Kolkata, New Delhi stores). Only its layout is adopted; cities and values will come from this project's data.
- The warehouse (WH-KOL) has no sales and is not a store; it is excluded from the revenue table and drill-down. West Bengal therefore does not appear on the current data.
- The overview sections (REQ-7 to REQ-11) depend only on ingestion data (Track 1), not on Tracks 2-3, so they can be delivered before the moves pipeline is complete.
- Open question: none.

## 2. Plan

### Delivery split
Track 1 (ingestion) is `Implemented`; Tracks 2 and 3 are `Draft` and define no `Move` / `Finding` model or service yet. Work is therefore split:
- **Part A - buildable now:** REQ-6, REQ-7 to REQ-12 (overview, re-run, last-run time). Depends only on Track 1 repositories.
- **Part B - blocked on Track 3:** REQ-1 to REQ-5 (moves table, decisions, findings, KPI cards, `moves.csv` / `moves.xlsx`, CLI). Its tasks cannot be detailed without Track 3's `Move` contract. They are listed below as blocked and will be planned in detail once Track 3's Plan is approved (via an update to this Plan, re-approved at Gate 2).

### Files and components (Part A)
| File | New/Change | Reason |
|---|---|---|
| `src/domain/overview.py` | New | Read-only result models for the overview (no logic). |
| `src/services/__init__.py` | New | Package marker. |
| `src/services/network_overview_service.py` | New | Business logic: revenue aggregation and store stock totals. Depends only on `IStoreRepository`, `ISalesRepository`, `IStockRepository`. |
| `src/api/__init__.py` | New | Package marker. |
| `src/api/data_context.py` | New | Holds the current repository container, cached overview, and last-run time; performs the safe re-run swap. |
| `src/api/app.py` | New | FastAPI app factory and routes. HTTP only; no business logic. |
| `src/api/__main__.py` | New | `python -m src.api` starts Uvicorn on port 8000. |
| `src/web/index.html`, `src/web/styles.css`, `src/web/app.js` | New | Single-page dashboard served by FastAPI as static files. |
| `requirements.txt` | New | Pins runtime and test dependencies (none is recorded today; `pytest` is not installed in the current environment although Track 1 tests need it). |
| `tests/fakes.py` | New | In-memory fake repositories implementing the Track 1 interfaces, for service unit tests. |
| `tests/test_network_overview_service.py` | New | Unit tests against fakes. |
| `tests/test_overview_real_data.py` | New | Checks AC-7 / AC-9 against an independent CSV calculation. |
| `tests/test_api_overview.py` | New | API tests with FastAPI `TestClient`, including re-run against a temporary copy of `data/csv/`. |

No Track 1 file is modified.

### Data models and contracts

**Revenue (REQ-8):** single source of truth is the existing `SalesLine.line_revenue` (`qty x selling_price`). Packaging is already excluded by the Track 1 loader. The service never re-derives the formula.

**`src/domain/overview.py`** (frozen dataclasses):
- `StoreOverview`: `store_id, tier, revenue, on_hand, in_transit, capacity, utilisation_pct, zero_stock_skus`
- `CityOverview`: `city, store_count, revenue, share_of_state_pct, stores: list[StoreOverview]`
- `StateOverview`: `state, store_count, revenue, share_pct, cities: list[CityOverview]`
- `NetworkOverview`: `total_revenue, store_count, states: list[StateOverview]`
- `MonthlyRevenue`: `months: list[str]` (`YYYY-MM`), `series: dict[str, list[float]]` (state -> value per month, zero-filled)

**`NetworkOverviewService`** (constructor takes the three repository interfaces):
- `get_network_overview() -> NetworkOverview`: states sorted by revenue desc; cities and stores sorted by revenue desc. Shares computed against the parent total; parent total 0 -> share 0.
- `get_monthly_revenue() -> MonthlyRevenue`: months span min..max `bill_date` month, every state present with zeros for empty months.
- Store stock: sum of `on_hand` / `in_transit` over snapshot positions where `location_id == store_id`; `zero_stock_skus` = count of that store's snapshot positions with `on_hand == 0`; `utilisation_pct = on_hand / capacity x 100`.
- States, cities, and stores come from `IStoreRepository`, so stores without sales or snapshot rows still appear with zeros, and WH-KOL (not a store) never appears.

**`DataContext`**:
- `current() -> (container, overview, monthly, last_run)`
- `rerun()`: under a lock, builds a **new** `InMemoryRepositoryContainer` and new overview; swaps references only on success. On exception the previous data and `last_run` are kept and the error is re-raised. (Swap instead of calling `container.sync()` in place so a failed load can never leave half-updated data.)
- Overview results are computed once per load and cached, since aggregating ~260k bill lines on every request is unnecessary.

**HTTP API (JSON):**
| Method / path | Response |
|---|---|
| `GET /` | `index.html` |
| `GET /api/status` | `{"last_run": ISO-8601}` |
| `GET /api/revenue/monthly` | `{"months": [...], "series": [{"state", "values": [...]}]}` |
| `GET /api/network` | `NetworkOverview` serialised (nested states -> cities -> stores) |
| `POST /api/sync` | `200 {"status": "ok", "last_run"}` or `500 {"status": "error", "message"}` |

**Frontend:**
- Hero: name read from `localStorage` key `stockMover.adminName` inside `try/catch`; prompt via an inline input (not `window.prompt`); rendered with `textContent` only (no HTML injection). "Change" link re-opens the input.
- Chart: hand-drawn inline SVG bar chart (one path per state, month axis, rupee axis, legend), with a small filter per state built from the API response. Empty selection -> message.
- State table: rows expand/collapse in place (state -> cities -> stores). Indian number formatting via `Intl.NumberFormat('en-IN')`.
- Re-run button: disables while running, calls `POST /api/sync`, then refetches status, chart, and table; on error shows a message and keeps current data.

### Dependencies
- `fastapi`, `uvicorn` - already chosen in this spec and installed.
- `pytest` - already used by Track 1 tests; must be installed.
- `httpx` - required by FastAPI `TestClient`; already installed.
- `openpyxl` - Part B only (Excel export); already installed.
- **No charting library.** A line chart with up to a handful of series is small enough to draw in SVG, works offline, and avoids a CDN dependency on a locally run tool.

### Risks and trade-offs
- **Untrusted stock rows:** Track 1 marks negative or mismatched snapshot rows `is_untrusted` but keeps them. Store stock totals include them so figures match `stock_snapshot.csv` (AC-9). A negative row would lower a store's total; acceptable for an overview, flagged here.
- **`zero_stock_skus` counts only SKUs present in the snapshot for that store**; a SKU never ranged in a store is not counted as a stock-out.
- **Re-run time:** a full reload re-reads all CSVs (a few seconds). Button shows a busy state; concurrent clicks are serialised by the lock.
- **In-process state:** last-run time and data live in memory; restarting the server reloads from CSV and resets `last_run` to startup time. Acceptable for a single local user.
- **Hand-drawn chart:** less feature-rich than a library (no zoom). Tooltips limited to a native SVG `<title>` per point.

### Test strategy
| Requirement | Test |
|---|---|
| REQ-8, REQ-10 | `test_network_overview_service.py`: fake repos with known lines -> exact revenue, store counts, shares sum to 100, sort order, total-0 share. `test_overview_real_data.py`: AC-7 against independent `csv` module sums. |
| REQ-9 | Service unit test: month range, zero-fill, per-state monthly sum == state total. Real-data test: 24 months Nov 2024 - Oct 2026. |
| REQ-11 | Service unit test: city/store nesting, store with no sales, store with no snapshot rows, utilisation, zero-stock count. Real-data test: AC-9 (UP -> Lucknow 4 / Kanpur 3; LKO on-hand matches CSV). |
| REQ-6, REQ-12 | `test_api_overview.py`: copy `data/csv/` to a temp dir, append a bill + line, `POST /api/sync` -> revenue and `last_run` change. Corrupt a CSV -> 500, previous data and `last_run` unchanged. |
| REQ-7 | No automated JS test harness exists; verified manually in a browser (AC-6, private-mode fallback, HTML-in-name rendered as text). Recorded in Spec memory. |
| AC-8, AC-10 (UI) | Manual browser check, recorded in Spec memory. |

### Rev 2 additions (REQ-7 change, REQ-13 to REQ-16)

**Files and components**
| File | New/Change | Reason |
|---|---|---|
| `src/domain/notifications.py` | New | `Notification` model. |
| `src/services/notification_service.py` | New | `INotificationSource` interface, `DataIssueNotificationSource`, and `NotificationService` that merges sources. |
| `src/api/data_context.py` | Change | Compute and cache notifications per load, alongside the overview. |
| `src/api/app.py` | Change | Add `GET /api/notifications`. |
| `src/web/index.html`, `src/web/styles.css` | Change | Nav bar, tabs, theme tokens for dark mode, name dialog, Moves tab layout; remove hero name controls. |
| `src/web/app.js` | Remove | Split into ES modules below (one responsibility each); the single file would otherwise own seven concerns. |
| `src/web/js/api.js`, `dom.js`, `storage.js` | New | Fetch wrapper; DOM / formatting helpers; `localStorage` access wrapped in `try/catch`. |
| `src/web/js/theme.js`, `tabs.js`, `profile.js`, `notifications.js` | New | One module per nav-bar feature. |
| `src/web/js/overview.js`, `moves.js`, `main.js` | New | Overview tab (existing chart / table code moved, not rewritten); Moves tab shell; start-up wiring and re-run. |
| `tests/fakes.py` | Change | Add `FakeRulesRepository`. |
| `tests/test_notification_service.py` | New | Unit tests against fakes. |
| `tests/test_api_overview.py` | Change | Notification endpoint tests on a temp data copy. |

No Track 1 file is modified.

**Notification contract**
- `Notification` (frozen): `id: str, kind: str ("data_issue" | "sign_off"), title: str, detail: str`.
- `id` = SHA-1 of the notification's content (for data issues: `table|key|column|rule_violated|value_seen`). Same issue after a re-run -> same id, so it stays seen; changed or new issue -> new id (REQ-15).
- `INotificationSource.collect() -> List[Notification]`. `NotificationService(sources: List[INotificationSource]).get_all()` concatenates in source order.
- `DataIssueNotificationSource(rules: IRulesRepository)`: one notification per `DataIssue`. Title from the rule (e.g. "Snapshot disagrees with weekly stock"), detail = `key`, value seen, action taken.
- Sign-off source (REQ-15b) is **not** built now. Part B adds it as a new `INotificationSource` with no change to `NotificationService` (open/closed).
- `GET /api/notifications` -> `{"items": [{"id", "kind", "title", "detail"}]}`.
- Existing violation noted, not changed: data issues are exposed through `IRulesRepository.get_all_data_issues()`, which mixes rule lookup with ingestion issues (interface segregation). Suggested fix for Track 1: a separate `IDataIssueRepository`. The source depends on `IRulesRepository` until then.

**Frontend design**
- **Modules:** native ES modules (`<script type="module">`), no bundler, no new dependency.
- **Nav bar:** sticky header with brand, tab buttons (`role="tab"`), theme toggle, bell button with count badge and a popover list, profile button with a popover (name, "Edit name" inline field). Popovers close on outside click and Escape.
- **Tabs:** `#overview` / `#moves` URL hash selects the view; `hashchange` switches without reload; reload keeps the hash (AC-11).
- **Theme:** `<html data-theme="light|dark">`. All colours are CSS custom properties with a dark set. Stored key `stockMover.theme`; when absent, `matchMedia('(prefers-color-scheme: dark)')` decides and changes are followed live. Chart re-renders on theme change, since its line colours are read from CSS variables.
- **Name:** native `<dialog>` shown once when `stockMover.adminName` has never been written. Save or dismiss writes the value (empty on dismiss) so it does not reappear. Edit lives only in the profile popover. All name output uses `textContent`.
- **Seen notifications:** key `stockMover.seenNotifications` holds the ids seen; opening the list replaces it with the current ids (bounded size). Storage unavailable -> everything counts as unseen.
- **Moves tab shell:** filter bar and table header exactly as REQ-16; Store `<select>` filled from `/api/network` (flattened, label `STORE-ID - City`); other controls `disabled`; `<tbody>` shows the empty-state row. Sign-off row edge and badge styles are defined now for Part B.

**Risks and trade-offs**
- ES modules need the page served over HTTP (they are), not opened as a file.
- `<dialog>` is supported in all target browsers (Chrome, Edge, Firefox).
- Notification ids from content mean that editing an issue's underlying value (e.g. a different wrong number) produces a new notification. This is intended.

**Test strategy**
| Requirement | Test |
|---|---|
| REQ-15 | `test_notification_service.py`: one notification per issue; same content -> same id across loads; different content -> different id; sources merged in order; no issues -> empty list. |
| REQ-15, REQ-12 | `test_api_overview.py`: real-data copy returns 4 items including `KNP-03/SHW-02-L`; appending a negative on-hand row and syncing adds exactly one new id and keeps the old 4 ids. |
| REQ-7, REQ-13, REQ-14, REQ-15 UI, REQ-16 | Manual browser checks of AC-6, AC-11 to AC-14 (no JS test harness), plus headless screenshots in both themes. Recorded in Spec memory. |

## 3. Tasks

**Part A**
- [x] **T1 - Dependencies** (all). Add `requirements.txt`; install. Done when: `python -m pytest tests/test_ingestion.py` passes.
- [x] **T2 - Overview models + fakes** (REQ-10, REQ-11). Add `src/domain/overview.py`, `tests/fakes.py`. Done when: modules import cleanly.
- [x] **T3 - Network overview service** (REQ-8, REQ-10, REQ-11). Done when: unit tests for revenue, counts, shares, sorting, nesting, and zero-cases pass against fakes.
- [x] **T4 - Monthly revenue** (REQ-8, REQ-9). Done when: unit tests for month range, zero-fill, and sum-equals-total pass.
- [x] **T5 - Real-data verification** (AC-7, AC-9). Done when: `tests/test_overview_real_data.py` passes.
- [x] **T6 - DataContext with safe re-run** (REQ-6, REQ-12). Done when: tests show a successful re-run swaps data and updates `last_run`, and a failed one keeps both.
- [x] **T7 - FastAPI app and routes** (REQ-3 for overview endpoints, REQ-6). Done when: `test_api_overview.py` passes, including the append-a-bill and corrupt-CSV cases; `python -m src.api` serves `/api/network` on port 8000.
- [ ] ~~**T8 - Dashboard shell + hero** (REQ-7 rev 1).~~ Replaced by T17 under rev 2.
- [ ] **T9 - Revenue chart + state filter** (REQ-9). Done when: manual check of AC-8 (all states default, deselect hides line, empty-selection message).
- [ ] **T10 - State table + drill-down** (REQ-10, REQ-11). Done when: manual check that UI values match `/api/network` and the UP / Lucknow example of AC-9.
- [ ] **T11 - Re-run button + refresh** (REQ-6, REQ-12). Done when: manual check of AC-5 and AC-10, including error message on a failing re-run.

**Part A rev 2** (order of work: T13 -> T19, then the manual checks of T9 -> T11 on the restructured page)
- [x] **T13 - Notification model, source, service** (REQ-15a). Done when: `tests/test_notification_service.py` passes.
- [x] **T14 - Notifications in DataContext + `GET /api/notifications`** (REQ-15, REQ-12). Done when: API tests pass (4 items on real data incl. `KNP-03/SHW-02-L`; new negative row adds exactly one new id after sync); full suite passes.
- [ ] **T15 - Split frontend into ES modules + nav bar + tabs** (REQ-13). Done when: overview renders as before (headless screenshot) and manual AC-11 passes.
- [ ] **T16 - Dark mode** (REQ-14). Done when: headless screenshots in both themes are readable and manual AC-12 passes.
- [ ] **T17 - Profile menu + first-visit name dialog; hero name controls removed** (REQ-7, REQ-13). Done when: manual AC-6, dismissed-dialog, private-mode, and HTML-in-name checks pass.
- [ ] **T18 - Notification bell UI** (REQ-15). Done when: manual AC-13, no-notifications, and load-failure checks pass.
- [ ] **T19 - Moves tab shell** (REQ-16). Done when: manual AC-14 passes.

**Part B - Blocked until Track 3 Plan is approved**
- [ ] **T12 - Plan Part B** (REQ-1 to REQ-5, REQ-15b, REQ-16 row behaviour): extend this Plan with the moves/findings/export/CLI design and the sign-off notification source using Track 3's contracts; return to Gate 2.
