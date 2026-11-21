# Manyavar VCH3 data pack: what it holds and how usable it is

Scope: structure, coverage, joins, data quality and fit for the two problem statements. This is an abstract-level study. It reports counts, ranges and integrity checks only. It does no statistical analysis (no trends, distributions, seasonality sizing or modelling). Every "pattern worth testing" below is a hypothesis for the later analysis phase, not a finding.

Sources read: `data/README.md`, both briefs (`A_Store_Coach_brief.pdf`, `B_Stock_Mover_brief.pdf`), `data/csv/data_dictionary.csv`, and all 17 CSVs.

---

## 1. The big picture

- Synthetic data for Manyavar (Vedant Fashions Limited), a menswear and ethnic-wear retailer. It is tuned to resemble real patterns, volumes are scaled down, and no real store, person or customer appears.
- 20 stores in 6 cities across 3 states, plus one warehouse (`WH-KOL`, Kolkata).
- 24 months of sales: 1 Nov 2024 to 31 Oct 2026. "Today" in the data is the close of 31 Oct 2026.
- Two problem statements use this same data. The team builds one of them:
  - **A. Store Coach.** A daily, unprompted system that tells each area manager which stores need attention and why, and gives each salesperson one action for the day. It grows three levers: conversion, items per bill, and repeat customers.
  - **B. Stock Mover.** A daily system that produces an approvable list of stock moves: warehouse to store, store to store, and pull-back of ageing stock. It is built on sales velocity and days of cover.
- The data is shipped as 17 CSVs (also as an Excel file, which is not in our folder) and a data dictionary. The README says nothing has been cleaned, so the problems in section 6 are deliberate and part of the test.

---

## 2. Table-by-table: what each file is and what it can tell us

### Reference (small, static)

- `stores` (20 rows). Store id (city code plus number), city, state, zone, tier, floor size, stock capacity, opening date, area manager.
  - Tiers: S++ (super flagship), S+ (flagship), A, B. A is better than B.
  - Zone maps one-to-one to state: North is Uttar Pradesh, East is Bihar, South is Karnataka.
  - Cities: Lucknow, Kanpur (North); Patna, Muzaffarpur (East); Bengaluru, Mysuru (South).
  - One store, BLR-05, is brand new (opened 10 Oct 2026).
  - Use: peer groups (store, city, state, tier), capacity limits, minimum display lookup.
- `area_managers` (6 rows). One per city. Carries `max_alerts_per_week = 5` for every manager.
  - The `stores` column is a comma-separated list inside one cell. It has to be split. It duplicates what `stores.area_manager_id` already gives.
  - Use: this is the recipient list for Problem A and the hard cap on alert volume.
- `items` (385 rows). One row per SKU, where a SKU is one style in one size.
  - 75 styles plus 3 packaging items (`PKG-BAG`, `PKG-COVER`, `PKG-BOX`).
  - Categories: Kurta Set, Sherwani, Indo-Western, Jacket, Mojari (footwear), Safa, Mala, Stole, Packaging.
  - Sizes: S to XXXL for apparel, 6 to 11 for Mojari, FS (free size) for Safa, Mala, Stole and packaging.
  - Also carries MRP, an illustrative cost price, launch date, and `is_core_style` (1 means replenished all year, 0 means a fashion style with a limited run). About a third of styles are core.
  - Use: category roll-ups, margin (MRP versus cost), style grouping across sizes, core versus fashion logic.
- `calendar` (2,373 rows). One row per date per state, Nov 2024 to Dec 2026.
  - `festival` is blank on non-festival days. `is_wedding_date` is 0 or 1.
  - It extends past the sales window into Nov and Dec 2026, so it can look forward.
  - Festivals are state-specific. Examples: Chhath Puja is Bihar only, Ganesh Chaturthi and Ugadi are Karnataka only, Holi is not in Karnataka.
  - Use: separating normal festival and wedding swings from real problems (Problem A explicitly says not to alert on these), and forward demand context for stock (Problem B).

### People and floor data (Problem A territory)

- `salespeople` (175 rows). Id, home store, name, join date.
  - Includes people who have left, but there is no exit date.
  - Use: peer comparison inside a store. Leavers must be inferred from the last bill or roster date.
- `roster_daily` (23,569 rows). One row per salesperson per day with status Present or Off.
  - Covers only 1 May to 31 Oct 2026, which is six months, not the full two years.
  - Use: staffing on the floor per day, missed shifts, weekly-off planning. This supports "move X's weekly off to Tuesday" style actions.
