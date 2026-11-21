# Base Engine
- Status: Draft
- Created: 2026-11-21

## 1. Spec

### Goal & context

Build the base engine: one trusted layer that loads the Manyavar VCH3 data and answers four questions for every store:
1. What stock does each store (and the warehouse) hold, and what is on its way?
2. How much stock has each store been supplied?
3. How far apart are the stores, measured in transit days?
4. How do sales look week by week and across festival and wedding seasons?

Later features build on this layer instead of re-reading the CSVs: stock-move and upgrade recommendations, and Store Coach if it is chosen. It corresponds to the "Build once, use for both" foundation in `docs/common.md` §7, limited to the parts these four questions need.

Sources: `docs/functional-requirements.md` (FR-*), `docs/common.md`, `docs/data-usability-report.md` (DUR), `data/README.md`.

### Scope

In:
- Loading the tables these questions need: `stores`, `items`, `bills`, `bill_lines`, `calendar`, `stock_snapshot`, `stock_weekly`, `warehouse_inbound`, `lead_times`.
- Store reference data (city, state, zone, tier, capacity).
- The current stock position per location and SKU.
- Estimated weekly supply per store and SKU.
- A transit-days matrix between all locations.
- Weekly sales and seasonal sales.
- A data-issue log for problems found in these tables.

Out:
- Recommendations of any kind: stock moves and upgrades. These get their own later spec.
- Velocity, days of cover and stock age (FR-B-01 to FR-B-05). These belong to the move-recommendation spec.
- Store Coach tables and metrics (`salespeople`, `roster_daily`, `footfall_daily`, `area_managers`).
- The rules tables (`rules`, `min_display`, `flagship_protected`).
- Scheduling and daily autonomous runs (FR-COM-17 to FR-COM-21).
- Real-world distances in km. The data has none.
- Changing the source CSVs (OOS-05).

### Requirements

**Loading**
- **REQ-1** Load the 9 in-scope tables from `data/csv/` with no manual steps:
  - every ID column is read as text (FR-COM-02);
  - dates are parsed as `YYYY-MM-DD` (FR-COM-03);
  - number columns are cast explicitly (FR-COM-04).
- **REQ-2** Any value that fails a type cast, or any key that does not join to its parent table (FR-DQ-15), is written to the data-issue log and excluded from results.

**Stores**
- **REQ-3** Provide a store list holding, for each of the 20 stores: store_id, city, state, zone, tier, stock_capacity_units and opened_on. Every store is marked as "new" or "established". A store is new if it opened fewer than 28 days before the as-of date (FR-DQ-07).

**Stock position**
- **REQ-4** Provide the stock position at the as-of date (31 Oct 2026) for every location (the 20 stores plus `WH-KOL`) and every non-packaging SKU, with:
  - on_hand;
  - in_transit;
  - in_transit_arrives_on;
  - oldest_stock_received_on.

  A pair with no snapshot row counts as 0 on hand and 0 in transit (FR-B-04).
- **REQ-5** Provide per-store totals: units on hand, units in transit, the number of distinct SKUs held, and on hand as a percentage of `stock_capacity_units`.
- **REQ-6** Flag a stock row as a data issue and mark it "untrusted", keeping it in the position table, when any of these holds:
  - on_hand < 0 (FR-DQ-04);
  - the snapshot on_hand disagrees with the 31 Oct `stock_weekly.closing_on_hand` (FR-DQ-05);
  - the store's total on hand exceeds its capacity (FR-DQ-06).

**Supply (estimated)**
- **REQ-7** For each store, SKU and week in `stock_weekly` except the first, estimate net supply as:

  `net_supply = closing_on_hand(this week) - closing_on_hand(previous week) + units sold in this week`

  Units sold count only non-packaging units, using the same Sunday-to-Saturday week. Every value is labelled as an estimate.
- **REQ-8** A negative net_supply is kept and labelled "net outflow (transfer out, shrinkage, or data error)". It is not set to zero.
- **REQ-9** Provide estimated supply rolled up per store per week, and per store over the whole 12-week window, plus the units in transit to each store now.
- **REQ-10** Provide planned warehouse supply: `warehouse_inbound` quantity by expected_date and SKU.

**Distance (transit days)**
- **REQ-11** Provide a transit-days matrix covering every ordered pair of locations (21 x 21, excluding a location paired with itself), derived from `lead_times` using each store's city and zone (FR-B-17):
  - from WH-KOL to a store: 3 days (East), 4 days (North), 6 days (South);
  - store to store: 2 days in the same city, 4 days in the same zone but a different city, 7 days in different zones.

  Store-to-warehouse pairs have no rule in `lead_times`. They are marked "no route" and are not guessed.

**Sales**
- **REQ-12** Provide weekly sales per store, and per store and category, for every Sunday-to-Saturday week from 1 Nov 2024 to 31 Oct 2026, with:
  - units sold (non-packaging);
  - revenue (`qty x selling_price`, FR-COM-08);
  - bill count.

  Packaging lines are excluded (FR-COM-10). A partial first or last week is marked as partial.
