# What Problem A (Store Coach) and Problem B (Stock Mover) have in common

Scope: abstract level. Sources: `data/README.md`, both briefs, the small rule tables, and the existing `docs/data-usability-report.md` (its findings are reused, not redone). Both briefs ship the identical 17-table data guide. The team builds one problem, but most of the foundation is the same.

---

## 1. Shared data: tables, columns, joins

- **Same pack, same guide.** Both briefs say "the same sample dataset" and print the same data guide, join figure and column list. Only the brief text on top differs.
- **Tables both problems read.**
  - `stores`: the spine. Store id, city, state, zone, tier, capacity, area manager. Peer groups, capacity and tier all come from here.
  - `items`: SKU, style, category, size, MRP, cost, launch date, core vs fashion, packaging flag.
  - `bills` and `bill_lines`: the sales record. A uses them for conversion, basket and repeat. B uses them as the only source of velocity.
  - `calendar`: festivals and wedding dates by state. A uses it to avoid false alarms. B uses it as forward demand context.
  - `area_managers`: A's recipients. For B it is the natural owner or escalation contact per store, and its `max_alerts_per_week` of 5 is a ready-made "how much will a human actually read" cap.
- **Tables mostly one side but useful to the other.**
  - Stock tables (`stock_snapshot`, `stock_weekly`, `warehouse_inbound`) are B's core. A's brief lists stock in its dataset too, and A's actions must be doable "with the people and stock it already has", so a cross-sell nudge should not point at a SKU the store does not hold.
  - `footfall_daily`, `roster_daily`, `salespeople` are A's core. For B, footfall is a cheap demand signal and a stock-out can depress it, but it is optional.
- **Join keys are identical and clean.**
  - `store_id` joins everything to `stores`. `sku_id` joins sales, stock and inbound to `items`. `bill_id` joins lines to bills. `state` joins stores to calendar. `style_id` groups sizes of a design.
  - `store_id` + `date` is the common daily grain for bills, footfall and (via weekly rollup) stock.
  - `location_id` in the stock snapshot is a store id or the warehouse `WH-KOL`, which is not in `stores`. This only bites B, but it is a join the shared code must not break.
- **Same time frame.** Sales 1 Nov 2024 to 31 Oct 2026. "Today" is the close of 31 Oct 2026. Roster is 1 May to 31 Oct 2026 only. Stock is a single snapshot plus 12 weeks.

## 2. Shared cleaning steps

- **Read every ID as text.** Store, SKU, bill, salesperson, customer and style ids. Dates parsed explicitly (year-month-day). Never open CSVs in Excel on the way.
- **Packaging rows are not products.** Three packaging SKUs (`PKG-BAG`, `PKG-COVER`, `PKG-BOX`, Rs 0, no launch date). Drop them from items-per-bill (A) and from velocity (B). Same filter, same table.
- **Placeholder customer `C99999999`.** About 1,800 bills across all stores and the full period. Mainly an A issue (repeat customers, wedding call lists). B only needs it if customers are used at all. One flag in the shared sales table covers both.
- **Join `bills` to `bill_lines` to `items` to `stores` once.** Line revenue is qty times selling price. Discount is MRP minus selling price.
- **New store BLR-05** (opened 10 Oct 2026, 22 days of footfall and bills, roster rows from 25 Sep). No history for either problem. It must not be called "slow" (A) or have velocity extrapolated from a few days (B). Treat as "too new to judge" with an explicit rule.
- **Impossible values are flagged, not acted on.** Both briefs reward this. Known examples:
  - PAT-03 footfall of 0 on days with bills (A: conversion is invalid, not low).
  - KNP-03 `SHW-02-L` with 300 units on hand against 250-unit capacity, and `KUR-02-M` at MYS-02 with on-hand -4 (B: do not move against these).
  - Days with footfall but zero bills in small stores (A: low conversion or missing bills, unknown; B: sales may be missing, so velocity may be understated).