- `footfall_daily` (13,892 rows). One row per store per day, a door-camera walk-in count. The dictionary warns that families walk in together, so footfall counts people rather than buying parties.
  - Covers the full 24 months for 19 stores and 22 days for BLR-05.
  - Use: the denominator for conversion (bills divided by footfall).

### Transactions (both problems)

- `bills` (90,805 rows). Bill id, date, store, salesperson, hashed customer id.
  - There is no time of day. See section 5.
  - The customer id is a hashed mobile number, stable across visits and across stores.
- `bill_lines` (259,772 rows). One row per item on a bill: bill id, SKU, quantity (1 to 3), MRP, selling price.
  - Line revenue is quantity times selling price. A bill's value is the sum of its lines.
  - Discount per unit is MRP minus selling price.
  - Packaging lines are priced at Rs 0 and are not products. They must be excluded when counting items per bill or sales velocity.
  - Money is in rupees and includes GST.
  - Use: everything. Conversion numerator, basket size, cross-sell pairs, discount behaviour, category mix, repeat customers, and the sales side of velocity.

### Stock (Problem B territory)

- `stock_snapshot` (3,547 rows). One row per location (20 stores plus the warehouse) per SKU, at close on 31 Oct 2026.
  - Columns: on hand, in transit, date the in-transit stock arrives, and date the oldest unit on hand was received.
  - A missing location and SKU pair means no stock and nothing in transit (see section 6).
  - Use: current position, stock age (from the oldest-received date), what is already on its way (it must not be sent twice).
- `stock_weekly` (61,416 rows). One row per store, SKU and week for the last 12 weeks (week ending 15 Aug to 31 Oct 2026). Weeks run Sunday to Saturday.
  - Columns: closing on hand and `days_in_stock` (how many of the 7 days had at least one unit).
  - This is the stock-out detector. A SKU with no sales and `days_in_stock` of 0 was not slow, it simply was not there. This is the brief's "zero sales isn't always slow" warning.
  - It has no warehouse rows.
- `warehouse_inbound` (768 rows). Deliveries due into the warehouse from 1 Nov to 16 Dec 2026 (five delivery dates). All are status "Planned". Use: what supply is coming, so the allocation is not limited to what is in the warehouse today.

### Stock rules (Problem B)

- `rules` (8 rules, in prose). The constraints a recommendation must respect:
  - Keep a minimum display per tier and category.
  - S++ stores never give away their top-20 styles.
  - Never send a store more than its capacity.
  - Stock in transit counts as already arriving.
  - A donor store must not fall below 30 days of cover for the style.
  - A single move worth more than Rs 1,00,000 at MRP needs human approval.
  - Replenishment today happens every Monday, but the system may recommend any day.
  - Ignore transport cost, but respect lead time.
- `min_display` (24 rows). Minimum units per tier and category (4 tiers by 6 categories).
  - It groups Safa, Mala and Stole into one category called "Accessories (Safa/Mala/Stole)". In `items` they are three separate categories, so they must be summed.
- `lead_times` (6 rows). Transit days per route:
  - Warehouse to store: 3 days East, 4 days North, 6 days South.
  - Store to store: 2 days same city, 4 days same zone but different city, 7 days different zone.
  - The route is written as a sentence, not a code. It must be derived from each store's city and zone.
- `flagship_protected` (80 rows). The top-20 styles for each of the 4 S++ stores (LKO-01, PAT-01, BLR-01, BLR-02), by rank.
  - Only S++ stores appear. These styles can never be transferred out.

### Metadata

- `data_dictionary` (36 rows). Column-level definitions with examples. It is accurate against what I found and is the fastest reference.

---

## 3. How the tables connect

- `store_id` joins every table that has it back to `stores`.
- `bill_id` joins `bill_lines` to `bills`.
- `sku_id` joins `bill_lines`, `stock_snapshot`, `stock_weekly` and `warehouse_inbound` to `items`.
- `salesperson_id` joins `bills` and `roster_daily` to `salespeople`.
- `area_manager_id` joins `stores` to `area_managers`.
- `state` joins `stores` to `calendar`.
- `style_id` groups all sizes of one design. It is the join to `flagship_protected`, and the unit for flagship protection and style-level cover.
- Special key cases:
  - `store_id` plus `date` joins `footfall_daily` to the bills of that store and day.
  - `location_id` in `stock_snapshot` is a store id or `WH-KOL`. The warehouse is not in `stores`.
