# InventoryIQ V2 — Two-Person Team Prompt Plan
## Backend: whitelist | Frontend: Rams

> **Document role:** Defines HOW whitelist and Rams build InventoryIQ V2 together.
>
> **Product source of truth:** `InventoryIQv2.md`
>
> **Mathematical source of truth:** `InventoryIQv2_Calculations_and_Formulas.md`
>
> **This document:** `InventoryIQv2_TeamPromptPlan.md`
>
> **Important:** Old V1 MD files are historical only and must not be used as V2 requirements.

---

# 0. The Big Decision: Do Rams Need to Wait?

**No. Rams should NOT wait for the backend to be finished.**

That would waste a large amount of time.

The two of you can work in parallel as soon as the **shared contract and visual direction** are agreed.

The key is that Rams should build against **mock/stub data that has the same shape as the real backend outputs**.

```text
                    INVENTORYIQ V2
                          |
              +-----------+-----------+
              |                       |
              v                       v
       whitelist / BACKEND      Rams / FRONTEND
              |                       |
       real calculations        mock/contract data
              |                       |
              +-----------+-----------+
                          |
                    SHARED CONTRACT
                          |
                    final integration
```

The backend does NOT need to be finished before the frontend starts.

What must exist before integration is a stable **data contract**.

---

# 1. Team Roles

## whitelist — Backend Owner

Owns:

- CSV validation
- cleaning
- date handling
- aggregation
- derived variables
- demand statistics
- trend analysis
- outlier detection
- seasonality/pattern analysis
- inventory planning
- safety stock
- reorder point
- stockout probability
- reorder quantity
- excess inventory
- financial metrics
- financial exposure
- product risk score
- category risk
- overall inventory health
- recommendation engine
- scenario engine
- Gemini backend/context preparation
- backend tests
- mathematical verification
- backend contracts

whitelist is responsible for the **truth and decisions**.

## Rams — Frontend Owner

Owns:

- dashboard layout
- navigation
- filters
- KPI cards
- priority cards
- AI Business Brief presentation
- Product Explorer
- Product Deep Dive presentation
- Category Analysis UI
- Historical Analysis UI
- What-If UI
- charts
- tables
- visual hierarchy
- responsive layout
- styling
- loading/error/empty states
- frontend usability
- frontend tests where useful

Rams is responsible for **how the product looks and feels**.

## Shared

Both:

- agree on data contracts
- agree on UI requirements
- review integration
- run the full application
- perform final QA
- keep scope locked
- communicate before changing shared contracts

---

# 2. Non-Negotiable Ownership Boundaries

To avoid two people editing the same logic:

| Area | whitelist | Rams |
|---|---|---|
| `validation.py` | OWNER | Do not edit |
| `data_processing.py` | OWNER | Do not edit |
| `analysis.py` | OWNER | Do not edit |
| `recommendation.py` | OWNER | Do not edit |
| `scenario.py` | OWNER | Do not edit |
| `gemini.py` | OWNER | Do not edit backend logic |
| `app.py` | Shared integration / frontend-owned presentation | OWNER for UI |
| UI components | Review only | OWNER |
| Charts | Data meaning/backend contract | OWNER for presentation |
| Tests for backend | OWNER | Review |
| Tests for UI | Review | OWNER |
| Product specification MD | Shared, changes require agreement | Shared |
| Formula MD | whitelist owns mathematical changes; Rams reads it | Read-only |
| Prompt plan | Shared | Shared |

### Critical rule

Rams must **never recreate backend formulas in the frontend**.

For example, if backend returns:

```python
{
    "days_remaining": 4.2,
    "stockout_probability": 0.81,
    "risk_score": 92
}
```

the frontend displays those values.

It must NOT calculate:

```python
days_remaining = inventory / average_demand
```

inside the UI.

This prevents duplicated business logic and inconsistent numbers.

---

# 3. Recommended Git Workflow

Because two people are working simultaneously, do NOT both work directly on the same branch at the same time.

Recommended:

```text
main
 |
 +-- backend-v2
 |
 +-- frontend-v2
```

whitelist works on:

```text
backend-v2
```

Rams works on:

```text
frontend-v2
```

Only merge into `main` after the relevant work has been reviewed and tested.

## Shared rule

Before either person starts:

```bash
git pull
git status
```

Before committing:

```bash
git status
git diff
```

Then:

```bash
git add .
git commit -m "v2: describe change"
git push
```

Never:

- force push
- `git reset --hard`
- overwrite the other person's work
- commit secrets
- commit `.env`
- commit `.streamlit/secrets.toml`
- blindly merge conflicts

If a merge conflict affects a shared contract, **stop and discuss it before resolving it**.

---

# 4. Shared Contract Strategy

This is what makes parallel development possible.

The backend and frontend agree on the conceptual shape of outputs before the backend is complete.

The exact Python implementation may evolve, but the meaning of fields should remain stable.

## Processed data contract

Backend produces validated, cleaned daily records with derived fields such as:

- date
- product
- category
- inventory
- units_sold
- unit_cost
- selling_price
- supplier
- lead_time_days
- daily_revenue
- daily_profit
- inventory_value
- inventory_change
- sales_velocity
- profit_margin

## Product analysis contract

Conceptually:

```python
{
    "product": ...,
    "demand": {
        "mean": ...,
        "median": ...,
        "std": ...,
        "variance": ...,
        "cv": ...,
        "min": ...,
        "max": ...
    },
    "trend": {...},
    "outliers": {...},
    "inventory": {...},
    "replenishment": {...},
    "excess": {...},
    "seasonality": {...},
    "financial": {...},
    "risk": {...}
}
```

## Recommendation contract

```python
{
    "action": "REORDER",
    "priority": "HIGH",
    "reasons": [...],
    "evidence": {...}
}
```

Allowed actions:

- `REORDER`
- `HOLD / PAUSE REORDERING`
- `REDUCE EXCESS INVENTORY`
- `MONITOR`
- `NO ACTION`

## Gemini context contract

```python
{
    "verified_analysis": {...},
    "recommendation": {...},
    "business_context": {...}
}
```

These are conceptual contracts, not requirements to use literal dictionaries.

---

# 5. Frontend Mock Data Strategy

Rams can begin before real backend outputs exist.

Create a frontend-only fixture such as:

```text
tests/fixtures/
    dashboard_mock.json
    product_mock.json
    category_mock.json
    history_mock.json
    scenario_mock.json
```

These fixtures must represent **real backend semantics**, not invented UI-only calculations.

Example:

```json
{
  "product": "Wireless Mouse",
  "risk_score": 92,
  "risk_level": "HIGH",
  "current_inventory": 12,
  "days_remaining": 3.0,
  "reorder_point": 85,
  "stockout_probability": 0.82,
  "recommendation": {
    "action": "REORDER",
    "priority": "CRITICAL",
    "reasons": [
      "Inventory coverage is below supplier lead time"
    ]
  }
}
```

Mock numbers are allowed for development.

They must NEVER become hardcoded production business logic.

---

# 6. Parallel Development Plan

The development is deliberately split into three tracks:

```text
TRACK A — Shared Foundation
          |
          +--------------------+
          |                    |
          v                    v
TRACK B — Backend        TRACK C — Frontend
whitelist                 Rams
          |                    |
          +---------+----------+
                    |
                    v
             Integration
                    |
                    v
                Final QA
```

---

# PHASE 0 — Shared Project Kickoff

### Both

Goal:

Agree on:

- V2 scope
- folder structure
- ownership
- Git branches
- shared contracts
- visual direction
- mock data strategy

### Prompt to KiloCode for whitelist

```text
We are starting InventoryIQ V2 with a two-person team.

whitelist owns the backend.
Rams owns the frontend.

Read:
- InventoryIQv2.md
- InventoryIQv2_Calculations_and_Formulas.md
- InventoryIQv2_TeamPromptPlan.md

Do not implement features yet.

Audit the repository and report:
1. current structure
2. existing V1 code
3. reusable code
4. conflicting V1 assumptions
5. current dependencies
6. current tests
7. recommended V2 structure
8. files that should be backend-owned
9. files that should be frontend-owned
10. any shared files that could create merge conflicts

Do not modify code until the audit is complete.
```