- **Category naming.** `items` has Safa, Mala, Stole separate. `min_display` groups them as "Accessories". Mostly B, but A's cross-sell pairs (safa, mojari, mala) use the same category column, so one category map serves both.
- **Leavers have no exit date** (A mainly). Not a B concern, but the same "infer from last activity" habit applies to any entity with no end date.

## 3. Shared derived building blocks

One codebase can build these once and both problems consume them.

- **Clean sales table.** Bill-line grain: date, store, salesperson, customer (placeholder flagged), SKU, style, category, size, qty, MRP, selling price, discount, revenue. Packaging excluded, store and item attributes attached.
- **Store-day table.** Store by date: footfall, bills, units, revenue, plus festival and wedding flags for the store's state, and a data-quality flag (e.g. PAT-03 broken counter, new store). A uses it directly. B uses the sales side for demand and the calendar flags for seasonality.
- **Calendar / season context.** State-level festival and wedding flags, including the look-ahead into Nov and Dec 2026. A: "this dip is normal, do not alert". B: "demand is about to rise, stock early, allow lead time". Same lookup, opposite use.
- **Peer grouping.** Store, city, state, tier, zone. A compares salespeople to peers in their own store, city and state. B compares stores (same tier, same zone) to judge whether a store is under-stocked or holding surplus. One peer-group helper serves both.
- **Baseline and anomaly pattern.** "Is this store/SKU unusual versus its own history and its peers, after allowing for season?" Conversion falling (A) and velocity or cover drifting (B) both need a seasonal baseline and a peer baseline. The calculation is the same shape.
- **Rupees at stake.** A common value measure (revenue or MRP value) to rank findings. A ranks issues by rupees. B ranks moves by value at MRP, and the Rs 1,00,000 approval rule is also a value test.
- **Store and area-manager lookup.** Store to area manager to city, so any output can be grouped by who has to read it.
- **Data-issue log.** One list of flagged data problems, with the rule that triggered each. Both briefs want issues flagged, not acted on.
- **Output layer.** Ranked list, one-line reason, owner, and a place to store what was recommended. Different content, same plumbing.

## 4. Shared product requirements in the briefs

- **Runs on its own, daily.** A: "Run on its own every day. No one should have to ask it a question." B: "Every day, find stock..." and "we check that it runs on its own." Both use "today" as 31 Oct 2026 and both allow any build approach (scheduled tasks, skills, artifacts). One scheduler or entry point serves both.
- **Ranked and capped output.**
  - A is explicit: at most 5 issues per area manager per week, ranked by rupees at stake, plus a card of 60 words or fewer per salesperson.
  - B is explicit about readability ("approve in ten minutes") and about prioritising when the warehouse cannot serve everyone, but gives no numeric cap. The 5-per-week cap in `area_managers` is a reasonable reference if B wants one.
  - Either way: rank by value, show the top items first, cut the tail.
- **Every action explained in one line.** A: lever, cause, one action. B: "Explain every move in one line." Same template idea: what, why, how much it is worth.
- **Easy to act on.**
  - A: who, what, when, doable today with existing people and stock, no budget or approval.
  - B: a ready-to-approve list a merchandiser can clear in ten minutes where every move makes sense, with human approval for moves above Rs 1,00,000.
  - Shared test: could a busy person do or approve this without asking a follow-up question?
- **Numbers are spot-checked.** A: "Wrong numbers cost more than missing features." B: "We spot-check your numbers, and we check that no rule is broken." Both favour correctness and traceability over breadth. Every figure should be reproducible from the clean tables.
- **Hidden problems planted in the data.** Both say "we know what is hidden" and check whether the system found it. Both also say a data problem should be flagged, not alerted on (A states it directly, B implies it with "zero sales is not always slow, check before you trust").
- **Follow-up and feedback loop.**
  - A: a week later, check whether the number moved and say so.
  - B: not stated, but a daily system that proposes moves naturally needs to know what was approved, what is already in transit, and not re-propose it.
  - Shared need: store yesterday's recommendations, compare to today's data, report the outcome. One recommendation log and re-measure step serves both.

## 5. Shared risks and data traps

