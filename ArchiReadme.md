Unified Retail Intelligence Platform
System Architecture, Scope, and Implementation Plan
Project concept: Combine the Stock Mover and Store Coach retail

challenges into one platform with deterministic statistical analytics, a

knowledge/RAG layer, a Live-Kit AI agent, and a dashboard with controlled

data-management workflows.

1. Vision and Objectives
Build a retail decision-support platform that helps managers understand

what is happening, why it is happening, and what action to take

across stores, inventory, products, and sales teams.
The system should: - Analyze sales, inventory, footfall, workforce, and

customer data. - Generate statistically sound, repeatable reports

without using an LLM for calculations. - Detect risks, anomalies,

shortages, excess inventory, and underperformance. - Recommend stock

movements and operational actions with explanations and evidence. - Make

reports and business context accessible through RAG and conversational

AI. - Allow authorized users to manage and correct business data through

conversational and dashboard workflows. - Track the outcomes of

recommendations so the system can evaluate whether actions helped.
Design principle
Deterministic analytics first; AI interpretation second; controlled

action execution third.
AI must not be the source of truth for numeric calculations, inventory

counts, sales records, or policy constraints.

2. Scope: Two Core Business Engines
2.1 Stock Mover --- Inventory Intelligence
Goal: Right stock, right store, right size, at the right time.
Responsibilities: - Identify store/SKU shortages and stock-out risk. -

Identify excess, slow-moving, and ageing inventory. - Calculate stock

cover and demand velocity. - Forecast demand over appropriate

horizons. - Recommend warehouse-to-store replenishment. - Recommend

store-to-store transfers. - Respect store capacity, display minimums,

protected styles, lead times, inbound stock, and donor-store safety

constraints. - Prioritize transfer recommendations and explain their

rationale. - Estimate the expected stock position before and after a

proposed movement.
Key outputs: - Stock-risk report. - Excess/ageing inventory

report. - Replenishment plan. - Store-to-store transfer plan. -

SKU/store demand forecast. - Constraint validation results. -

Recommendation priority and explanation.
2.2 Store Coach --- Sales & Workforce Intelligence
Goal: Improve sales performance, conversion, basket size, and repeat

customer behavior.
Responsibilities: - Calculate store performance and trends. - Measure

conversion, average bill value (ABV), items per bill (IPB), revenue, and

other agreed KPIs. - Compare stores with suitable peer groups and their

own baselines. - Analyze salesperson performance with context and fair

comparisons. - Analyze footfall, roster coverage, working hours, and

staffing patterns where the data permits. - Identify potential

cross-selling, customer-retention, and operational opportunities. -

Detect anomalies, declining performance, unusual discounts, and other

issues. - Generate actionable coaching opportunities.
Key outputs: - Daily/weekly/monthly store reports. - Region and

store-grade comparisons. - Salesperson performance reports. - KPI trends

and deviations. - Anomaly reports. - Coaching/action recommendations. -

Evidence and comparison baselines.

3. High-Level Architecture
flowchart TD
    U[Users: HQ, Area Managers, Store Managers, Staff] --> UI[Dashboard / Chat / Voice UI]
    UI --> AG[LiveKit AI Agent]
    AG --> API[Backend API and Tool Gateway]

    API --> SQL[(Operational Database)]
    API --> RAG[RAG / Knowledge Retrieval]
    API --> PE[Pandas Statistical Engine]

    DATA[Data Sources: Sales, Bills, Stock, Footfall, Roster, Calendar] --> ETL[Data Ingestion and Validation]
    ETL --> SQL

    PE --> SQL
    PE --> REP[Structured Reports / Findings]
    REP --> SQL
    REP --> IDX[Knowledge Index]
    RAG --> IDX

    PE --> OPT[Forecasting and Optimization]
    OPT --> REP

    API --> AUD[Audit / Permissions / Validation]
    AUD --> SQL

    AG --> DASH[Dashboard Summaries / Insights / Explanations]
    API --> DASH