### Exit gate

Both agree on ownership and structure.

---

# PHASE 1 — Shared Contract + Foundation

## whitelist

Build:

- Python environment
- dependency setup
- validation/processing module skeletons
- backend test structure
- contract definitions/stable output meanings
- representative sample dataset

Do NOT build the whole backend yet.

## Rams

At the same time:

- establish Streamlit UI shell
- navigation
- page/section structure
- global filter area
- styling system
- reusable card/table/chart containers
- loading/error/empty states
- frontend mock-data loader

Rams uses mock data.

### Important

Rams does NOT wait for backend calculations.

---

# PHASE 2 — Backend Data Contract

## whitelist

Implement:

- exact CSV schema
- validation
- cleaning
- date handling
- aggregation
- derived variables

Tests for:

- valid data
- missing columns
- invalid dates
- invalid numeric values
- invalid lead time
- duplicate product/date records
- missing inventory
- zero sales
- negative inventory
- insufficient data

### Backend gate

All validation tests pass.

### Rams

Continue UI using fixtures.

No dependency on live backend yet.

---

# PHASE 3 — Demand Analytics

## whitelist

Implement:

- mean
- median
- sample SD
- variance
- CV
- min/max
- demand volatility
- trend
- outliers
- seasonality/patterns

Use the formula document as the mathematical source of truth.

Create known-value tests.

### Rams

Build:

- Demand KPI cards
- demand trend chart
- volatility indicator
- outlier chart
- seasonality chart
- product deep-dive demand section

All using mock contract data.

---

# PHASE 4 — Inventory Planning

## whitelist

Implement and test:

- lead-time demand
- safety stock
- reorder point
- days remaining
- stockout probability
- reorder quantity

Required edge cases:

- zero demand
- zero SD
- missing lead time
- very large lead time
- inventory at zero
- inventory exactly at ROP
- inventory above ROP

### Mathematical checkpoint

Verify:

If inventory equals:

```text
ROP = lead-time demand + safety stock
```

then estimated stockout probability should approximately equal the service-level failure probability.

For 95% service:

```text
≈ 5%
```

### Rams

Build:

- inventory KPI cards
- safety stock display
- stockout risk display
- reorder information
- inventory chart
- risk visual components

Still uses mock data.

---

# PHASE 5 — Excess + Financial Analysis

## whitelist

Implement:

- target stock
- excess units
- excess value
- capital tied up
- revenue
- gross profit
- profit/unit
- margin
- revenue at risk
- profit at risk

Test financial edge cases.

### Rams

Build:

- financial KPI cards
- excess inventory section
- capital tied up presentation
- financial risk presentation
- tooltips/labels explaining estimated exposure

Do not rename backend metrics without agreement.

---

# PHASE 6 — Risk & Recommendations

## whitelist

Implement:

- product risk score
- risk level
- category risk
- overall inventory health
- recommendation engine

All five actions must work:

```text
REORDER
HOLD / PAUSE REORDERING
REDUCE EXCESS INVENTORY
MONITOR
NO ACTION
```

Test conflicting signals.

Example:

```text
high stockout risk
+
high excess inventory
```

must produce a sensible business decision.

Every recommendation must carry evidence/reasons.

### Rams

Build:

- overall health section
- risk badges
- top-priority cards
- recommendation cards
- product explorer table
- filters/sorting

---

# PHASE 7 — Product Explorer + Deep Dive

## whitelist

Expose a stable product-level result structure.

No new backend calculations unless required by the approved V2 specification.

## Rams

Build the complete Product Explorer:

```text
Product
Risk Score
Risk Level
Main Issue
Recommendation
```

Allow:

- search
- sorting
- risk filtering
- category filtering
- stockout filtering
- excess filtering
- product selection

Then build Product Deep Dive:

- demand
- trend
- outliers
- seasonality
- inventory
- safety stock
- stockout probability
- financials
- risk
- recommendation

Use mock data until integration.

