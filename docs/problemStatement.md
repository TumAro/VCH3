# PDF Brief Conversion

This document converts the points in both participant PDFs into one Markdown reference.

Sources:
- `statement-1.pdf`: Stock Mover (Case study B)
- `statement-2.pdf`: Store Coach (Case study A)

## Shared hackathon context

- One Excel workbook is available, with a CSV copy as the alternate format.
- The dataset contains 20 Manyavar stores and one warehouse.
- Sales run from 1 November 2024 through 31 October 2026.
- Stock is as of the close of 31 October 2026.
- The daily roster covers 1 May through 31 October 2026 only.
- Stock history covers the 12 weeks ending 15 August through 31 October 2026.
- The calendar covers festivals and auspicious wedding dates from November 2024 through December 2026.
- All money is in INR and includes GST.
- Line revenue is `qty × selling_price`; a bill's value is the sum of its line revenues.
- Discount per unit is `mrp − selling_price`.
- `style_id` groups all sizes of a design.
- The data is synthetic; patterns are tuned to real Manyavar data, but no real store, salesperson or customer appears.
- Volumes are scaled down.
- Build approach is open: Claude, artifacts, scheduled tasks, skills or another implementation may be used.
- The system should run autonomously; no person should have to start or query it.
- Judgment emphasizes correct numbers, hard-rule compliance, actionable findings and discovery of hidden problems.
- Every figure should be reproducible from the source rows.

## Data guide

### Table overview

| Table | One row represents | Rows | Primary use |
|---|---|---:|---|
| `stores` | Store | 20 | Store attributes, location, tier, capacity and area manager |
| `area_managers` | Area manager | 6 | Areas, responsible stores and alert readability limit |
| `items` | SKU: style plus size | 385 | Product, category, size, price, launch and style attributes |
| `salespeople` | Salesperson | 175 | People, store assignment and join date |
| `roster_daily` | Salesperson per day | 23,569 | Daily Present or Off status |
| `footfall_daily` | Store per day | 13,892 | Walk-ins counted by the door camera |
| `bills` | Bill | 90,805 | Store, salesperson, customer and sale date |
| `bill_lines` | Item on a bill | 259,772 | Quantity and price for each SKU sold |
| `stock_snapshot` | Location by SKU | 3,547 | Stock, in-transit units and stock age at 31 October 2026 |
| `stock_weekly` | Store by SKU by week | 61,416 | Closing stock and days in stock for the last 12 weeks |
| `warehouse_inbound` | Delivery | 768 | Planned warehouse deliveries starting 1 November 2026 |
| `calendar` | Date by state | 2,373 | Festival and wedding-date context |
| `rules`, `min_display`, `lead_times`, `flagship_protected` | Rule or setting | - | Stock movement rules |

### Join keys

- `store_id` joins `stores` to store-related tables.
- `area_manager_id` joins `area_managers` to `stores`.
- `salesperson_id` joins `salespeople`, `roster_daily` and `bills`.
- `bill_id` joins `bills` to `bill_lines`.
- `sku_id` joins `items`, `bill_lines`, stock tables and `warehouse_inbound`.
- `style_id` groups sizes belonging to the same design.
- `state` joins `stores` to `calendar`.
- `store_id + date` joins daily store activity to `footfall_daily`.
- `location_id` in stock tables is a store ID or `WH-KOL`, the warehouse.

### Stores

- `store_id`: store code in city-number form, for example `LKO-01`.
- `city`, `state`, `zone`: stores span six cities in Uttar Pradesh, Bihar and Karnataka.
- Zones: Uttar Pradesh = North, Bihar = East, Karnataka = South.
- `tier`: S++, S+, A or B; S++ is a super flagship and S+ is a flagship.
- `size_sqft`: store floor area.
- `stock_capacity_units`: maximum physical stock capacity.
- `opened_on`: store opening date; one store is brand new.
- `area_manager_id`: responsible area manager.

### Area managers

- `area_manager_id / name / city`: one area manager per city.
- `stores`: comma-separated responsible store IDs.
- `max_alerts_per_week`: how many alerts an area manager will read in a week.

### Items