Main components
1.	Data ingestion and validation
2.	Operational database
3.	Statistical analytics engine
4.	Forecasting and optimization modules
5.	Report generation and storage
6.	RAG knowledge system
7.	LiveKit agent and tool gateway
8.	Dashboard and user workflows
9.	Permission, validation, and audit system
10.	Scheduler and monitoring

4. Component Details and What to Build
4.1 Data Ingestion and Validation
Purpose: Bring source data into the system reliably and

consistently.
Sources may include CSV/Excel files, exports, APIs, or future

integrations.
Work to do
·	Define schemas for each input.
·	Validate columns, data types, required fields, IDs, dates, and

quantities.
·	Detect missing data, duplicates, invalid records, and inconsistent

references.
·	Normalize store IDs, SKU IDs, employee IDs, timestamps, and

categories.
·	Reject or quarantine invalid rows rather than silently accepting

them.
·	Record import metadata: source, timestamp, file/version, row counts,

errors.
·	Make imports idempotent where possible, preventing accidental

duplicate ingestion.
·	Provide an import report with accepted/rejected rows and reasons.
Expected output
Clean, validated, versioned data ready for analytics and storage.
4.2 Operational Database
Purpose: Store authoritative business records.
Suggested database: PostgreSQL.
Possible entities: - Stores and store attributes. - Regions and

area-manager assignments. - Products, styles, SKUs, sizes, and

categories. - Employees and salesperson/store assignments. - Bills and

bill line items. - Daily footfall. - Rosters and working hours. -

Inventory snapshots and movements. - Warehouse stock and inbound

shipments. - Calendar events, festivals, and business rules. - Customer

data, only if provided and access is appropriate. - Report metadata and

report records. - Recommendations and recommendation outcomes. - Audit

logs.
Work to do
·	Design normalized schemas and relationships.
·	Define unique keys and foreign keys.
·	Add indexes for common queries (date, store, SKU, employee, report

type).
·	Use transactions for writes and inventory changes.
·	Define data retention and privacy rules.
·	Keep raw imported data and cleaned/derived data distinguishable.
·	Avoid treating generated reports as the authoritative source for

inventory or sales.
4.3 Pandas Statistical Engine --- No AI
Purpose: Calculate metrics, comparisons, findings, forecasts, and

recommendation candidates reproducibly.
This engine is the numerical source of truth.
Build it as independent modules, with shared data preparation and metric

definitions.
Module A: Sales Analytics
Calculate: - Revenue and units sold. - Bills and transaction counts. -

Average bill value (ABV). - Items per bill (IPB). - Conversion = bills /

footfall, subject to the agreed definition and data quality. - Growth

and trend metrics. - Category/style/size performance. - Discount and

return metrics if the data supports them.
Module B: Inventory Analytics
Calculate: - On-hand stock and available stock. - Sales velocity. -

Stock cover. - Stock-out risk. - Sell-through. - Inventory turnover

where inputs support it. - Excess stock. - Ageing inventory. - Inventory

distribution across stores and sizes.
Example: stock_cover_days = available_units / average_daily_units_sold
Define zero-sales handling carefully. Do not report infinite or

misleading cover as an ordinary number; use a distinct status such as

no_recent_sales or not_estimable.
Module C: Store Performance Analytics
Calculate: - Store KPIs by day/week/month. - Comparisons against the

store's own baseline. - Peer comparisons by store grade, region, format,

or other relevant groups. - Trends and statistically meaningful

deviations where possible.
Avoid comparing stores with fundamentally different traffic, size,

location, or customer mix without adjusting or clearly qualifying the

comparison.
Module D: Workforce Analytics
Calculate: - Sales and units per salesperson. - Sales per working hour

when reliable shift/hour data exists. - Conversion by salesperson only

when attribution is valid. - Peer comparisons and consistency over

time. - Roster coverage against footfall and trading hours. - Potential

coaching indicators.
Avoid unfair rankings from small samples, unequal shifts, or different

customer opportunities. Display sample size and uncertainty where