- **REQ-13** Provide seasonal sales. Every store-day is tagged from `calendar` using the store's state (FR-COM-13), with its festival name (blank if none) and wedding flag. Provide:
  1. units and revenue per store for each festival in each year;
  2. average daily revenue per store on wedding days and on non-wedding days;
  3. monthly units and revenue per store, so each month can be compared with the same month a year earlier.

**Data issues**
- **REQ-14** Keep a data-issue log. Each entry holds: table, key, column, value seen, the rule it breaks, and the action taken (FR-COM-14).
- **REQ-15** Every figure the engine produces can be traced back to its source rows. Given a store, SKU (or category) and date range, the engine can return the input rows behind a figure (FR-COM-26).

### Acceptance criteria

- **AC-1 (REQ-1, 2)**
  - Row counts loaded match the CSVs: stores 20, items 385, bills 90,805, bill_lines 259,772, calendar 2,373, stock_snapshot 3,547, stock_weekly 61,416, warehouse_inbound 768, lead_times 6.
  - IDs with leading zeros keep them.
  - A test file with one bad number and one unknown store_id produces two log entries.
- **AC-2 (REQ-3)** The store list has 20 rows, and BLR-05 is the only store marked "new".
- **AC-3 (REQ-4)**
  - Every one of the 21 locations has a row for every non-packaging SKU.
  - A store-SKU pair absent from the snapshot shows 0 / 0.
  - On-hand totals per location equal the snapshot sums.
- **AC-4 (REQ-5, 6)**
  - KUR-02-M at MYS-02 (-4) is logged and marked untrusted.
  - SHW-02-L at KNP-03 (snapshot 300 against weekly 0) is logged and marked untrusted.
  - KNP-03 is flagged as over capacity.
  - No other snapshot-versus-weekly mismatches are flagged (DUR §6 reports exactly 2).
- **AC-5 (REQ-7, 8)** For 10 randomly chosen store-SKU-weeks, net_supply matches a hand calculation from `stock_weekly`, `bills` and `bill_lines`. At least one negative value, if any exists, carries the "net outflow" label.
- **AC-6 (REQ-9, 10)** Per-store supply totals equal the sum of their weekly rows. Warehouse inbound totals by date equal the CSV sums for the 5 delivery dates.
- **AC-7 (REQ-11)**
  - The matrix has 21 x 20 = 420 ordered pairs.
  - LKO-01 to LKO-02 is 2 days, LKO-01 to KNP-01 is 4, LKO-01 to BLR-01 is 7, WH-KOL to PAT-01 is 3, and WH-KOL to MYS-01 is 6.
  - Every store-to-WH-KOL pair is "no route".
- **AC-8 (REQ-12)** For 5 random store-weeks, units, revenue and bill count match a hand calculation. Packaging SKUs never appear in the totals.
- **AC-9 (REQ-13)**
  - For 3 random store-festival-year combinations, totals match a hand calculation.
  - Festivals appear only for stores in states where `calendar` lists them. For example, no Chhath Puja row appears for a Karnataka store.
- **AC-10 (REQ-14, 15)** Every log entry has all 6 fields. For any figure from AC-5, AC-8 or AC-9, the engine returns the exact source rows used.
- **AC-11 (REQ-12, 13, 15)** Running the engine twice on the same data gives identical outputs.

### Edge cases & failure modes

- **BLR-05** opened 10 Oct 2026, so it has partial weekly sales and few supply weeks. It is marked "new" and its figures are not compared with other stores.
- **PAT-03** has a footfall fault, which does not affect this engine because footfall is out of scope.
- **Placeholder customer** `C99999999`: its bills are real sales lines, so they count in units and revenue. Customer-level logic is out of scope.
- **Units sold in a week with no stock_weekly row** for that store and SKU: supply cannot be estimated for that week, so it is logged and skipped.
- **Missing source CSV or missing column**: the engine fails loudly with the file and column name. It does not produce partial output.
- **Calendar dates beyond 31 Oct 2026** (Nov and Dec 2026) are loaded but not used for sales. They are available for later look-ahead.
- **A SKU in `warehouse_inbound` or `stock_weekly` with no snapshot row** is covered by the zero-fill in REQ-4.

### Assumptions & open questions

Assumptions:
- **Net supply is not shipment data.** Store-to-store transfers out and shrinkage reduce it, so it measures net inflow, not deliveries.
- **The "new store" cut-off is 28 days** (four full weeks). It needs confirmation.
- **Week alignment.** Weeks run Sunday to Saturday (README #8), so sales weeks align with `stock_weekly.week_ending`.

Open questions:
1. **Is the 28-day "new store" cut-off acceptable?**
2. **Where will the outputs be used?** CSV files that the team opens, a Python library imported by later features, or both? This affects the Plan, not the requirements above.
3. **Language and stack?** No code exists yet, and Python with pandas is the usual choice for this data. To be decided at Gate 2.

## 2. Plan

_To be written after Gate 1 approval._

## 3. Tasks

_To be written after Gate 1 approval._