---

# PHASE 8 — Category Analysis

## whitelist

Finalize category-level outputs.

Ensure category risk:

- reuses the product methodology
- does not make categories risky solely because they contain expensive products
- includes meaningful magnitude/context

## Rams

Build:

- category KPI cards
- category risk comparison
- inventory value by category
- stockout exposure
- excess inventory
- high-risk product counts

---

# PHASE 9 — Historical Analysis

## whitelist

Expose the historical data needed by the frontend.

Historical analysis must use actual observations.

Do not create a second source of truth.

## Rams

Build:

- sales over time
- inventory over time
- product/category selection
- date range
- optional event markers

Trend and seasonality remain calculations; Historical Analysis remains the exploration layer.

---

# PHASE 10 — What-If Scenario Engine

## whitelist

Implement `scenario.py`.

Requirements:

- scenario changes assumptions
- actual dataset remains unchanged
- same analysis engine is reused
- baseline vs scenario outputs are comparable
- demand change supported
- lead-time change supported
- reset behaviour supported

Scenario propagation should work:

```text
Demand change
 ↓
Days remaining
 ↓
Stockout risk
 ↓
Safety-stock / planning outputs
 ↓
Reorder quantity
 ↓
Financial exposure
 ↓
Recommendation
```

## Rams

Build:

- demand slider/input
- lead-time control
- baseline vs scenario cards
- comparison chart
- impact summary
- Reset Scenario
- clear explanation that scenario values are hypothetical

---

# PHASE 11 — Gemini

## whitelist

First perform a dependency/environment gate.

Check:

1. exact SDK/package
2. package installed in active `.venv`
3. import works
4. API key loads correctly
5. minimal API request works
6. model response is received
7. response parsing works

Only after the gate passes should full Gemini integration begin.

Gemini receives verified outputs only.

It must never:

- calculate core metrics
- change Python values
- override recommendations
- invent facts

Implement:

1. Executive Business Brief
2. Product Deep-Dive Explanation

## Rams

Build Gemini presentation:

- executive brief area
- generate button/state
- loading state
- error state
- product AI explanation area

Rams can change the visual presentation without changing the Gemini backend contract.

---

# PHASE 12 — First Integration

This is the first point where mock data starts being replaced by live backend outputs.

Order:

```text
CSV
 ↓
validation
 ↓
processing
 ↓
analysis
 ↓
risk
 ↓
recommendation
 ↓
frontend
```

Do NOT integrate everything at once.

Integrate in slices:

### Slice 1

Dashboard KPIs.

### Slice 2

Top priorities.

### Slice 3

Product Explorer.

### Slice 4

Product Deep Dive.

### Slice 5

Category Analysis.

### Slice 6

Historical Analysis.

### Slice 7

Scenario Analysis.

### Slice 8

Gemini.

After every slice:

```text
run tests
run app
verify values
check UI
check contracts
commit
```

---

# PHASE 13 — Full Integration Testing

## Both

Test the real path:

```text
Upload CSV
 ↓
Validation
 ↓
Processing
 ↓
Analysis
 ↓
Risk
 ↓
Recommendation
 ↓
Dashboard
 ↓
Explorer
 ↓
Deep Dive
 ↓
Category
 ↓
History
 ↓
Scenario
 ↓
Gemini
```

Check:

- no missing fields
- no incorrect field names
- no UI-side recalculation
- no stale mock values
- filters propagate correctly
- product selection propagates correctly
- scenario values don't mutate baseline
- Gemini receives correct verified context

---

# PHASE 14 — Mathematical Audit

## whitelist leads

Independently verify:

- mean
- SD
- variance
- CV
- trend
- IQR
- MAD fallback
- seasonality factors
- lead-time demand
- safety stock
- ROP
- stockout probability
- reorder quantity
- excess inventory
- financial metrics
- revenue/profit at risk
- risk score

Use known-value synthetic datasets.

Do not rely solely on the application output as proof.

---

# PHASE 15 — Recommendation Business Audit

## Both

Create synthetic scenarios such as:

### Scenario A

Low inventory + high demand + long lead time.