possible.
Module E: Demand Forecasting
Build a forecasting baseline first: - Rolling averages and weighted

averages. - Day-of-week patterns. - Seasonality. -

Festival/wedding-calendar effects when relevant and data-supported. -

Trend. - Stock-out periods that censor observed demand. - Forecast

horizon appropriate to replenishment lead time.
Evaluate models with time-based backtesting. Track forecast errors. Do

not claim forecast accuracy without measured validation.
Module F: Anomaly Detection
Detect and flag: - Sudden sales declines or spikes. - Unexpected

inventory changes. - Unusual discounting. - Data-quality anomalies. -

Stock discrepancies. - Store or salesperson metrics that deviate from

appropriate baselines.
Use explicit rules/statistical thresholds initially; add more

sophisticated methods only when they are justified and validated.
Module G: Stock Mover Optimization
Calculate candidate movements and optimize allocations.
Consider: - Receiving-store demand and shortage. - Donor-store excess

stock and minimum safe cover. - Warehouse available stock. - Inbound and

in-transit inventory. - Display minimums. - Store capacity. - Protected

styles/store rules. - Transfer lead times. - Forecasted demand during

lead time. - Transfer quantities and priorities.
Use a constraint-based optimizer where appropriate (for example,

OR-Tools), or a clearly documented deterministic heuristic for the first

MVP.
Each proposed transfer must pass feasibility checks. Recommendations

should be candidates until approved and executed.
Statistical engine requirements
·	Unit-tested calculations.
·	Explicit metric definitions and versions.
·	Reproducible inputs and outputs.
·	Data-quality flags.
·	Evidence and baselines for findings.
·	No LLM-generated numbers.
·	Run IDs and data timestamps.
·	Validation and regression tests.
4.4 Reports and Findings
Purpose: Turn analytical results into reusable, structured records.
Generate reports at suitable scopes: - Company-wide. - Region. -

Store. - Category/style/SKU. - Salesperson. - Inventory risk. -

Forecast. - Transfer/replenishment recommendations.
Reports should include: - Report type and scope. - Period and generated

timestamp. - Data version/run ID. - Metrics and units. -

Baseline/comparison. - Findings. - Severity/priority. - Evidence

references. - Recommended actions (where generated by deterministic

logic). - Confidence/limitations. - Data-quality warnings.
Prefer JSON or structured database records as the canonical report.

Human-readable Markdown/PDF can be generated from those records for

export.
4.5 RAG and Knowledge Layer
Purpose: Retrieve relevant reports, policies, store context,

historical findings, and business knowledge for the agent.
Sources: - Statistical engine reports. - Store profiles and

attributes. - Product/category information. - Business rules and

operational policies. - Historical trends and findings. - Previous

recommendations and outcomes. - User-approved documentation.
Work to do
·	Store canonical structured reports in SQL/object storage.
·	Index report summaries and relevant textual evidence in a vector

store.
·	Add metadata to every indexed record: report type, store, region,

SKU, employee (when appropriate), period, severity, source, and

version.
·	Use metadata filters during retrieval.
·	Keep report IDs and source references so answers can be traced.
·	Update indexes when reports change; remove stale versions from

active retrieval.
·	Use hybrid retrieval (metadata/keyword + semantic/vector) where

useful.
·	For exact numerical questions, retrieve structured data from SQL/API

instead of relying on embeddings.
·	Apply permissions to retrieval; users must not see reports they are

not authorized to access.
RAG is not the database. It is a retrieval and contextualization

layer.
4.6 LiveKit AI Agent
Purpose: Natural-language and voice interface for understanding

reports, exploring findings, and helping users make decisions.
Responsibilities: - Understand the user's request. - Identify the

appropriate scope, period, and entity. - Select backend tools. -

Retrieve structured metrics and supporting knowledge. - Summarize

findings in clear language. - Distinguish measured facts from

hypotheses. - Explain recommendations, constraints, and uncertainty. -

Ask for clarification when the request is ambiguous. - Prepare write

actions for confirmation where required.
The agent should not: - Calculate authoritative KPIs itself. - Invent