- Integrity checks that passed:
  - Every bill has at least one line, and every line has a bill.
  - Every SKU in any table exists in `items`.
  - Every store in any table exists in `stores`.
  - No duplicate bill ids.
  - No duplicate keys in snapshot, weekly stock, footfall, roster or calendar.
  - Every bill's salesperson belongs to the store on the bill.
  - Every bill date in the roster window has a matching roster row for that person.
  - No line sold before its SKU launch date.
  - No selling price above MRP, no non-packaging line at Rs 0, and no line MRP that disagrees with the item MRP.
- The joins are clean, so the data is usable without any repair work on keys. The caveat is the IDs-as-text rule: IDs must be read as strings, or tools will convert them to numbers or dates.

---

## 4. What the data can answer

### For Problem A (Store Coach)

- **More bills (conversion).**
  - Bills per store per day divided by footfall per store per day, with peer comparison within store, city and state.
  - Salesperson presence from the roster, matched to footfall and bills.
  - Whether a good salesperson has stopped appearing: roster for May to Oct 2026, bills for the full period.
  - Whether a whole city is slowing, which indicates a market problem and not a store problem. This needs city roll-ups of bills and footfall over time.
- **Bigger baskets (items per bill).**
  - Items per bill excluding packaging.
  - Cross-sell pairs, since the brief names the targets: safa, mojari or mala with a sherwani, and a jacket with a kurta. The category column makes this possible.
  - Categories a salesperson avoids that their city buys.
  - Discount depth per salesperson and store, from MRP and selling price. Only a minority of lines carry any discount, so discounting is a distinct behaviour that can be profiled.
- **More repeat customers.**
  - Customer id gives first bill date and later bills, which supports the brief's definition: a customer billing again 30 or more days after their first bill.
  - Customers can be linked to their salesperson and store, so role models whose customers return can be named.
  - A customer's bills can span stores. Some customers appear in more than one store, so repeat has to be defined at the right level (store versus company).
  - Wedding purchases: a customer who bought around a wedding date last season can be listed for a call. This is the brief's own example.
- **Not a problem (must not alert).**
  - Festival and wedding seasonality: use `calendar`.
  - Regional taste differences: category mix by state and city.
  - A number that cannot be right: see the data issues in section 6. The brief says to flag these as data issues and not to alert the area manager.
- **Constraints the data enforces.**
  - Recipients are 6 area managers with a cap of 5 alerts each per week, so a ranking by rupees at stake is needed.
  - Salespeople get a card of 60 words or fewer: one behaviour, a peer from the same store, one action.
  - The "follow up a week later" requirement needs a way to store the previous recommendation and re-measure.

### For Problem B (Stock Mover)

- **Velocity.** Units sold per store per SKU (or style and size) per day, from `bill_lines` joined to `bills`. Cover is stock divided by daily velocity.
  - Stock-outs censor velocity: use `stock_weekly.days_in_stock` to know when sales were not possible.
  - Use style-level and size-level views. Size matters because "right size" is in the brief's title.
- **Warehouse to store.** Warehouse on hand, plus the inbound schedule, against store need and capacity. Lead time is by zone, so a southern store needs stock 3 days earlier than an eastern one for the same decision date.
- **Under-stocked stores.** Stores whose SKUs show stock-out days while they were selling.
- **Store to store.** Donor stores need 30 or more days of cover after the move, must stay above the minimum display, and cannot be S++ top-20 styles. Lead time depends on same city, same zone or different zone.
- **Ageing stock.** `oldest_stock_received_on` gives the age of the oldest unit. Core versus fashion styles (`is_core_style`, `launch_date`) matters because fashion styles have a limited run.
- **Approvals.** Moves above Rs 1,00,000 at MRP need a human, so the output needs that flag.
- **Capacity.** Stock on hand plus in transit plus any proposed inbound against `stock_capacity_units`.
- **Explainability.** Every move needs a one-line reason, and a merchandiser should be able to approve the list in about 10 minutes.

---

## 5. What the data cannot tell us (gaps)