Expected direction:

```text
REORDER
```

### Scenario B

Huge inventory + weak demand + low stockout exposure.

Expected direction:

```text
REDUCE EXCESS INVENTORY
```

### Scenario C

Healthy inventory + stable demand.

Expected direction:

```text
NO ACTION
```

### Scenario D

Some risk but not urgent.

Expected direction:

```text
MONITOR
```

### Scenario E

Inventory is excessive and adding more would worsen the situation.

Expected direction:

```text
HOLD / PAUSE REORDERING
```

Also test conflicting signals.

---

# PHASE 16 — Data Quality / Failure Audit

Test:

- empty CSV
- missing required columns
- invalid dates
- missing inventory
- zero demand
- zero SD
- negative inventory
- invalid lead time
- duplicate product/date
- insufficient history
- missing categories
- unusual outliers
- selling price below cost
- very large values

The application should fail **clearly and safely**, not silently produce nonsense.

---

# PHASE 17 — UX Audit

## Rams leads

Check:

- Can a user understand inventory health immediately?
- Can they see what needs attention?
- Can they understand why?
- Can they find a product quickly?
- Can they understand its risk?
- Can they see the recommendation?
- Can they inspect history?
- Can they run a scenario?
- Can they understand the AI output?
- Are estimates clearly labelled?
- Are charts readable?
- Are there duplicate KPIs?
- Are there confusing terms?
- Is the dashboard overloaded?

Fix presentation problems without changing backend methodology.

---

# PHASE 18 — Scope-Creep Audit

## Both

Compare implementation against `InventoryIQv2.md`.

Look for:

- undocumented features
- accidental V1 features
- duplicate features
- unnecessary dependencies
- unnecessary modules
- duplicated calculations
- optional features that became mandatory
- features that can be removed without damaging the product

Do not add features during this audit.

Remove/defer unnecessary additions.

---

# PHASE 19 — Final Code Review

## whitelist reviews backend

Check:

- duplicated logic
- large functions
- unclear names
- hidden assumptions
- fragile parsing
- swallowed exceptions
- inconsistent returns
- unsafe secrets
- hardcoded business rules
- unnecessary dependencies

## Rams reviews frontend

Check:

- duplicated UI code
- unnecessary components
- unreadable layouts
- inconsistent spacing
- confusing labels
- broken states
- dead UI
- unnecessary charts
- mock data accidentally remaining
- frontend-side calculations
- poor error handling

---

# PHASE 20 — Final Regression

Run:

- unit tests
- mathematical known-value tests
- validation tests
- recommendation scenario tests
- scenario tests
- integration tests
- Gemini mock tests
- frontend tests where applicable

Then run the application end-to-end using the representative dataset.

Report:

- total tests
- passed
- failed
- skipped
- warnings
- known limitations

Never declare success with unresolved critical failures.

---

# PHASE 21 — Final Product Verification

The final product must prove:

```text
CSV Upload
    ↓
Validation
    ↓
Processing
    ↓
Analysis
    ↓
Risk
    ↓
Recommendation
    ↓
Dashboard
    ↓
Product Explorer
    ↓
Product Deep Dive
    ↓
Category Analysis
    ↓
Historical Analysis
    ↓
Scenario Analysis
    ↓
Gemini
    ↓
Full QA
```

And critically:

```text
If Gemini is unavailable:

InventoryIQ still calculates
+
InventoryIQ still shows risk
+
InventoryIQ still recommends actions
+
Dashboard still works
```

Gemini is an enhancement, not a dependency for the deterministic core.

---

# 22. Standard KiloCode Prompt Format

whitelist should give KiloCode focused prompts.

Use:

```text
Implement ONLY [PHASE/TASK].

Read:
- InventoryIQv2.md
- InventoryIQv2_Calculations_and_Formulas.md
- InventoryIQv2_TeamPromptPlan.md

Before coding:
1. inspect the existing implementation
2. inspect relevant contracts
3. identify dependencies
4. explain the implementation approach briefly

Requirements:
[focused requirements]

Do NOT:
- modify unrelated modules
- add features
- change approved formulas
- move business logic into the UI
- redesign unrelated parts

After coding:
1. run relevant tests
2. run the application if appropriate
3. report all failures/warnings
4. show changed files
5. do not continue automatically to the next phase
```