missing data. - Guess inventory counts. - Override business rules. -

Directly write to tables without validated APIs. - Claim that a

recommendation was executed when it was only proposed.
Suggested read tools
get_company_summary(period)
get_region_summary(region, period)
get_store_summary(store_id, period)
get_store_sales_report(store_id, period)
get_inventory_report(store_id, category_or_sku)
get_stock_risk(store_id, sku)
get_salesperson_report(employee_id, period)
get_anomalies(scope, period)
get_transfer_recommendations(scope)
get_forecast(scope, horizon)
search_knowledge_base(query, filters)

Tool names are illustrative. Define contracts and access scopes before

implementation.
4.7 Dashboard
Purpose: Provide immediate, visual, actionable information without

requiring a conversation.
Suggested pages: 1. Executive overview. 2. Store performance. 3.

Regional performance. 4. Stock Mover. 5. Inventory ageing and stock

risk. 6. Forecasts. 7. Salesperson / Store Coach. 8. Alerts and

anomalies. 9. Recommendation approval queue. 10. Data imports and

quality. 11. History and outcomes. 12. Conversational assistant.
Dashboard metrics should be loaded from structured analytics

records/APIs. AI-generated summaries can appear alongside them, not

replace them.
4.8 Conversational Data Management
Purpose: Allow authorized users to add, update, or correct records

through natural language or forms.
Examples: - Add a store. - Update store capacity or grade. - Correct a

stock count. - Import new sales. - Update a product attribute. - Correct

an employee/store assignment. - Add a business rule or calendar event.
Workflow: 1. Parse user intent. 2. Identify the target record. 3.

Retrieve current state. 4. Validate proposed values and permissions. 5.

Present a change preview. 6. Obtain confirmation for sensitive or

impactful changes. 7. Apply the change via a backend API and database

transaction. 8. Record actor, timestamp, before/after values, and

reason. 9. Trigger recalculation or report invalidation as needed. 10.

Return the result.
Do not use RAG to perform database writes. Use APIs and validated

transactions.
4.9 Permissions, Validation, and Audit
Define roles such as: - HQ/admin. - Area manager. - Store manager. -

Inventory manager. - Sales staff. - Read-only analyst.
Implement: - Authentication. - Role-based and scope-based permissions. -

Store/region access boundaries. - Write validation. - Confirmation

requirements. - Audit logs. - Sensitive-data minimization. - Safe

handling of customer and employee information.
4.10 Scheduler and Automation
Run scheduled jobs to: - Import/refresh data. - Validate new data. - Run

statistical modules. - Generate reports. - Refresh forecast outputs. -

Create stock transfer candidates. - Index reports into the knowledge

layer. - Prepare dashboard summaries. - Monitor job failures and stale

reports.
Provide manual reruns with run IDs and status tracking. Prevent

duplicate runs or duplicate imports from causing inconsistent data.

5. End-to-End Daily Workflow
flowchart TD
    A[Scheduled data refresh] --> B[Validate and normalize]
    B --> C[Store validated data]
    C --> D[Run Pandas analytics]
    D --> E[Forecast and optimize]
    E --> F[Generate structured reports]
    F --> G[Persist reports and findings]
    G --> H[Update knowledge index]
    G --> I[Update dashboard metrics]
    H --> J[LiveKit agent retrieves context]
    J --> K[Generate summaries and explanations]
    I --> L[Dashboard ready]
    K --> L
    L --> M[Manager reviews recommendations]
    M --> N[Approve / reject / edit action]
    N --> O[Execute through controlled API]
    O --> P[Track outcomes]
    P --> Q[Evaluate effectiveness]

The daily workflow should not depend on the AI agent successfully

running before the dashboard can display numerical metrics.

6. Cross-Engine Intelligence
The most differentiated feature is connecting Stock Mover and Store

Coach.
Examples:
Scenario A: Low conversion caused by unavailable stock
·	Store Coach detects conversion below baseline.
·	Inventory analytics finds high-demand sizes unavailable.
·	Stock Mover identifies feasible supply from warehouse or donor

