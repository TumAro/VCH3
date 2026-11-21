# Data summary: the 17 CSVs in `data/csv/`

A short, plain-language overview of every file. For detail, see:
- `data/README.md` - official notes and common mistakes.
- `data/csv/data_dictionary.csv` - every column explained.
- `docs/data-usability-report.md` - joins, gaps and data-quality issues.

Key facts:
- Synthetic data for Manyavar: 20 stores in 6 cities (Lucknow, Kanpur, Patna, Muzaffarpur, Bengaluru, Mysuru) and one warehouse, `WH-KOL`.
- Sales run from 1 Nov 2024 to 31 Oct 2026. "Today" is the close of 31 Oct 2026.
- Money is in rupees and includes GST. Dates are written `YYYY-MM-DD`.
- The data is not cleaned, so expect deliberate issues.

---

## Reference data

| File | Rows | One row is | Columns |
|---|---|---|---|
| `stores.csv` | 20 | A store | store_id, city, state, zone, tier, size_sqft, stock_capacity_units, opened_on, area_manager_id |
| `area_managers.csv` | 6 | An area manager (one per city) | area_manager_id, name, city, stores, max_alerts_per_week |
| `items.csv` | 385 | A SKU (one style in one size) | sku_id, style_id, style_name, category, size, mrp, cost_price, launch_date, is_core_style, is_packaging |
| `calendar.csv` | 2,373 | A date in a state (Nov 2024 to Dec 2026) | date, state, festival, is_wedding_date |

- **Store tiers:** S++ (super flagship), S+ (flagship), A, B.
- **Zones:** North (Uttar Pradesh), East (Bihar), South (Karnataka).
- **Area managers:** the `stores` column is a comma-separated list held in one cell.
- **Item categories:** Kurta Set, Sherwani, Indo-Western, Jacket, Mojari, Safa, Mala, Stole and Packaging.
  - There are 75 styles and 3 packaging items.
  - `is_core_style = 1` means the style is replenished all year.
- **Calendar:** festivals are state-specific, and the calendar runs two months past the sales data.

## People and floor data (mainly Store Coach)

| File | Rows | One row is | Columns |
|---|---|---|---|
| `salespeople.csv` | 175 | A salesperson | salesperson_id, store_id, name, join_date |
| `roster_daily.csv` | 23,569 | A salesperson on a day | date, store_id, salesperson_id, status (Present/Off) |
| `footfall_daily.csv` | 13,892 | A store on a day | date, store_id, footfall |

- `salespeople.csv` includes people who have left, but there is no exit date.
- The roster covers only 1 May to 31 Oct 2026.
- Footfall comes from a door camera that counts people, not buying groups.

## Sales transactions (both problems)

| File | Rows | One row is | Columns |
|---|---|---|---|
| `bills.csv` | 90,805 | A bill | bill_id, bill_date, store_id, salesperson_id, customer_id |
| `bill_lines.csv` | 259,772 | An item on a bill | bill_id, sku_id, qty, mrp, selling_price |

- **Line revenue** = `qty` x `selling_price`. **Discount per unit** = `mrp` - `selling_price`.
- `customer_id` is a hashed mobile number. It stays the same across visits and stores.
- Bills have no time of day.
- Packaging lines are Rs 0 and are not products. Exclude them from item counts and sales velocity.

## Stock data (mainly Stock Mover)

| File | Rows | One row is | Columns |
|---|---|---|---|
| `stock_snapshot.csv` | 3,547 | A location and SKU on 31 Oct 2026 | as_of_date, location_id, sku_id, on_hand, in_transit, in_transit_arrives_on, oldest_stock_received_on |
| `stock_weekly.csv` | 61,416 | A store, SKU and week (last 12 weeks) | week_ending, store_id, sku_id, closing_on_hand, days_in_stock |
| `warehouse_inbound.csv` | 768 | A planned delivery to the warehouse (1 Nov to 16 Dec 2026) | expected_date, sku_id, qty, status |

- In `stock_snapshot.csv`, `location_id` is a store or `WH-KOL`. A missing location and SKU pair means zero stock.
- `days_in_stock` (0 to 7) shows whether a SKU with no sales was slow or simply out of stock.
- Weeks run Sunday to Saturday, and `stock_weekly.csv` has no warehouse rows.

## Stock rules (Stock Mover)

| File | Rows | One row is | Columns |
|---|---|---|---|
| `rules.csv` | 8 | A stock rule, in prose | rule, detail |
| `min_display.csv` | 24 | A tier and category | tier, category, min_display_units |
| `lead_times.csv` | 6 | A route | route, days |
| `flagship_protected.csv` | 80 | A protected style at an S++ store | store_id, rank, style_id |

The 8 rules:
1. Keep the minimum display quantity per tier and category.
2. S++ stores never give away their top-20 styles.
3. Never exceed a store's `stock_capacity_units`.
4. Stock in transit counts as arriving.
5. A donor store must not drop below 30 days of cover for the style.
6. Any single move worth more than Rs 1,00,000 at MRP needs human approval.
7. Replenishment happens every Monday today, but any day may be recommended.
8. Ignore transport cost, but respect lead time.

Watch for:
- `min_display.csv` groups Safa, Mala and Stole as "Accessories (Safa/Mala/Stole)". Sum the three categories from `items.csv` to match it.
- `lead_times.csv` routes are sentences. Derive the route from each store's city and zone:
  - Warehouse to store: 3 days (East), 4 days (North), 6 days (South).
  - Store to store: 2 days (same city), 4 days (same zone), 7 days (different zone).

## Metadata

| File | Rows | One row is | Columns |
|---|---|---|---|
| `data_dictionary.csv` | 36 | A column definition | tab, column, what_it_means, example |

---

## How the files join

- `store_id` -> `stores` (from bills, footfall, roster, salespeople, stock tables, flagship_protected)
- `bill_id` -> `bills` (from bill_lines)
- `sku_id` -> `items` (from bill_lines, stock tables, warehouse_inbound)
- `salesperson_id` -> `salespeople` (from bills, roster_daily)
- `area_manager_id` -> `area_managers` (from stores)
- `state` -> `calendar` (from stores)
- `style_id` groups all sizes of one design (items, flagship_protected)