- No time of day on bills. The brief's example action ("keep six people on the floor this Saturday and Sunday, 4 to 8 pm") cannot be derived from this data. Day-level actions are possible, hour-level actions are not.
- No exit dates for salespeople. A leaver has to be inferred from when their bills and roster rows stop.
- No returns, cancellations or exchanges, so net sales cannot be measured.
- No customer attributes beyond the hashed id (no age, occasion or product intent), so wedding buyers are an inference from calendar timing.
- No per-store assortment or planogram, no display data, and no actual stock-out reasons.
- No stock history before the last 12 weeks, and no stock history for the warehouse. Velocity must come from sales, not stock movement.
- Roster covers only 6 months. Any staffing analysis that compares across years is not possible.
- No real transport cost (the brief says to ignore it).
- No indication of which style-size combinations each store is meant to carry. The weekly stock table shows which pairs existed, but not which ones should.
- Warehouse inbound is only "Planned". There is no delay history and no supplier information.
- The Excel file (`manyavar_data.xlsx`) mentioned in the README is not in our folder. The CSVs are the same data, so nothing is missing.

---

## 6. Data quality: issues that exist in the data

The README states nothing has been cleaned. These are the issues found with simple integrity checks. Each is a trap to handle explicitly, and some are probably planted on purpose.

- **A placeholder customer.** One customer id (`C99999999`) has 1,833 bills, across many stores and the full 24 months. Every other customer has at most 7 bills.
  - This is almost certainly a catch-all id used when no phone number is captured.
  - It must be excluded from repeat-customer and loyalty logic, or it will distort them badly.
- **Broken footfall at PAT-03.** Footfall is recorded as 0 on 12 days in October 2026 (5 to 16 Oct) while bills were still made on 11 of those days. Bills cannot exceed walk-ins, so this is a counter fault.
  - Conversion for that store and period must be flagged as a data issue and not as a performance problem.
- **Days with footfall but no bills.** There are 1,266 store-days where footfall is above 0 and zero bills exist. These are concentrated in the smaller stores (KNP-02, KNP-03, LKO-03, MYS-01, MYS-02, MZF-01, MZF-02, PAT-03, PAT-04).
  - It is not yet known whether this is genuine low conversion or missing bills. It needs a check before conversion is trusted.
- **Over-capacity store.** KNP-03 holds about twice its stated capacity (250 units capacity). A single SKU (`SHW-02-L`) shows 300 units on hand at KNP-03, and its weekly stock row for the same date shows 0.
  - This looks like a keying error (300 instead of a small number or 3). It also sits in the smallest tier and would distort any move recommendation.
- **A negative stock value.** `KUR-02-M` at MYS-02 shows on-hand of -4. Stock cannot be negative. This is a plain data issue.
- **Snapshot versus weekly mismatch.** The last weekly row (31 Oct) and the snapshot should agree for the same store and SKU. They agree on all but 2 of the 3,407 pairs that appear in both, and those 2 are the issues above.
- **Absent rows mean zero stock.**
  - The snapshot has no rows for store-SKU pairs with no stock and nothing in transit. The weekly table has rows for them (zero on hand).
  - 28 snapshot rows have zero on hand with stock in transit (their oldest-received date is blank by design).
  - Treat a missing snapshot row as zero stock, not as unknown.
- **A very under-stocked store.** MZF-01 (an A-tier store with 350 capacity) holds roughly a third of that capacity and carries far fewer SKUs than comparable stores. This is a candidate real problem for Problem B, not an error. It is the sort of thing the hidden test probably wants found.
- **A new store with partial data.** BLR-05 opened 10 Oct 2026 (22 days of footfall and bills) but the roster has rows from 25 Sep 2026. It has no history, so velocity and peer comparisons for it need special handling. It must not be flagged as "slow".
- **Roster versus bills.** Six bills in the roster window were made by a salesperson marked Off that day. This is minor and probably a roster or bill-date error.
- **Salespeople with no roster rows.** 35 of 175 salespeople never appear in the roster. In nearly all cases their last bill is before May 2026, so they are leavers. A few have bills as late as Feb to Apr 2026, which fits attrition during the year. One person (SP1138, joined 23 Jun 2026) has no bills at all.
- **Packaging rows.** Three packaging SKUs have no launch date and MRP equal to cost (both 0). Packaging appears as lines on bills and must be excluded from items per bill and from velocity.
- **Zero-sales SKUs.** 12 non-packaging SKUs never sold in the whole period. Not every one can be called dead stock. Some are new styles (the latest launch is Sep 2026), so check launch date and stock presence first. That is the brief's warning about zero sales.
- **Coverage mismatches across stock tables.** The snapshot covers 353 SKUs, weekly stock covers 372, and inbound covers 201. Of the inbound SKUs, 68 have no warehouse stock today, so they are fully new supply.
- **Naming mismatch.** `min_display` merges Safa, Mala and Stole into one category. `items` keeps them separate.
- **Format traps.** IDs are text. Dates are year-month-day. Opening a CSV in Excel by double-click can corrupt the IDs.