---

# 23. Standard Rams Workflow

Rams can work independently using:

```text
V2 product specification
        +
shared contracts
        +
mock fixtures
        ↓
frontend implementation
```

Rams does NOT need to ask whitelist for every UI decision.

Rams is free to improve:

- layout
- typography
- card design
- chart presentation
- spacing
- navigation
- interaction
- AI presentation

as long as:

1. backend meanings are preserved
2. values aren't recalculated
3. no new product feature is silently added
4. shared contracts aren't changed without agreement

---

# 24. Contract Change Protocol

If Rams needs a field that doesn't exist:

Do NOT invent a calculation.

Instead:

```text
Rams identifies required field
        ↓
asks whitelist
        ↓
whitelist checks V2 specification
        ↓
if already supported:
backend exposes it
        ↓
if not supported:
decide whether it is genuinely required
        ↓
update contract only if approved
```

If whitelist wants to change the meaning of an existing field:

```text
STOP
 ↓
tell Rams
 ↓
agree on new meaning
 ↓
update contract
 ↓
update backend tests
 ↓
update frontend fixtures
 ↓
integrate
```

This prevents silent contract drift.

---

# 25. Integration Rules

Never integrate an unfinished backend feature by guessing its output.

Instead:

```text
Backend output contract
        ↓
Frontend fixture
        ↓
Frontend UI
        ↓
Live backend
```

This means Rams can be ahead of whitelist without being blocked.

---

# 26. Testing Strategy

InventoryIQ needs three types of confidence.

## Mathematical confidence

Does the formula produce the correct number?

## Integration confidence

Does the correct number travel through every layer?

## Business confidence

Does the resulting recommendation make sense?

All three are required.

```text
Correct math
+
Correct integration
+
Correct business decision
=
Reliable InventoryIQ
```

---

# 27. Scope Lock

Do NOT add:

- PDF reports
- authentication
- database
- notifications
- chatbot
- Shopify integration
- forecasting system
- EOQ
- MOQ
- supplier reliability model
- lead-time variability model without data
- unnecessary pages
- random AI features
- duplicate analytics
- arbitrary charts
- features from old V1 documentation

Optional Advanced Visualization remains optional.

If time becomes tight:

**drop optional visuals before compromising core calculations, recommendations, testing, or integration.**

---

# 28. Recommended Work Order for the Two of You

The actual schedule should look like this:

```text
DAY / STAGE 1
Both:
  Foundation + contracts

whitelist:
  validation + processing

Rams:
  dashboard shell + design system

              ↓

STAGE 2
whitelist:
  demand + inventory analytics

Rams:
  demand + inventory UI

              ↓

STAGE 3
whitelist:
  risk + recommendations

Rams:
  health + priorities + explorer

              ↓

STAGE 4
whitelist:
  category + history + scenarios

Rams:
  category + history + scenario UI

              ↓

STAGE 5
whitelist:
  Gemini backend

Rams:
  Gemini UI

              ↓

STAGE 6
Both:
  integration

              ↓

STAGE 7
Both:
  testing + audits + polish
```

The stages are not necessarily days. Move at the pace of the project.

---

# 29. The Most Important Rule for whitelist + Rams

Never think:

> "Backend first, frontend later."

Think:

> **"Backend and frontend develop in parallel against a shared contract."**

The backend provides the **meaning**.

The frontend provides the **experience**.

The contract connects them.

---

# 30. Final Architecture