stores.
·	Unified system prioritizes replenishment.
·	Store performance analysis marks stock availability as a possible

contributing factor rather than automatically blaming staff.
Scenario B: Excess stock at a weak-demand store
·	Inventory engine detects excess stock and low velocity.
·	Store Coach confirms category demand is weak.
·	Stock Mover checks stores with stronger demand and shortages.
·	Optimizer proposes feasible transfers.
Scenario C: High footfall but low basket size
·	Store Coach detects low items-per-bill.
·	Inventory engine checks whether complementary products are

available.
·	Agent presents evidence-based cross-selling opportunities.
·	Dashboard tracks IPB after the coaching action.
Scenario D: Festival or wedding demand
·	Calendar and forecasting modules detect a demand window.
·	Inventory engine estimates requirements.
·	Store Coach identifies stores and teams that may need preparation.
·	System prioritizes stock before the demand peak, accounting for lead

times.
Cross-engine conclusions should be grounded in data and labeled

appropriately. Correlation alone does not prove causation.

7. Recommendation Lifecycle and Feedback Loop
Every recommendation should be a trackable object.
Suggested lifecycle:
Generated
   ↓
Validated
   ↓
Pending approval
   ├── Rejected
   ├── Edited
   └── Approved
          ↓
       Executed
          ↓
     Outcome window
          ↓
      Evaluated

Track: - Recommendation ID. - Type. - Scope. - Evidence. - Expected

impact. - Constraints. - Generated timestamp. - Approval/rejection. -

Edits. - Execution status. - Outcome period. - Actual measured

outcome. - Evaluation result.
Evaluate after an appropriate time window, such as seven days for some

store actions or a longer interval for stock movements. The interval

must match the action and data availability.
Use this feedback to evaluate recommendation effectiveness and improve

thresholds/models. Do not automatically train on outcomes without

quality checks.

8. Suggested Technology Stack
Treat this as a proposed stack, not a mandatory list.

Layer                   Suggested technology    Reason

Analytics               Python, Pandas, NumPy   Data analysis and

deterministic

calculations
Forecasting             Statsmodels,            Baselines and validated

scikit-learn; possibly  models

XGBoost
Optimization            OR-Tools                Inventory allocation

and transfer

constraints
API                     FastAPI                 Typed, testable backend

APIs
Database                PostgreSQL              Authoritative

operational and

analytics storage
Vector retrieval        pgvector or a separate  Semantic retrieval with

vector store            metadata
AI/voice                LiveKit Agents          Conversational and

voice interface
Frontend                React / Next.js         Dashboard and user

interaction
Charts                  Plotly or a suitable    Interactive visual

chart library           analytics
Scheduler               APScheduler initially;  Scheduled analytical

orchestration later if  runs

needed
Authentication          Suitable identity       Identity and access

provider + backend RBAC control
Deployment              Docker                  Repeatable local/demo

deployment
Avoid adding infrastructure solely for novelty. Start with a modular

monolith and separate worker processes if necessary; split into

microservices only when deployment, scale, or team ownership demands it.

9. Data Contracts
The interfaces between components are more important than the initial

choice of libraries.
Define versioned schemas for:
Analytics run
·	Run ID.
·	Module.
·	Scope.
·	Input data version.
·	Start/end timestamps.
·	Status.
·	Metrics.
·	Findings.
·	Warnings.
·	Model/logic version.
Report
·	Report ID.
·	Report type.
·	Scope.
·	Period.
·	Metrics.
·	Baselines.
·	Findings.
·	Evidence references.
·	Recommendation references.
·	Data-quality notes.
Recommendation
·	Recommendation ID.
·	Type.
·	Source/destination or target entity.
·	Quantity/action.
·	Priority.
·	Evidence.
·	Expected impact.
·	Constraints.
·	Approval state.
·	Execution state.
Finding
·	Finding ID.
·	Finding type.
·	Severity.
·	Metric.
·	Actual value.
·	Baseline.
·	Difference.
·	Evidence.
·	Scope.
·	Period.
·	Related recommendations.
These contracts let the Pandas engine, database, dashboard, RAG system,