- `sku_id`: one style and size combination, for example `KUR-12-XL`.
- `style_id / style_name`: design across all sizes.
- `category`: Sherwani, Indo-Western, Kurta Set, Jacket, Mojari, Safa, Mala, Stole or Packaging.
- `size`: clothing sizes S through XXXL, Mojari sizes 6 through 11, or `FS` for free size.
- `mrp / cost_price`: tag price and illustrative cost; all values include GST.
- `launch_date`: date the style went on sale.
- `is_core_style`: `1` means replenished throughout the year; `0` means a limited-run fashion style.
- `is_packaging`: `1` marks carry bags, garment covers or gift boxes with ₹0 MRP. These are not products.

### Salespeople and roster

- `salesperson_id / store_id / name / join_date`: employee identity and store.
- No salesperson exit date is recorded.
- `roster_daily.date / store_id / salesperson_id`: daily roster row.
- `roster_daily.status`: `Present` or `Off`.

### Footfall, bills and bill lines

- `footfall_daily.date / store_id / footfall`: walk-ins counted by the door camera.
- Families may cause one camera count to represent multiple customers.
- `bills.bill_id / bill_date / store_id`: one row per bill.
- `bills.salesperson_id`: salesperson who made the sale.
- `bills.customer_id`: hashed customer identity; the same customer ID follows visits across stores.
- `bill_lines.bill_id / sku_id / qty`: items included in a bill.
- `bill_lines.mrp / selling_price`: tag price and post-discount selling price.

### Stock tables

- `stock_snapshot.as_of_date`: stock snapshot date.
- `stock_snapshot.location_id`: store or `WH-KOL` warehouse.
- `stock_snapshot.sku_id`: stocked SKU.
- `stock_snapshot.on_hand`: units currently at the location.
- `stock_snapshot.in_transit`: units dispatched but not yet arrived.
- `stock_snapshot.in_transit_arrives_on`: in-transit arrival date.
- `stock_snapshot.oldest_stock_received_on`: oldest receipt date for units on hand.
- `stock_weekly.week_ending`: week ending Saturday; weeks run Sunday to Saturday.
- `stock_weekly.closing_on_hand`: units at Saturday close.
- `stock_weekly.days_in_stock`: number of days in the week that at least one unit was available, range 0–7.
- `warehouse_inbound.expected_date / sku_id / qty / status`: future warehouse delivery and quantity.
- `warehouse_inbound.status` is `Planned` in the supplied data.

### Calendar and stock setting tables

- `calendar.date / state`: date and state-specific festival context.
- `calendar.festival`: festival name, or blank when no festival is recorded.
- `calendar.is_wedding_date`: `1` for an auspicious wedding date, otherwise `0`.
- `min_display`: minimum display units by tier and category.
- `lead_times`: dispatch-to-arrival time by route and zone.
- `flagship_protected.store_id / rank / style_id`: protected top-20 styles for each S++ store.

## Stock Mover: brief requirements

### Objective

Every day, find stock in the wrong place and produce a ready-to-approve list containing:

1. What to send from the warehouse.
2. What to move between stores.
3. What to pull back.

### Velocity and cover

- Velocity is units sold per day for each style and size in each store.
- Compute SKU velocity from sales and roll it up to style level.
- Cover is `stock ÷ daily velocity`, measured in days.
- Stock means on-hand units plus in-transit units.
- Zero sales do not automatically mean low demand: a product may have been out of stock or newly launched.
- Use `stock_weekly.days_in_stock` to distinguish `not sold` from `not available`.
- Use `oldest_stock_received_on` to calculate stock age.

### Move categories

- **Warehouse to store:** state what to send, who should receive it and which stores receive priority when supply is insufficient.
- **Under-stocked stores:** identify stores that would sell more if they held more.
- **Store to store:** move stock from where it sits to where it sells.
- **Ageing stock:** move or pull back ageing stock before it becomes too late, accounting for whether a style is core or fashion.
- **Pull back:** return unsuitable ageing or excess stock to a place where it will sell or the warehouse.

### Hard stock rules

Every move must pass all of these rules:

1. **Minimum display:** the giving store must remain at or above its tier and category minimum display. Safa, Mala and Stole count together under `Accessories (Safa/Mala/Stole)`.
2. **Capacity:** on hand plus in transit plus all inbound moves at the receiving store must stay at or below `stock_capacity_units`.
3. **Flagship protection:** no protected style may leave an S++ flagship. For each protected row, this applies to every size of the style.
4. **In transit:** in-transit units count as arriving; do not send duplicate units to the same store.
5. **Donor cover:** no store-to-store move may leave the giving store below 30 days of cover for that style.
6. **Approval threshold:** a single move above ₹1,00,000 at MRP is worth `quantity × MRP` and must be marked for human approval.
7. **Lead time:** add route lead time to dispatch date to calculate arrival date.
8. **Transport cost:** ignore transport cost in the move decision.
9. **Replenishment cycle:** moves may be recommended on any day; do not assume dispatch only happens on Mondays.
10. **Available supply:** never send more units than the giving location has on hand.

### Lead-time routes

- Warehouse `WH-KOL` to an East-zone store in Bihar: 3 days.
- Warehouse `WH-KOL` to a North-zone store in Uttar Pradesh: 4 days.
- Warehouse `WH-KOL` to a South-zone store in Karnataka: 6 days.
- Store to store in the same city: 2 days.
- Store to store in the same zone but in a different city: 4 days.
- Store to store in different zones: 7 days.

### Warehouse supply

- Include on-hand warehouse stock and planned warehouse inbound.
- Do not allocate inbound units before their `expected_date`.
- If warehouse supply cannot satisfy every under-stocked store, rank and allocate in the order of greatest need or value.

### Required move-list fields

Each move should contain:

- Move type: warehouse to store, store to store or pull back.
- From location.
- To location.
- `sku_id` and `style_id`.
- Quantity.
- Value at MRP.
- Dispatch date.
- Arrival date.
- Human-approval flag.
- One-line reason.

The list should be small enough for a merchandiser to approve in about ten minutes. Moves needing approval should be grouped together. Moves and findings must be ordered by rupee value or stock impact.

### Explanation requirement

- Explain every move in one line.
- Include the numerical facts behind the decision, for example receiver cover before and after, donor cover after the move or ageing age.
- The explanation must match the source calculation and be traceable to store and SKU rows.

### Stock Mover acceptance

- The system found the hidden stock problems.
- Its numbers pass spot checks.
- Every move passes every hard rule.
- The system produces the list on its own.
- It does not treat every zero-sales SKU as slow: launch date and days in stock are checked first.
- It is usable in a ten-minute merchandiser review.

## Store Coach: brief requirements

### Objective

Every morning, tell each area manager which stores need attention and why, and give each salesperson one behaviour to improve today.

### Three levers

#### 1. More bills

- Metric: conversion = bills divided by footfall.
- Find a good salesperson who has left or keeps missing shifts.
- Find too few people on the floor on busy days.
- Find a steady-walk-in store with falling conversion.
- Find a whole city slowing down and label it a market problem rather than a store problem.

#### 2. Bigger baskets

- Metric: items per bill.
- Find salespeople failing to add obvious pairs:
  - Safa, Mojari or Mala with a Sherwani.
  - Jacket with a Kurta Set.
- Find a salesperson avoiding a category that their city buys.
- Find discounts substantially above the store's norm.

#### 3. More repeat

- A return customer is a customer who bills again 30 or more days after their first bill.
- Find stores or salespeople whose customers do not come back.
- Name role-model salespeople whose customers do return so others can learn from them.

### Fair comparison

- Compare a salesperson against peers in the same store, city and state, not against the whole country.
- Compare a store against peers in its own city and state.
- Compare a store with its own history for the same festival or wedding period.
- Do not raise normal festival or seasonal swings as problems.
- Do not raise regional taste differences as problems.

### Not-a-problem conditions

- Normal festival and season swings.
- Regional differences in category mix.
- A number that cannot be right: flag it as a data issue and do not alert the area manager.

## Store Coach output requirements

### Area-manager issues

- Send issues only to the six responsible area managers.
- Limit each area manager to at most five issues per week.
- Rank issues by rupees at stake, highest first.
- Each issue names:
  - Lever: more bills, bigger baskets or more repeat.
  - Cause.
  - Exactly one action.
- Show the rupees-at-stake figure and how it was reached.
- Keep the explanation traceable to the store or salesperson source rows.

### Salesperson cards

- Give each active salesperson one card per day.
- Keep each card to 60 words or fewer.
- Include exactly:
  - One behaviour.
  - A named peer from the same store.
  - One action for today.
- Do not create a card for a salesperson inferred to have left.

### Action quality

Every action must:

- Be doable today with existing people and stock.
- Require no budget, approval or new system.
- Name who should act.
- Name what should be done.
- Name when it should be done.
- Include day-level timing when staffing is involved; bills have no time of day, so do not invent hourly ranges.
- Provide a defined customer ID list and count when retention work is proposed.

Examples from the brief:

- “Keep six people on the floor this Saturday and Sunday, 4–8 pm. Move Vikas's weekly off to Tuesday.”
- “Show a safa and mojari with every sherwani trial today.”
- “Call the 15 customers who bought for a wedding last season and haven't been back.”

Vague actions such as “improve conversion at the store” or “focus on cross-selling” are not sufficient.

### Follow-up

- Store each issue or salesperson card.
- One week later, re-measure the targeted metric.
- Report whether the number moved and give before and after values.
- If the data window ends before the follow-up date, say it is not yet measurable.

### Store Coach acceptance

- The system found hidden causes and named the correct cause.
- The system spot-checked values agree with hand calculations.
- Every action is achievable in the store today.
- The system runs independently every day.

## Shared operational requirements

- Run daily as a scheduled autonomous process.
- Use a fixed as-of date and produce deterministic output from the same inputs and as-of date.
- Write a dated, reviewer-readable output set for every run.
- Record run date, as-of date, input row counts, output counts, data-issue count and success or failure.
- If a run fails, retain the previous day's output and record the failure reason.
- Rank output items by rupees at stake or MRP value, with the highest first.
- Apply hard caps after ranking, never relax caps to fit more output.
- Every output item needs a short plain-language reason with source numbers.
- Store issued recommendations so follow-up can compare before and after states.

## Data-quality points to enforce

- Read identifiers as text, not numbers or dates.
- Parse dates as `YYYY-MM-DD`.
- Exclude packaging SKUs from product counts, items-per-bill and sales velocity calculations.
- Flag customer `C99999999` or implausibly active customer identities and exclude them from repeat-customer logic.
- Flag and remove a bill or store-day with counter faults from conversion calculations when footfall is zero but bills exist.
- Footfall with zero bills is reviewable but should not automatically be called poor conversion.
- Log negative stock and exclude the affected SKU/store pair from moves.
- Reconcile the 31 October snapshot with the final weekly closing stock; mismatches require a data issue and move exclusion.
- Block over-capacity receiving locations and under-capacity-safe donor locations.
- A newly opened store lacks enough history for velocity or peer judgments.
- Check launch date and days in stock before calling a zero-sales SKU slow or dead.
- Log bills by an Off salesperson and do not count them as missed shifts.
- Packaging blank launch dates and ₹0 prices must not raise launch or zero-price errors.
- Infer leavers carefully when no exit date exists and document the inactivity rule.
- Map Safa, Mala and Stole to a single Accessories display category.
- Blank festival means no festival; blank in-transit arrival means nothing in transit.
- Check quantity, prices, footfall, stock days and bill dates for impossible values.
- Log unknown store, SKU, salesperson or bill IDs and exclude them from affected calculations.

## Known data traps from both PDFs

- A product with zero sales is not necessarily slow.
- Stock-outs, missing stock, recent launches and low `days_in_stock` can explain zero sales.
- Door-camera footfall can be family-level rather than customer-level.
- A small store or a newly opened store has limited history and noisy ratios.
- Regional category preferences are not necessarily store failures.
- Festival and wedding effects can make a normal fall or rise look abnormal.
- The stock snapshot and 12-week history may not fully align; mismatches must be investigated rather than silently moved.
- No time of day exists in bill data, so staffing recommendations must stay at day-level granularity.
- Roster coverage ends in October 2026, so it cannot support detailed staffing conclusions beyond that window.
- Future warehouse inbound is planned and therefore must not be assumed available before its expected date.

## Shared model and implementation shape

- One shared loader for all 17 tables.
- Explicit text handling for all IDs.
- Explicit date and numeric casting.
- A clean line-sales table joining bills, bill lines, items and stores.
- A store-day table containing footfall, bills, units, revenue and calendar flags.
- A peer comparison helper by store, city, state, zone and tier.
- A data-issue log with table, key, column, value, broken rule and action taken.
- A rupee-value ranking helper.
- A one-line explanation generator.
- A recommendation log and follow-up process.
- A daily run entry point that writes dated outputs with no prompt or manual start.