```text
                    INVENTORYIQ V2

                         CSV
                          |
                          v
                 +----------------+
                 | validation.py  |
                 +-------+--------+
                         |
                         v
                 +-------------------+
                 | data_processing.py|
                 +---------+---------+
                           |
                           v
                    +-------------+
                    | analysis.py |
                    +------+------+
                           |
                           v
                 Risk & Health Layer
                           |
                           v
                 +------------------+
                 | recommendation.py|
                 +--------+---------+
                          |
             +------------+-------------+
             |                          |
             v                          v
        scenario.py                 gemini.py
             |                          |
             +------------+-------------+
                          |
                          v
                  SHARED DATA CONTRACT
                          |
                          v
                       app.py
                          |
                          v
                    Rams FRONTEND
                          |
        +---------+-------+--------+----------+
        |         |       |        |          |
      Health   Explorer Category History   Scenarios
        |
        v
   Product Deep Dive
        |
        v
    Gemini Brief
```

---

# 31. Definition of Done

InventoryIQ V2 is done when:

### Backend

- [ ] CSV validation works
- [ ] processing works
- [ ] derived variables are correct
- [ ] demand statistics are correct
- [ ] trend works
- [ ] outliers work
- [ ] seasonality works
- [ ] safety stock works
- [ ] ROP works
- [ ] stockout probability works
- [ ] reorder quantity works
- [ ] excess inventory works
- [ ] financial metrics work
- [ ] risk scoring works
- [ ] category analysis works
- [ ] overall health works
- [ ] recommendations work
- [ ] scenarios work
- [ ] Gemini backend works
- [ ] backend tests pass

### Frontend

- [ ] dashboard works
- [ ] filters work
- [ ] health section works
- [ ] priorities work
- [ ] AI brief works
- [ ] product explorer works
- [ ] product deep dive works
- [ ] category analysis works
- [ ] historical analysis works
- [ ] scenario UI works
- [ ] charts are understandable
- [ ] error/loading/empty states work
- [ ] no frontend-side business calculations
- [ ] no stale mock data

### Final

- [ ] integration tests pass
- [ ] mathematical audit passes
- [ ] recommendation audit passes
- [ ] data-quality audit passes
- [ ] Gemini failure does not break deterministic core
- [ ] UX audit passes
- [ ] scope audit passes
- [ ] dependency audit passes
- [ ] no secrets committed
- [ ] Git working tree is clean
- [ ] final application works end-to-end

---

# 32. Golden Development Loop

For whitelist:

```text
Choose ONE backend task
        ↓
Give focused prompt to KiloCode
        ↓
KiloCode implements
        ↓
KiloCode tests
        ↓
whitelist reviews result
        ↓
ChatGPT reviews methodology/architecture
        ↓
Fix if necessary
        ↓
Commit
        ↓
Update shared contract only if approved
```

For Rams:

```text
Choose ONE frontend task
        ↓
Use approved contract/mock fixture
        ↓
Build UI
        ↓
Test with fixture
        ↓
Check UX
        ↓
Confirm no backend logic was duplicated
        ↓
Commit
```

For integration:

```text
Frontend fixture
      ↓
Replace with live backend
      ↓
Verify field-by-field
      ↓
Run tests
      ↓
Run app
      ↓
Check visual result
      ↓
Commit
```

---

# 33. Final Mental Model

InventoryIQ V2 is still:

```text
RAW BUSINESS DATA
        ↓
CLEAN
        ↓
UNDERSTAND DEMAND
        ↓
UNDERSTAND INVENTORY
        ↓
CALCULATE RISK
        ↓
DECIDE ACTION
        ↓
PRESENT CLEARLY
        ↓
EXPLAIN WITH AI
```

But development is now:

```text
             YOU + RAMS
                 |
        +--------+--------+
        |                 |
        v                 v
   whitelist           Rams
   BACKEND            FRONTEND
        |                 |
        |    CONTRACT     |
        +--------+--------+
                 |
                 v
             INTEGRATE
                 |
                 v
              TEST
                 |
                 v
               AUDIT
                 |
                 v
              SHIP
```

**The most important improvement over the original Prompt Plan is parallelism through contracts and fixtures.**

Rams does **not** need to wait for the backend to finish.

whitelist builds the real intelligence.

Rams builds the real interface.

The shared contract prevents the two sides from drifting apart.

And ChatGPT remains the external review layer: after important backend milestones, bring KiloCode's report/results here and I will check **math → architecture → integration → edge cases → scope → business logic** before you move forward.