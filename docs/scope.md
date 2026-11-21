# Scope: Daily Stock Move Recommender (Vedant Fashions / Manyavar)

**Format:** Web dashboard, with users able to upload more data
**Goal:** Every day, produce a ready-to-approve list of stock moves (warehouse → store, store → store, ageing) that a merchandiser can review in ~10 minutes.
**Judged on:** stockout-aware velocity, hidden problems found, numbers accurate, zero rule breaks, runs on its own, moves a merchandiser would approve.

**Priority key:** **P0** = must ship, **P1** = ship if time allows, **P2** = stretch / mention in pitch only.

---

## 1. Functional Requirements

### FR1. Data ingestion
| ID | Requirement | Pri |
|---|---|---|
| FR1.1 | Load workbook (or CSV copies); join tabs on `store_id`, `sku_id`, `bill_id`, `salesperson_id`, `state` | P0 |
| FR1.2 | Exclude packaging SKUs (`is_packaging = 1`) everywhere | P0 |
| FR1.3 | Basic validation on load: missing keys, negative stock, duplicates, orphan SKUs. Log issues, don't crash | P1 |
| FR1.4 | Rerun on a fresh data drop with no manual edits (config-driven file path) | P0 |

### FR2. Velocity engine
| ID | Requirement | Pri |
|---|---|---|
| FR2.1 | Units/day per store × SKU from `bills` + `bill_lines`; roll up to style and category | P0 |
| FR2.2 | **Stockout-aware:** divide by in-stock days (`stock_weekly.days_in_stock`), not calendar days | P0 |
| FR2.3 | New store fallback: borrow velocity from peer stores (same tier/city) | P0 |
| FR2.4 | Festival/wedding uplift by state from `calendar` (simple multiplier on the forward demand window) | P1 |
| FR2.5 | Core vs fashion: core uses long window; fashion uses recent window and carries ageing risk | P1 |

### FR3. Stock position and cover
| ID | Requirement | Pri |
|---|---|---|
| FR3.1 | Effective stock per location × SKU = on-hand + in-transit (arriving on `in_transit_arrives_on`) | P0 |
| FR3.2 | Cover (days) = effective stock ÷ daily velocity | P0 |
| FR3.3 | Stock age from `oldest_stock_received_on` | P0 |
| FR3.4 | Warehouse supply = WH-KOL snapshot + `warehouse_inbound` | P0 |

### FR4. Problem detection
| ID | Requirement | Pri |
|---|---|---|
| FR4.1 | Flag low-cover (under-stocked) store × SKU, ranked by expected sales loss | P0 |
| FR4.2 | Flag high-cover and ageing stock (stricter thresholds for fashion) | P0 |
| FR4.3 | Surface hidden problem pockets (stockout clusters, ageing clusters, store imbalances) in a "Findings" summary | P0 |
| FR4.4 | Label zero-sales cases as "no stock" vs "no demand" | P0 |

### FR5. Move generation (in this order)
| ID | Requirement | Pri |
|---|---|---|
| FR5.1 | **Warehouse → store:** allocate by need; when supply is short, lowest cover / highest loss first | P0 |
| FR5.2 | **Store → store:** surplus stores to need stores | P0 |
| FR5.3 | **Ageing:** move old stock to where it sells, or flag for pull-back to warehouse | P1 |
| FR5.4 | Lead time check from `lead_times`; move must arrive before the store runs out | P0 |
| FR5.5 | Never re-send in-transit stock | P0 |

### FR6. Hard constraints (zero violations allowed)
| ID | Rule | Pri |
|---|---|---|
| FR6.1 | Giver stays at or above `min_display` (tier × category) | P0 |
| FR6.2 | Receiver stays within `stock_capacity_units` | P0 |
| FR6.3 | No transfer out of an S++ store's top-20 flagship styles | P0 |
| FR6.4 | Giver keeps ≥ 30 days cover after a store-to-store move | P0 |
| FR6.5 | **Final validation pass** re-checks the whole list together (cumulative effect of moves); drops or trims any move that breaks a rule | P0 |

### FR7. Explainability
| ID | Requirement | Pri |
|---|---|---|
| FR7.1 | One-line reason per move built from computed values, e.g. "Send 12: KUR-05-L has 3 days cover at LKO-02, sells 4/day" | P0 |
| FR7.2 | Every number in a reason is generated from the data (template strings, never free text), so spot-checks match | P0 |