and agent evolve independently.

10. Example Repository Structure
retail-intelligence/
├── apps/
│   ├── dashboard/                 # Frontend
│   └── api/                       # FastAPI application
├── services/
│   ├── analytics/                 # Statistical engine
│   │   ├── sales/
│   │   ├── inventory/
│   │   ├── store_performance/
│   │   ├── workforce/
│   │   ├── forecasting/
│   │   ├── anomalies/
│   │   └── stock_mover/
│   ├── agent/                     # LiveKit agent and tool definitions
│   ├── ingestion/                  # Imports and validation
│   ├── reporting/                  # Report schemas and generation
│   └── recommendations/              # Lifecycle and evaluation
├── shared/
│   ├── schemas/                    # Versioned contracts
│   ├── metrics/                    # Shared definitions
│   ├── permissions/
│   └── utilities/
├── knowledge/
│   ├── retrieval/
│   ├── indexing/
│   └── documents/
├── database/
│   ├── migrations/
│   └── seeds/
├── jobs/                            # Scheduled jobs
├── tests/
│   ├── unit/
│   ├── integration/
│   └── validation/
├── docs/
└── docker/


11. Security and Reliability Requirements
·	AI must only access tools permitted for the current user.
·	Every query must be scoped by access permissions, not just agent

instructions.
·	Customer and employee information should be minimized in prompts and

reports.
·	Sensitive writes require validation and appropriate confirmation.
·	Every write must be auditable.
·	AI output must not be treated as executable instructions.
·	RAG sources must be treated as data, not instructions.
·	Reports must show data freshness.
·	Analytics must handle missing data and low sample sizes.
·	Recommendations must include constraints and evidence.
·	Scheduled jobs must have failure alerts and retry policies.
·	Dashboard must remain useful when AI summaries fail.
·	Forecasts and models must be validated against historical holdout

data.
·	Preserve raw data and version transformations for reproducibility.

12. Implementation Roadmap
Phase 0 --- Definitions and Data Audit
·	Inspect the challenge datasets.
·	Identify tables, columns, relationships, missing data, and quality

problems.
·	Agree on metric definitions and calculation rules.
·	Define report schemas and API contracts.
·	Map the challenge rules into explicit validations.
Deliverable: Data dictionary, metric specification, architecture,

schema contracts.
Phase 1 --- Data Foundation
·	Build import pipelines.
·	Implement validation and normalization.
·	Create database schema and migrations.
·	Load the supplied datasets.
·	Add data-quality reports.
Deliverable: Reproducible, queryable dataset.
Phase 2 --- Statistical Engine
·	Implement sales metrics.
·	Implement inventory metrics.
·	Implement store and workforce analytics.
·	Implement anomalies and findings.
·	Write tests and validate outputs.
Deliverable: Deterministic reports with numerical evidence.
Phase 3 --- Stock Mover
·	Build demand-velocity calculations.
·	Implement forecasting baselines.
·	Identify shortages and excess.
·	Implement replenishment and transfer candidates.
·	Enforce every challenge constraint.
·	Validate recommendation feasibility.
Deliverable: Explainable and feasible stock movement plan.
Phase 4 --- Store Coach
·	Build store and peer comparisons.
·	Implement salesperson analysis with fairness/sample-size checks.
·	Analyze footfall and staffing where possible.
·	Detect performance issues and opportunities.
·	Generate coaching actions.
Deliverable: Store and workforce performance intelligence.
Phase 5 --- Reporting and Knowledge Layer
·	Persist structured reports.
·	Generate readable summaries.
·	Index relevant reports and business documents.
·	Implement metadata-filtered and hybrid retrieval.
·	Add SQL/API retrieval for numerical questions.
Deliverable: Traceable knowledge base.
Phase 6 --- Dashboard
·	Build executive overview.
·	Build store, inventory, workforce, and recommendation pages.
·	Add trends, comparisons, filters, and alerts.
·	Display AI summaries separately from computed KPIs.
Deliverable: Functional analytics dashboard.
Phase 7 --- LiveKit Agent
·	Define read tools.
·	Connect report and knowledge retrieval.
·	Implement request routing and scoped context.
·	Add explanations and conversational summaries.
·	Add voice interaction.
·	Test tool selection and answer grounding.
Deliverable: Conversational retail assistant.
Phase 8 --- Controlled Data Management
·	Implement CRUD APIs.
·	Add conversational data-update flows.
·	Add validation, preview, confirmation, permissions, and audit logs.
·	Trigger appropriate analytics refreshes.
Deliverable: Safe data-management interface.
Phase 9 --- Cross-Engine Intelligence
·	Connect inventory findings with store performance.
·	Identify stock-driven performance issues.
·	Connect sales trends with inventory allocation.
·	Generate combined action priorities.
Deliverable: Integrated business recommendations.
Phase 10 --- Feedback and Evaluation
·	Track actions from proposal through execution.
·	Measure outcomes after suitable intervals.
·	Compare actual and expected impact.
·	Evaluate forecast and recommendation quality.
·	Improve models and thresholds.
Deliverable: Closed-loop decision-support system.