---

## 7. Fit to each problem

### Problem A: Store Coach

- Data supports it well. Footfall, bills, lines, roster, salespeople and calendar cover all three levers.
- Strengths:
  - Two full years of bills and footfall, which gives enough history to separate normal seasonality from real change.
  - Salesperson on every bill, so individual behaviour is measurable.
  - A roster for staffing questions.
  - A festival and wedding calendar by state, so false alarms can be filtered.
- Risks and limits:
  - No time of day, so only day-level staffing actions are possible.
  - Roster only covers 6 months.
  - Footfall counts families as one entry each, so conversion is not a pure percentage of buyers.
  - Placeholder customer and PAT-03 footfall fault must be handled.
  - Hard output constraints: at most 5 issues per manager per week, 60-word salesperson cards, a one-week follow-up.
- Judging in the brief: the hidden problems are checked and numbers are spot-checked ("wrong numbers cost more than missing features"). So correctness of the numbers matters more than breadth.

### Problem B: Stock Mover

- Data supports it, but with more constraints. The inputs are less rich than the transaction side.
  - Stock history is only 12 weeks and the snapshot is a single day.
  - There is one warehouse and 5 inbound delivery dates.
- Strengths:
  - Explicit rules, minimums, lead times and protected styles are given as data, so rule violations are checkable.
  - Stock-out days per week make velocity correction possible.
  - Stock age is available per SKU and location.
- Risks and limits:
  - Every rule must hold at once on every move. A single violation counts against the output.
  - The data errors in section 6 (KNP-03, MYS-02, negative stock) could trigger a wrong move.
  - Velocity must come from sales and be corrected for stock-outs, or understocked stores will look slow.
  - The 12-week stock window is shorter than the sales history, so seasonality for stock must come from the sales side and the calendar.

### Overlap

- Both use `stores`, `items`, `bills`, `bill_lines` and `calendar`. The sales pipeline (clean bills, drop packaging, join to items and stores) is shared work.
- Problem A leans on people and footfall data. Problem B leans on stock and rules data.
- Both require a run-on-its-own daily output, and both will be spot-checked for number accuracy.

---

## 8. Hypotheses to test in the analysis phase (not findings)

These are things the data's structure suggests might be planted. None has been tested.

- A salesperson who left or who misses shifts at a high-performing store (roster and bills).
- A store with steady footfall but falling conversion.
- A city-wide slowdown that is a market effect, not a store effect.
- Salespeople who rarely attach safa, mojari or mala to sherwanis, or a jacket to a kurta.
- A salesperson who discounts far more than their store's norm.
- A store or salesperson whose customers do not come back, and role models whose customers do.
- Festival and wedding swings that look like problems but are not.
- A store with stock in the wrong sizes, so sizes sell out while others sit.
- A core style stocked out in one store while another store holds surplus.
- Fashion styles ageing in stores where they do not sell.
- Stock sitting in a protected top-20 style that a naive system would move.
- A store at or over capacity that cannot take more, and a store far below capacity that needs stock (KNP-03 and MZF-01 are early candidates).
- Warehouse stock that is not enough for every store, forcing a prioritisation decision.
- Stock already in transit that a naive system would send again.
- A new store (BLR-05) with no history that needs a starting assumption.

---

## 9. Suggested first steps (once the analysis phase starts)

- Load everything as text and cast numbers explicitly.
- Build one clean sales table: bills joined to lines, items and stores, packaging removed, placeholder customer flagged.
- Build one store-day table: footfall, bills, roster presence, festival and wedding flags. Flag the PAT-03 fault.
- Build one stock table: snapshot with missing rows filled as zero, joined to weekly history, in-transit and the min-display group mapping.
- Decide which problem the team is solving, because the rest of the work diverges from there.
- Keep a written list of every data issue found, because both briefs reward flagging data problems and not acting on them.