### FR8. Output and approval
| ID | Requirement | Pri |
|---|---|---|
| FR8.1 | Output columns: type, from, to, SKU, quantity, arrival date, reason | P0 |
| FR8.2 | Rank by impact (sales loss avoided / ageing value saved), best first | P0 |
| FR8.3 | Cap alerts per area manager at `max_alerts_per_week`, keeping the highest-impact moves | P1 |
| FR8.4 | Export to Excel (sheets: Moves, Findings, Rejected moves) and CSV | P0 |
| FR8.5 | Same moves list is served to the web dashboard (see FR10) | P0 |

### FR9. Automation
| ID | Requirement | Pri |
|---|---|---|
| FR9.1 | Single command runs the whole pipeline end to end | P0 |
| FR9.2 | Daily schedule (cron / scheduled task) that runs the same command | P0 |
| FR9.3 | Per-run log: timestamp, input file, counts of moves by type, rules that rejected candidates | P0 |

### FR10. Web dashboard
| ID | Requirement | Pri |
|---|---|---|
| FR10.1 | Approval list view: sortable and filterable moves table (type, from, to, SKU, qty, arrival, reason) | P0 |
| FR10.2 | Findings view: hidden problem pockets (stockouts, ageing clusters, store imbalances) with drill-down to store/SKU | P0 |
| FR10.3 | Summary cards: total moves by type, units moved, stockout SKUs, ageing value at risk | P1 |
| FR10.4 | Per-move approve / reject action, with the decision saved and included in export | P1 |
| FR10.5 | Store and SKU detail view: velocity, cover, stock age, in-transit | P1 |
| FR10.6 | Download current list as Excel/CSV from the dashboard | P0 |
| FR10.7 | Run status panel: last run time, counts, rejected moves and the rule that rejected them | P1 |



## 2. Non-Functional Requirements

| Area | Requirement | Pri |
|---|---|---|
| **Correctness** | Numbers in output reconcile to source data; spot-checkable by hand for any move | P0 |
| **Rule safety** | Constraint checks are centralised in one module and unit-tested on a few known cases; a violation is a bug, not a warning | P0 |
| **Determinism** | Same input produces the same output (fixed tie-breakers, no randomness) | P0 |
| **Performance** | Full run on the provided dataset (24 months, 20 stores) completes in under ~2 minutes on a laptop | P1 |
| **Reproducibility** | Fresh clone runs with one install step and one command; dependencies pinned | P0 |
| **Configurability** | Thresholds (ageing days, cover targets, festival uplift, velocity window) live in one config file, not hard-coded | P0 |
| **Robustness** | Bad rows or missing optional tabs are logged and skipped; the run still completes | P1 |
| **Usability** | A merchandiser can read and approve the list in ~10 minutes: sorted, plain-language reasons, no jargon, manageable row count | P0 |
| **Auditability** | Rejected candidate moves and the rule that rejected them are recorded | P1 |
| **Maintainability** | Modular pipeline (load → velocity → position → detect → generate → validate → export) with a short README | P1 |
| **Dashboard responsiveness** | Moves table loads in under ~2 seconds; recompute after upload shows progress and does not block the UI | P1 |
| **Upload safety** | File type and size limits; malformed uploads are rejected with a clear message and never corrupt the existing dataset | P0 |
| **Security / privacy** | Uploaded data stays within the app; no credentials in the repo | P1 |

---

## 3. Out of Scope

- Transport cost optimisation (brief says ignore it)
- Footfall and roster analysis (belongs to other case studies)
- Demand forecasting with ML models (use transparent rule-based velocity)
- Authentication, user roles and multi-tenant management (single-user dashboard assumed)
- Real-time or intraday updates
- Writing back to any ERP/WMS

---

## 4. Assumptions

- The `rules` tab may hold thresholds (ageing days, etc.); if absent, defaults in config are used and logged.
- "Day" granularity is enough; weekly stock data is spread across the week for in-stock-day logic.
- Moves are at SKU (style-size) level, whole units.
- Move generation is fully deterministic and rule-based; no LLM is involved.

---

## 5. Definition of Done

- [ ] One command (or the dashboard upload) produces `moves.xlsx` and `moves.csv` from the raw workbook
- [ ] Velocity uses in-stock days (demonstrated on at least one stockout example)
- [ ] Findings list shows the hidden problem pockets
- [ ] Zero rule violations after the final validation pass (checked by an independent test script)
- [ ] Every move has a data-backed one-line reason; 5 random moves hand-verified
- [ ] Web dashboard shows the ranked moves list and findings, with Excel/CSV download
- [ ] A user can upload new data in the dashboard and see moves recompute
- [ ] Daily schedule configured and a run log written
- [ ] README with run instructions