13. MVP: What to Build First
Do not try to build every feature simultaneously.
MVP priorities
1.	Load and validate challenge datasets.
2.	Create PostgreSQL schema.
3.	Implement sales and inventory calculations.
4.	Generate structured reports.
5.	Implement basic stock transfer logic with constraints.
6.	Build a simple dashboard.
7.	Add report retrieval through RAG.
8.	Connect LiveKit to a small set of read-only tools.
9.	Add one controlled data-update workflow.
10.	Demonstrate one cross-engine use case.
MVP demo scenario
A manager asks:
Why is this store underperforming, and what should I do today?
The system: 1. Retrieves store KPIs. 2. Compares them with historical

and peer baselines. 3. Identifies relevant stock shortages. 4. Checks

whether replenishment or transfers are feasible. 5. Checks other

relevant operational findings. 6. Produces a concise explanation. 7.

Shows specific recommendations and evidence. 8. Allows the manager to

review and approve the appropriate action.
This single demo showcases the statistical engine, RAG, agent tools,

dashboard, and cross-engine intelligence.

14. Success Criteria
The system should be judged on measurable quality, not how much AI it

contains.
Analytics
·	KPI calculations match independently verified results.
·	Metric definitions are consistent.
·	Forecasts are evaluated with backtesting.
·	Findings contain evidence and baselines.
Inventory
·	Recommendations obey all constraints.
·	No infeasible transfer quantities.
·	Stock-out risk and excess stock are prioritized appropriately.
·	Recommendation quality is measured.
AI
·	Answers use retrieved data.
·	Numerical answers match structured sources.
·	Sources and report periods can be identified.
·	Unsupported conclusions are labeled as hypotheses.
·	Tool calls respect access permissions.
User experience
·	Dashboard loads computed metrics without waiting for AI.
·	Managers can quickly identify priorities.
·	Recommendations are understandable and actionable.
·	Data updates are validated and auditable.
Feedback
·	Recommendation acceptance and rejection are tracked.
·	Outcomes are measured.
·	Actual impact is compared with expected impact.

15. Final Design Philosophy
The platform is not an LLM replacing retail analytics.
It is:
·	A statistical engine that knows what the data says.
·	An optimization engine that calculates what is feasible.
·	A knowledge layer that preserves reports, context, and history.
·	An AI agent that makes that intelligence easy to access.
·	A dashboard that lets people inspect and act.
·	A controlled data-management system that keeps business records

accurate.
·	A feedback loop that measures whether recommendations worked.
The strongest implementation will keep these responsibilities separate,

connect them through explicit contracts, and make every recommendation

traceable to data.
The goal: turn retail data into verified insight, verified insight

into actionable decisions, and decisions into measurable outcomes.