- **Absence of a signal is not a weak signal.**
  - B states it ("zero sales is not always slow"). Stock-outs and new styles cause zero sales.
  - A has the mirror case: a counter fault or missing bills look like poor conversion.
  - Cross-effect: a store out of stock in a category may look like poor basket building or a conversion dip.
- **Seasonality masquerading as a problem.** Festivals are state-specific (Chhath in Bihar, Ganesh Chaturthi and Ugadi in Karnataka, Holi not in Karnataka). Wedding dates swing demand. Both problems can raise a false alarm if they ignore `calendar`.
- **Small or new entities.** BLR-05 has almost no history. Small stores have thin counts, so ratios and velocities there are noisy. Both need a "not enough data" rule.
- **Planted data errors that mislead any naive calculation.** Placeholder customer, PAT-03 footfall, KNP-03 over-capacity, negative stock at MYS-02, packaging rows. A system that does not log and exclude them produces wrong numbers, which both briefs punish.
- **Right level of comparison.** A: compare to peers in own store, city, state, not the whole country. B: compare stores within tier or zone and use style and size, not just total units. Wrong grouping gives wrong conclusions in both.
- **A city-level problem is not a store-level problem.** A says so for slowdowns. For B the equivalent is a whole region short of stock because the warehouse could not serve it.
- **Fixed inputs that are partial.** No time of day on bills, no returns, roster only 6 months, stock history only 12 weeks, warehouse inbound all "Planned". Neither problem should claim precision the data does not hold.
- **Explanation can drift from the number.** A one-line reason that does not match the calculation will be caught on a spot-check. Generate the sentence from the same variables used to make the decision.
- **IDs and dates as text** (see section 2). The same silent failure hits both.

## 6. What differs (so the overlap is read in context)

- **Question.** A asks "which store or person needs attention and what should they do today?" B asks "where is stock in the wrong place and what should move?"
- **Audience.** A: six area managers and 175 salespeople. B: a merchandiser or planner approving a list.
- **Core data.** A: footfall, roster, salespeople, customers. B: stock snapshot, weekly stock, inbound, rules, min display, lead times, flagship list.
- **Constraints.** A is limited by readability caps (5 issues a week, 60 words) and by "doable today". B is limited by hard rules that must all hold on every move (minimum display, flagship protection, capacity, in-transit, 30-day donor cover, lead time, approval threshold). B has more hard correctness checks, A has more judgment and wording.
- **Success test.** A: found the hidden cause and named it, and the action is actionable. B: found the hidden stock problems, and no rule is broken.
- **Foundations that are reusable no matter which one is picked**
  - Clean sales table, store-day table, calendar context, peer grouping, data-issue log, value-based ranking, one-line explanation helper, run-daily entry point, recommendation log.
  - Even if the team picks A, the stock tables and rules are not needed. Even if it picks B, people and footfall tables are not needed. Everything else above is.

## 7. Build once, use for both

- **Loader**: reads all CSVs as text, casts types explicitly, one place for date and ID handling.
- **Clean sales table**: packaging out, placeholder customer flagged, stores and items joined, discount and revenue computed.
- **Store-day table**: footfall, bills, units, revenue, festival and wedding flags, data-quality and new-store flags.
- **Calendar helper**: festival and wedding lookup by state and date, including look-ahead.
- **Peer-group helper**: store, city, state, zone, tier. One function that returns "who is this compared with".
- **Baseline helper**: seasonal and peer baseline for any metric, with a "not enough data" return.
- **Data-issue log**: single list with rule, entity and date. Flagged items are excluded from decisions.
- **Value and ranking helper**: rupees at stake, top N per owner, cutoff.
- **One-line reason builder**: template filled from the same variables the decision used.
- **Recommendation log and re-check**: store what was recommended, re-measure later, report whether it moved or was done.
- **Daily entry point**: one runnable that loads, builds tables, runs the chosen problem's rules, writes the ranked output with no human prompt.
- **Spot-check hooks**: for any number shown, a way to print the rows it was computed from.
