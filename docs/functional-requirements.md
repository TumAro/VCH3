# Functional requirements: Manyavar VCH3 (Store Coach or Stock Mover)

This document says what the system must do. It does not say how. It covers both problems because the team has not yet chosen between them.

Sources: `data/README.md`, `briefs/A_Store_Coach_brief.pdf` ("Brief A"), `briefs/B_Stock_Mover_brief.pdf` ("Brief B"), `data/csv/*.csv`, and `docs/data-usability-report.md` ("DUR"). Each requirement names its source in brackets after the text.

Conventions:
- "Must" is mandatory. "Should" is expected unless the team writes down a reason not to do it.
- "Today" means the close of 31 Oct 2026, the as-of date of the data [README]. The first run date is 1 Nov 2026.
- Money is in Rs and includes GST [README, both briefs].
- Requirement IDs: `FR-COM` shared, `FR-A` Store Coach, `FR-B` Stock Mover, `FR-DQ` data quality, `AC` acceptance, `OOS` out of scope, `GAP` data gaps.

---

## 1. Shared foundation requirements

### 1.1 Data ingestion

- **FR-COM-01** The system must load all 17 tables from `data/csv/` without manual steps. [README "What is in this pack"]
- **FR-COM-02** The system must read every ID column (`store_id`, `bill_id`, `sku_id`, `style_id`, `salesperson_id`, `customer_id`, `area_manager_id`, `location_id`) as text, with no conversion to numbers or dates. [README "Things people get wrong" #13]
- **FR-COM-03** The system must parse all dates as year-month-day (`YYYY-MM-DD`). [README #12]
- **FR-COM-04** The system must cast number columns explicitly (`qty`, `mrp`, `selling_price`, `footfall`, `on_hand`, `in_transit`, `closing_on_hand`, `days_in_stock`, `stock_capacity_units`, `min_display_units`, `days`, `max_alerts_per_week`, `cost_price`). Any value that will not cast must be logged as a data issue (see FR-COM-14). [README "Loading it"]
- **FR-COM-05** The system must join tables only on the documented keys: `store_id`, `bill_id`, `sku_id`, `salesperson_id`, `area_manager_id`, `state`, `style_id`, and `store_id` + `date` for footfall. [README "How the tables join", brief data guide figure]
- **FR-COM-06** The system must treat `stock_snapshot.location_id = WH-KOL` as the warehouse. It must not look the warehouse up in `stores`. [README #6]
- **FR-COM-07** The system must split `area_managers.stores` (a comma-separated list in one cell) into individual store IDs. Any disagreement with `stores.area_manager_id` must be logged. [README #11]

### 1.2 Shared derived values

- **FR-COM-08** Line revenue must be `qty × selling_price`. Bill value must be the sum of its line revenues. [README #2, both briefs "Good to know"]
- **FR-COM-09** Discount per unit must be `mrp − selling_price`. [README #3, `bill_lines` dictionary]
- **FR-COM-10** Lines where `items.is_packaging = 1` (`PKG-BAG`, `PKG-COVER`, `PKG-BOX`) must be excluded from item counts, items per bill, category mix and sales velocity. [README #4, `items.is_packaging`]
- **FR-COM-11** The system must group SKUs into styles with `style_id`, and must be able to report at both SKU (style + size) level and style level. [`items.style_id`]
- **FR-COM-12** The system must map Safa, Mala and Stole from `items.category` to the single `min_display` category "Accessories (Safa/Mala/Stole)" whenever it compares against minimum display. [README #9, `min_display.csv`]
- **FR-COM-13** The system must attach to every store-date the festival name and `is_wedding_date` from `calendar`, joined on the store's `state`. [`calendar`, README "How the tables join"]

### 1.3 Data-issue flagging

- **FR-COM-14** The system must keep a data-issue log. Each entry must hold: table, key (for example store + date or location + SKU), column, value seen, the rule it breaks, and the action taken (excluded, capped, or kept and flagged). [Brief A "A number that can't be right. Flag it as a data issue"; README "Blank cells"]
- **FR-COM-15** No value logged as a data issue may drive an alert (A) or a move (B) unless the log says how it was neutralised. [Brief A "don't alert the area manager"; Brief B "Check before you trust"]
- **FR-COM-16** The data-issue log must be published with each daily run, separate from the alerts or the move list. [Brief A, Brief B judging]

### 1.4 Scheduling and the daily autonomous run

- **FR-COM-17** The system must run once a day on a schedule, with no person asking it a question or starting it. [Brief A "Run on its own every day"; Brief B "Every day…", "We check that it runs on its own"]
- **FR-COM-18** Each run must take an as-of date. Given the same data and the same as-of date, it must produce the same output. [Brief A/B "We spot-check your numbers"]
- **FR-COM-19** Each run must write its output to a fixed, dated location (one output set per run date) that a reviewer can open without running code. [Brief B "A merchandiser could approve your list in ten minutes"]
- **FR-COM-20** Each run must record: run date, as-of date, input files read with row counts, number of outputs produced, number of data issues logged, and success or failure. [Brief A/B "runs on its own"]
- **FR-COM-21** A failed run must leave the previous day's output untouched and record the failure reason. [FR-COM-17]

### 1.5 Output ranking and caps

- **FR-COM-22** Every output item (alert or move) must carry a rupee value used for ranking. [Brief A "ranked by rupees at stake"; Brief B `rules` Approval "worth … at MRP"]
- **FR-COM-23** Outputs must be sorted by that rupee value, highest first. [Brief A]
- **FR-COM-24** Hard caps from the briefs and rules tables must be enforced at output time, after ranking, and never relaxed to fit more items in. [Brief A "at most 5", `area_managers.max_alerts_per_week`; Brief B `rules`]

### 1.6 One-line explanations

- **FR-COM-25** Every output item must carry a one-line, plain-language reason that quotes the numbers behind it. [Brief B "Explain every move in one line"; Brief A "names the lever, the cause and one action"]
- **FR-COM-26** Every number quoted in an explanation must be traceable to its source rows (store, SKU or salesperson, and date range), so a reviewer can recompute it. [Brief A/B "We spot-check your numbers"]

### 1.7 Follow-up loop

- **FR-COM-27** The system must store every output item it issues, with its ID, issue date, the metric it targets and that metric's baseline value. [Brief A "Follow up: a week later"]
- **FR-COM-28** Seven days after an item is issued, the system must re-measure the targeted metric and report "moved / did not move", with before and after values. [Brief A "check whether the number moved, and say so"]
- **FR-COM-29** If the follow-up window extends past the last date in the data, the system must report "not yet measurable" instead of a result. [GAP-01; data ends 31 Oct 2026]

---

## 2. Problem A: Store Coach

Goal: "Every morning, without anyone asking, tell each area manager which stores need attention and why, and tell each salesperson one thing to do better today." [Brief A]

Tables: stores, area_managers, salespeople, roster_daily, footfall_daily, bills, bill_lines, items, calendar. [README "Which files you need"]

### 2.1 Lever metrics

- **FR-A-01** Conversion must be bills ÷ footfall for a store-day, computed from `bills` (count of `bill_id`) and `footfall_daily.footfall`. [Brief A "CONVERSION Bills ÷ footfall"]
- **FR-A-02** Items per bill must be the sum of non-packaging `qty` on a bill. It must be computable per store and per salesperson. [Brief A "ITEMS PER BILL"; README #4]
- **FR-A-03** A return customer must be one who bills again 30 or more days after their first bill. The system must state whether "first bill" is counted per store or company-wide and use that consistently. [Brief A "A customer billing again 30+ days after their first bill"; `bills.customer_id` "same ID across visits and stores"]
- **FR-A-04** All three levers must be available per store, per salesperson, per city and per state, over any date range in the data. [Brief A "Look at every store and every salesperson through these three levers"]

### 2.2 Fair comparison

- **FR-A-05** A salesperson must be compared against peers in the same store, city and state, never against the whole country. [Brief A "Compare fairly"]
- **FR-A-06** A store must be compared against stores in its own city and state, and against its own history for the same festival or wedding period. [Brief A "Not a problem: Normal festival and season swings · Regional taste differences"]

### 2.3 Problems the system must detect

More bills:
- **FR-A-07** Detect a good salesperson who has left or keeps missing shifts, from `bills.salesperson_id` activity and `roster_daily.status`. [Brief A "A good salesperson has left or keeps missing shifts"]
- **FR-A-08** Detect too few people on the floor on busy days, by comparing `roster_daily` Present count with footfall on those days. [Brief A "Too few people on the floor on busy days"]
- **FR-A-09** Detect stores where walk-ins are steady but fewer of them buy (footfall flat, conversion down). [Brief A "Walk-ins steady but fewer of them buying"]
- **FR-A-10** Detect a whole city slowing down and label it a market problem. It must not be raised as one store's problem. [Brief A "A whole city slowing down (that's a market problem, not one store's)"]

Bigger baskets:
- **FR-A-11** Detect salespeople not adding the obvious pair: Safa, Mojari or Mala with a Sherwani; Jacket with a Kurta Set. [Brief A "Salespeople not adding the obvious pair"; `items.category`]
- **FR-A-12** Detect a salesperson avoiding a category that their city buys. [Brief A]
- **FR-A-13** Detect discounts well above the store's norm, per salesperson, using FR-COM-09. [Brief A "Discounts well above the store's norm"]

More repeat:
- **FR-A-14** Detect stores or salespeople whose customers do not come back. [Brief A "More repeat"]
- **FR-A-15** Name role models whose customers do come back, so others can learn from them. [Brief A "Role models whose customers do. Name them"]

Not a problem:
- **FR-A-16** The system must not alert on normal festival or season swings, using `calendar.festival` and `calendar.is_wedding_date` for the store's state. [Brief A "Not a problem"]
- **FR-A-17** The system must not alert on regional taste differences (category mix that differs by city or state). [Brief A]
- **FR-A-18** A number that cannot be right must be flagged as a data issue (FR-COM-14). It must not be sent to the area manager. [Brief A]

### 2.4 Area manager alerts

- **FR-A-19** Alerts must go to each of the 6 area managers in `area_managers`, covering only the stores they look after. [`area_managers`, `stores.area_manager_id`]
- **FR-A-20** An area manager must receive at most `max_alerts_per_week` issues per rolling week (5 for every manager in the data). Daily runs must share that weekly budget. [Brief A "at most 5 issues a week"; `area_managers.max_alerts_per_week`]
- **FR-A-21** Issues must be ranked by rupees at stake, highest first, before the cap is applied. [Brief A "ranked by rupees at stake"]
- **FR-A-22** Each issue must name the lever (more bills, bigger baskets or more repeat), the cause and exactly one action. [Brief A "Each issue names the lever, the cause and one action"]
- **FR-A-23** Each issue must show its rupees-at-stake figure and how it was reached in one line. [FR-COM-25, FR-COM-26]

### 2.5 Salesperson cards

- **FR-A-24** Each active salesperson must receive one card per day. [Brief A "tell each salesperson one thing to do better today"]
- **FR-A-25** A card must be 60 words or fewer. [Brief A "a card of 60 words or fewer"]
- **FR-A-26** A card must hold exactly: one behaviour, one named peer from the same store, and one action for today. [Brief A]
- **FR-A-27** The named peer must be a salesperson in the same `store_id` who is still active (FR-DQ-11). [Brief A "a peer from the same store"]
- **FR-A-28** No card may go to a salesperson inferred to have left. [GAP-02, FR-DQ-11]

### 2.6 Action rules

- **FR-A-29** Every action must be doable today by the store with the people and stock it already has: no budget, no approval, no new system. [Brief A "Every action must be easy to do"]
- **FR-A-30** Every action must name who, what and when. An alert without a nameable action must not be sent. [Brief A "If you can't name the action, the alert isn't ready to send"]
- **FR-A-31** Staffing actions must be at day level (for example a named day and a named person's weekly off). They must not state an hour range, because bills carry no time of day. [GAP-01; Brief A example "Saturday and Sunday, 4–8 pm"]
- **FR-A-32** A customer call-list action must give a count and a defined list of `customer_id`s (for example customers who bought near a wedding date last season and have not returned). [Brief A "Call the 15 customers who bought for a wedding last season and haven't been back"]

### 2.7 Follow-up

- **FR-A-33** A week after each alert or card, the system must report whether the targeted lever metric moved for that store or salesperson (FR-COM-27 to FR-COM-29). [Brief A "Follow up"]

---

## 3. Problem B: Stock Mover

Goal: "Every day, find stock that's in the wrong place. Produce a ready-to-approve list: what to send from the warehouse, what to move between stores, and what to pull back." [Brief B]

Tables: stores, items, bills, bill_lines, stock_snapshot, stock_weekly, warehouse_inbound, calendar, rules, min_display, lead_times, flagship_protected. [README "Which files you need"]

### 3.1 Velocity and cover

- **FR-B-01** The system must compute velocity (units sold per day) for each store × SKU, from non-packaging `bill_lines.qty` joined to `bills.store_id` and `bills.bill_date`. It must also roll this up to store × style. [Brief B "Velocity is how fast each style and size sells in each store"]
- **FR-B-02** Velocity must not treat days with no stock as zero-demand days. It must use `stock_weekly.days_in_stock` to tell "not sold" from "not there". [Brief B "A product with zero sales isn't always a slow product. Check before you trust"; `stock_weekly.days_in_stock`]
- **FR-B-03** Cover must be stock ÷ daily velocity, in days. Stock means `on_hand` plus `in_transit`. [Brief B "Cover is stock ÷ daily velocity"; `rules` In-transit]
- **FR-B-04** A store × SKU pair with no `stock_snapshot` row must be treated as 0 on hand and 0 in transit. [DUR §6 "Absent rows mean zero stock"]
- **FR-B-05** Stock age must be today minus `stock_snapshot.oldest_stock_received_on`. [`stock_snapshot` dictionary "Use it to work out stock age"]

### 3.2 Move types the system must produce

- **FR-B-06** Warehouse → store: what to send from `WH-KOL`, to which store, and when, including when there is not enough for every store. [Brief B "WAREHOUSE → STORE … when there isn't enough for everyone"]
- **FR-B-07** Warehouse supply must include `stock_snapshot` on hand at `WH-KOL` and `warehouse_inbound` quantities by `expected_date`. No unit may be allocated before its expected date. [`warehouse_inbound`]
- **FR-B-08** Under-stocked stores: list stores that would sell more if they held more. [Brief B "UNDER-STOCKED STORES"]
- **FR-B-09** Store → store: move stock from where it sits to where it sells. [Brief B "STORE → STORE"]
- **FR-B-10** Ageing stock: move or pull back ageing stock to where it sells before it is too late, taking account of `items.is_core_style` (0 = limited-run fashion style). [Brief B "AGEING STOCK"; `items.is_core_style`]

### 3.3 Hard rules (every move must pass every rule)

- **FR-B-11 Minimum display.** No move may leave a giving store below `min_display_units` for its `tier` and category. Safa, Mala and Stole count together as "Accessories (Safa/Mala/Stole)" (FR-COM-12). [`rules` Minimum display; `min_display.csv`]
- **FR-B-12 Capacity.** No move may take a receiving store's on hand + in transit + all inbound moves in the list above `stores.stock_capacity_units`. [`rules` Capacity]
- **FR-B-13 Flagship protection.** No move may take stock of a `flagship_protected.style_id` out of its S++ `store_id` (LKO-01, PAT-01, BLR-01, BLR-02, top-20 each). This applies to every size of the style. [`rules` Flagship protection; `flagship_protected`]
- **FR-B-14 In transit.** Stock in transit counts as arriving. The system must not send units that duplicate what is already in transit to that store. [`rules` In-transit]
- **FR-B-15 Donor cover.** No store-to-store move may leave the giving store with under 30 days of cover for that style. [`rules` Donor cover]
- **FR-B-16 Approval threshold.** Any single move worth more than Rs 1,00,000 at MRP (`qty × items.mrp`) must be flagged "needs human approval". [`rules` Approval]
- **FR-B-17 Lead times.** Every move must carry an arrival date equal to dispatch date + lead time from `lead_times`, derived from the stores' `zone` and `city`:
  - Warehouse WH-KOL to store, East zone (Bihar): 3 days
  - Warehouse WH-KOL to store, North zone (UP): 4 days
  - Warehouse WH-KOL to store, South zone (Karnataka): 6 days
  - Store to store, same city: 2 days
  - Store to store, same zone, different city: 4 days
  - Store to store, different zone: 7 days
  [`rules` Logistics cost; `lead_times.csv`; README #10]
- **FR-B-18 Transport cost.** Transport cost must not affect any move. [`rules` Logistics cost "Ignore transport cost"]
- **FR-B-19 Replenishment day.** The system may recommend a move on any day. It must not assume Monday-only dispatch. [`rules` Replenishment cycle]
- **FR-B-20** A move must never send more units than the giving location has on hand. [`stock_snapshot.on_hand`]

### 3.4 The move list

- **FR-B-21** Each move must state: move type (warehouse→store, store→store, pull back), from location, to location, `sku_id` and `style_id`, quantity, value at MRP, dispatch date, arrival date, approval flag, and a one-line reason. [Brief B "ready-to-approve list"; FR-COM-25]
- **FR-B-22** The one-line reason must quote the figures behind the move (for example the receiver's cover and the giver's cover after the move). [Brief B "Explain every move in one line"]
- **FR-B-23** The list must be ordered and sized so a merchandiser can approve it in about ten minutes. Moves needing approval (FR-B-16) must be grouped together. [Brief B "approve your list in ten minutes"]
- **FR-B-24** Each run must output a rule-check summary: for each rule FR-B-11 to FR-B-17, the number of moves checked and the number of violations. The violation count must be 0. [Brief B "we check that no rule is broken"]

### 3.5 Follow-up

- **FR-B-25** Seven days after a move is issued, the system should report whether the receiver's cover or stock-out days and the giver's ageing stock changed (FR-COM-27 to FR-COM-29). [Brief A follow-up practice, applied to B; optional for B]

---

## 4. Data-quality handling requirements

Each item below is a known issue in the data (DUR §6). The system must detect it by rule, not by hard-coding the ID, and log it under FR-COM-14.

- **FR-DQ-01 Placeholder customer.** Customer IDs with implausibly many bills (for example `C99999999`, 1,833 bills across many stores) must be excluded from repeat, loyalty and call-list logic. [DUR §6; Brief A "A number that can't be right"]
- **FR-DQ-02 Bills without footfall.** Store-days with footfall 0 and bills above 0 (for example PAT-03, 5 to 16 Oct 2026) must be flagged as a counter fault and dropped from conversion. [DUR §6; FR-A-01]
- **FR-DQ-03 Footfall without bills.** Store-days with footfall above 0 and zero bills (1,266 store-days, mostly smaller stores) must be flagged for review. They must not count as poor conversion until checked. [DUR §6]
- **FR-DQ-04 Negative stock.** `on_hand` < 0 (for example `KUR-02-M` at MYS-02, -4) must be logged and treated as unknown. The pair must not give or receive in any move. [DUR §6]
- **FR-DQ-05 Snapshot versus weekly mismatch.** Where the 31 Oct `stock_weekly.closing_on_hand` differs from `stock_snapshot.on_hand` for the same store × SKU (for example `SHW-02-L` at KNP-03: 300 vs 0), the pair must be logged and excluded from moves. [DUR §6]
- **FR-DQ-06 Over capacity.** A store whose on hand exceeds `stock_capacity_units` (KNP-03) must be flagged. Once any FR-DQ-05 suspect values are removed, it must still be blocked from receiving if it is at or over capacity. [DUR §6; `rules` Capacity]
- **FR-DQ-07 New store.** A store opened inside the analysis window (BLR-05, opened 10 Oct 2026) must not be flagged as slow or poorly converting for lack of history. Velocity or peer figures for it must be marked "insufficient history". [DUR §6; `stores.opened_on` "One store is brand new"]
- **FR-DQ-08 Zero-sales SKUs.** A SKU with zero sales must be checked against `launch_date` and `days_in_stock` before it is called slow or dead stock. [Brief B "zero sales isn't always a slow product"; DUR §6]
- **FR-DQ-09 Bill by an Off salesperson.** A bill made by a salesperson marked Off that day (6 cases) must be logged. It must not count as a missed shift. [DUR §6]
- **FR-DQ-10 Packaging rows.** Packaging SKUs with blank `launch_date` and Rs 0 MRP and cost must not raise launch-date or zero-price errors. [DUR §6; README #4]
- **FR-DQ-11 Leavers.** With no exit date, a salesperson must be treated as left when they have no bills and no Present roster rows for a defined recent period. The rule and its cut-off must be written in the run log. [`salespeople` "No exit date is recorded"; DUR §6]
- **FR-DQ-12 Accessories naming.** The Safa/Mala/Stole to "Accessories" mapping (FR-COM-12) must be checked at load. Any `items.category` that maps to no `min_display` category (other than Packaging) must be logged. [README #9]
- **FR-DQ-13 Blank cells.** `calendar.festival` blank means no festival. `stock_snapshot.in_transit_arrives_on` blank means nothing in transit. `oldest_stock_received_on` blank with `on_hand = 0` is expected. Any other blank must be logged. [README "Blank cells"]
- **FR-DQ-14 Range checks.** At load, the system must check and log: `qty` ≤ 0, `selling_price` > `mrp`, non-packaging line at Rs 0, `days_in_stock` outside 0–7, `footfall` < 0, and `bill_date` before the SKU's `launch_date`. [data dictionary column definitions]
- **FR-DQ-15 Unknown keys.** Any `store_id`, `sku_id`, `salesperson_id` or `bill_id` that does not join to its parent table must be logged and excluded. [README "How the tables join"]

---

## 5. Acceptance criteria and verification

### 5.1 Numbers are right (spot checks)

- **AC-01** For 10 randomly chosen store-days, conversion, bill count and footfall shown by the system match a hand calculation from `bills` and `footfall_daily`. Verifies FR-A-01. [Brief A "We spot-check your numbers"]
- **AC-02** For 10 random bills, the items-per-bill and bill value shown match a hand sum of their `bill_lines`, with packaging excluded. Verifies FR-COM-08, FR-COM-10, FR-A-02.
- **AC-03** For 5 random customers, the repeat flag matches a hand check of their bill dates against the 30-day rule. Verifies FR-A-03.
- **AC-04** For 10 random store × SKU pairs, velocity, cover and stock age match a hand calculation from the source rows. Verifies FR-B-01 to FR-B-05. [Brief B "We spot-check your numbers"]
- **AC-05** For every rupee figure quoted in an alert or move, a reviewer can find the source rows from the explanation alone. Verifies FR-COM-26.

### 5.2 Rules are kept (compliance checks)

- **AC-06** A rule checker run over the full move list reports 0 violations for minimum display, capacity, flagship protection, in transit, donor cover and lead times. Verifies FR-B-11 to FR-B-17 and FR-B-24. [Brief B "we check that no rule is broken"]
- **AC-07** Every move with `qty × mrp` > Rs 1,00,000 carries the approval flag, and no move at or below that value does. Verifies FR-B-16.
- **AC-08** No move's arrival date differs from dispatch date + the `lead_times` days for its route. Verifies FR-B-17.
- **AC-09** No area manager has more than 5 issues in any rolling 7 days. Verifies FR-A-20.
- **AC-10** Every salesperson card has 60 words or fewer (counted automatically), names a peer from the same store, and holds exactly one action. Verifies FR-A-25 to FR-A-27.
- **AC-11** Every A action names who, what and when, needs no budget, approval or new system, and states no hour range. Verifies FR-A-29 to FR-A-31. [Brief A "We check that every action is one a store could carry out today"]
- **AC-12** Each area manager's issues are in descending rupee order. Verifies FR-A-21, FR-COM-23.

### 5.3 Hidden problems found, false alarms avoided

- **AC-13** Every known data issue in §4 shows up in the data-issue log, and none of them drives an alert or a move. Verifies FR-COM-14, FR-COM-15 and FR-DQ-01 to FR-DQ-15.
- **AC-14** For each cause type in FR-A-07 to FR-A-15 (A) or each move type in FR-B-06 to FR-B-10 (B), the team can show at least one output item, or a written statement that none was found and why. [Brief A/B "We check whether your system found it and named the right cause"]
- **AC-15** No alert is raised whose only cause is a festival or wedding swing, or a city-wide drop attributed to one store. Verifies FR-A-10, FR-A-16.

### 5.4 Runs on its own

- **AC-16** The scheduled run fires on its own on at least two consecutive days and produces dated outputs and run logs, with nobody prompting it. Verifies FR-COM-17, FR-COM-19, FR-COM-20. [Brief A/B "We check that it runs on its own"]
- **AC-17** Running twice with the same as-of date gives identical outputs. Verifies FR-COM-18.
- **AC-18** A run 7 days after an item is issued produces a follow-up line for that item ("moved", "did not move", or "not yet measurable"). Verifies FR-COM-27 to FR-COM-29, FR-A-33.

---

## 6. Out of scope and known data gaps

### 6.1 Out of scope

- **OOS-01** Building both problems. The team delivers one of A or B. [README "Your team builds on one of them, not both"]
- **OOS-02** Transport cost in any form. [`rules` Logistics cost]
- **OOS-03** Actions that need budget, approval, new hires or a new system (Problem A). [Brief A]
- **OOS-04** Executing moves or sending messages to real people. The system produces lists, alerts and cards. Approval and dispatch are human steps. [Brief B "ready-to-approve list"]
- **OOS-05** Correcting source data. The system flags issues. It does not rewrite the CSVs. [README "Nothing in this data has been corrected or cleaned"]
- **OOS-06** Purchasing or changing `warehouse_inbound` plans. [Brief B scope covers sending, moving and pulling back only]
- **OOS-07** Statistical model choice, forecasting method and thresholds. These belong in design, not in this document.

### 6.2 Known data gaps that limit requirements

- **GAP-01** No time of day on bills. Staffing actions can only be at day level (FR-A-31). Data ends 31 Oct 2026, so follow-ups on the first runs cannot be measured until new data arrives (FR-COM-29). [DUR §5]
- **GAP-02** No exit dates for salespeople. Leavers must be inferred (FR-DQ-11). [`salespeople` dictionary]
- **GAP-03** The roster covers only 1 May to 31 Oct 2026. Shift and staffing findings cannot go back further. [README #7]
- **GAP-04** Footfall counts people, and families walk in together. Conversion is bills per walk-in, not per buying party. [`footfall_daily` dictionary]
- **GAP-05** No returns, exchanges or cancellations. All revenue is gross. [DUR §5]
- **GAP-06** No customer attributes. "Wedding buyer" can only be inferred from bill date against `calendar.is_wedding_date`. [DUR §5]
- **GAP-07** Stock history is 12 weeks (15 Aug to 31 Oct 2026), and there is no weekly history for the warehouse. Longer-term demand must come from sales. [`stock_weekly` dictionary]
- **GAP-08** No planned assortment per store. The data does not say which SKUs a store is meant to carry. [DUR §5]
- **GAP-09** `warehouse_inbound` is all "Planned", with no delay history. Inbound is taken as arriving on `expected_date`. [DUR §5]
- **GAP-10** The single stock snapshot means warehouse→store and store→store moves are planned from 31 Oct 2026 positions only. Later runs repeat the same position until new data is loaded. [`stock_snapshot.as_of_date`]
