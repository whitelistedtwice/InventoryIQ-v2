# InventoryIQ V2 --- Two-Person KiloCode Prompt Plan

> **Team:** whitelist = Backend / Data / Logic; Rams = Frontend / UI /
> UX\
> **Primary implementation agent:** KiloCode\
> **Review:** ChatGPT\
> **Product source of truth:** `InventoryIQv2.md`\
> **Math source of truth:**
> `InventoryIQv2_Calculations_and_Formulas.md`\
> **This document:** `InventoryIQv2_TeamPromptPlan.md`

## 1. Core Workflow

KiloCode builds. ChatGPT reviews. whitelist owns backend truth. Rams
owns presentation.

``` text
                    V2 SPEC
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       whitelist BACKEND      Rams FRONTEND
             │                   │
        real outputs        mock fixtures
             │                   │
             └─────────┬─────────┘
                       ▼
                  INTEGRATION
                       ▼
                 CHATGPT REVIEW
                  /          \
               PASS          FIX
                │             │
             COMMIT      KiloCode fixes
                │             │
                └──────┬──────┘
                       ▼
                   NEXT PHASE
```

**Rams does not need to wait for the backend.** He builds against stable
contracts and mock fixtures, then swaps fixtures for real outputs during
integration.

## 2. Ownership

### whitelist

`validation.py`, `data_processing.py`, `analysis.py`, risk/health
aggregation, `recommendation.py`, `scenario.py`, `gemini.py`, backend
tests, mathematical/business correctness.

### Rams

`app.py` presentation layer, navigation, filters, KPI cards, priorities,
Product Explorer, Product Deep Dive presentation, Category UI,
Historical UI, Scenario UI, Gemini presentation, loading/error/empty
states and visual polish.

### Shared

Contracts, integration, Git coordination, final QA and release.

## 3. Contract Rules
**Critical data rule:** missing inventory must NOT become zero. Missing inventory remains missing/unavailable and must be handled explicitly.


Conceptual analysis contract:

``` python
{
    "product": ...,
    "demand": {...},
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

Recommendation contract:

``` python
{
    "action": ...,
    "priority": ...,
    "reasons": [...],
    "evidence": {...}
}
```

Gemini context:

``` python
{
    "verified_analysis": {...},
    "recommendation": {...},
    "business_context": {...}
}
```

These are conceptual contracts; implementation may use
dictionaries/dataclasses/classes. **Meaning and required fields must
remain stable.**

The frontend never recreates backend formulas.

## 4. Parallel Development Rules

Rams may use mock data while backend work is unfinished.

Mock fixtures must use the same contract shape as real outputs and must
include: - high stockout risk - high excess - high volatility -
increasing demand - decreasing demand - healthy/no action -
medium/monitor

Mock values must never become hidden backend constants.

## 5. Git Rules

Use separate branches where practical:

``` text
main
├── backend-whitelist
└── frontend-rams
```

Before every meaningful commit:

``` bash
git status
git diff
```

Never commit API keys, `.env`, Streamlit secrets or unrelated work.
Never force-push or use `git reset --hard` as a routine fix.

If a shared contract must change:

``` text
need discovered
→ explain why
→ check V2 spec
→ check consumers
→ agree
→ update contract
→ update tests/code
→ integrate
```

## 6. Review Rule

A KiloCode report saying "done" is not enough.

A phase is complete only when: 1. implementation exists, 2. relevant
tests pass, 3. ChatGPT review passes, 4. any required fixes are made, 5.
the milestone is committed.

## 7. Debugging Rule

When something fails:

``` text
STOP
→ reproduce
→ find earliest failing layer
→ inspect input
→ inspect output
→ check contract
→ fix root cause
→ smallest relevant test
→ regression test
→ continue
```

For Gemini specifically:

``` text
environment
→ package
→ import
→ API key/config
→ minimal request
→ response
→ parsing
→ dashboard
```

Do not rewrite prompts before checking the actual failing layer.

## 8. Scope Lock

Do not add: - PDF/report export - EOQ - authentication - database -
notifications - chatbot - Shopify integration - unrelated forecasting
systems - duplicate risk/health features - duplicate product
explorer/deep dive features - automatic outlier deletion - UI-side
copies of backend business logic

The optional Advanced Visualization Layer is only a late BUILD/DEFER
decision.

------------------------------------------------------------------------

## Phase 0 --- Repository Audit

**Owner:** whitelist

### KiloCode prompt

``` text
We are rebuilding InventoryIQ as V2. Read InventoryIQv2.md, InventoryIQv2_Calculations_and_Formulas.md and InventoryIQv2_TeamPromptPlan.md. Old V1 MD files are historical only. Do NOT modify files. Audit the repository: structure, dependencies, Python environment, tests, reusable code, V1 assumptions that conflict with V2, backend/frontend conflict risks, and recommended minimal V2 structure. Report and stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 1 --- Project Foundation

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 1. Create the minimal V2 structure: app.py, validation.py, data_processing.py, analysis.py, recommendation.py, scenario.py, gemini.py, tests, data, requirements. Set up the Python environment and test runner. Do not implement business logic, final UI, or Gemini. Verify imports, test runner, app skeleton and active environment. Run tests and stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 2 --- Data Contract & Validation

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 2 using the exact V2 schema: date, product, category, inventory, units_sold, unit_cost, selling_price, supplier, lead_time_days. Validate columns, types, dates, numeric fields, lead time, duplicate product/date records, missing inventory and invalid values. Missing inventory must NOT become zero; legitimate zero sales must remain zero. Test valid data, missing columns, invalid dates/numbers, invalid lead time, duplicates, missing inventory, zero sales, negative inventory and missing values. Do not implement analysis/recommendations/UI. Run tests and stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 3 --- Data Processing & Derived Variables

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 3. Handle dates, sorting, valid daily aggregation, and derived variables: daily revenue, daily profit, inventory value, inventory change, sales velocity and profit margin. Inventory is END-OF-DAY inventory. Never use inventory change as a demand proxy. Preserve zero sales and missing inventory semantics. Test receiving-stock cases, zero sales, zero selling price, negative margin and missing inventory. Run tests and stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 4 --- Demand Statistics

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 4 from the calculation document: mean, median, sample SD (ddof=1), variance, CV, min, max and volatility classification. Handle zero demand, zero SD, insufficient observations and missing values. CV must not divide by zero. Add known-value mathematical tests. Do not implement trend/risk/recommendations/UI. Run tests and stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 5 --- Trend & Outliers

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 5. Trend uses OLS Demand_t = a + b*t and TrendStrength = b*(n-1)/mean_demand, with >+10% increasing, <-10% decreasing, otherwise stable. Outliers use IQR fences; use the approved MAD fallback where appropriate. Never delete outliers. Add known-value and edge tests. Do not modify inventory planning or recommendations. Run tests and stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 6 --- Inventory Planning

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 6 from the math document: lead-time demand mu*L; sigma_LT=s*sqrt(L); safety stock=z*s*sqrt(L), default service level 95% and z≈1.645; ROP=mu*L+SS; days remaining=inventory/mu; reorder quantity=max(0,ROP-inventory); stockout probability=1-Phi((I-mu*L)/(s*sqrt(L))). Handle zero demand, zero SD, invalid/missing lead time and insufficient data. No EOQ/MOQ. Add known-value tests and verify inventory=ROP gives approximately 1-service-level stockout probability. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 7 --- Excess & Financial Analysis

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 7. Financials: revenue, COGS, gross profit, profit/unit, margin, inventory value. ShortageUnits=max(0,mu*L-I); RevenueAtRisk=ShortageUnits*SellingPrice; ProfitAtRisk=ShortageUnits*(SellingPrice-UnitCost). Excess: TargetStock=mu*H+SS, default H=30 days; ExcessUnits=max(0,I-TargetStock); ExcessValue=ExcessUnits*UnitCost. ROP is NOT max inventory. Label estimates appropriately. Test known values and edge cases. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 8 --- Seasonality & Patterns

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 8. Weekday factor = weekday mean / overall mean; monthly factor = month mean / overall mean. Provide weekday/weekend and demand peak/drop patterns. Require roughly 4+ weeks for meaningful weekday patterns and 12+ months for true annual monthly seasonality; shorter history is an observed monthly pattern. Do not invent missing calendar dates as zero unless dataset semantics establish a complete daily record. Test insufficient history and zero overall demand. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 9 --- Product Risk Score

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 9. Initial 0–100 risk framework: stockout 30%, volatility 20%, trend 15%, excess 15%, financial exposure 10%, seasonality 10%. Risk levels 0–39 LOW, 40–69 MEDIUM, 70–100 HIGH. Normalize financial exposure relatively, not by raw dollars. Outliers are not a major direct component. Centralize normalization/configuration. Create synthetic low/medium/high and conflicting-signal tests. Treat weights as initial pending validation. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 10 --- Category Risk & Overall Health

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 10. Aggregate category risk, inventory value, capital tied up, stockout exposure, excess inventory, volatility, high-risk counts, and overall health. Reuse product methodology; do not create a second unrelated risk model. Do not make a category risky solely because it is expensive. Use shared explainable aggregation and configurable thresholds. Test healthy, stockout-heavy, excess-heavy, volatile and mixed businesses. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 11 --- Recommendation Engine

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 11. Allowed actions ONLY: REORDER, HOLD / PAUSE REORDERING, REDUCE EXCESS INVENTORY, MONITOR, NO ACTION. Recommendations must use verified signals, include action, priority, reasons and evidence, and provide reorder quantity when applicable. HOLD means pause adding stock; REDUCE means address existing excess. Test conflicting signals: stockout+excess, rising demand+low stock, falling demand+high stock, volatility with adequate coverage, healthy, zero demand and missing lead time. Gemini must never decide. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 12 --- Scenario Engine

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 12. Scenario assumptions must never mutate the real dataset. Reuse the SAME analysis engine. Required controls: demand change and lead-time change. Demand +20% means average demand * 1.20. Use supplier lead time for lead-time-dependent calculations. Test propagation through coverage, stockout risk, safety stock/ROP, reorder quantity, financial exposure and recommendations. Test baseline unchanged, same-engine reuse, +20%, lead-time change, unchanged scenario and reset. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 13 --- Gemini Environment Gate

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY the Gemini environment gate. Do not build the final Gemini feature. In the project's actual active environment verify: exact SDK/package installed, import works, secure API key/config exists, minimal API request works, response arrives and parsing works. Never print the key. If anything fails, diagnose the earliest failing layer and fix only that environment/dependency issue. Do not integrate until the gate passes. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 14 --- Gemini Module

**Owner:** whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 14. Gemini has exactly two jobs: Executive Business Summary and selected Product Deep-Dive Explanation. Give Gemini verified backend outputs, not raw CSV. It must not calculate authoritative metrics, alter numbers, override recommendations or invent facts. Implement graceful failure so deterministic InventoryIQ works without Gemini. Add mocked tests and stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 15 --- Frontend Foundation

**Owner:** Rams

### KiloCode prompt

``` text
Implement ONLY Phase 15 using InventoryIQv2.md. Build the Streamlit UI shell, navigation, global date/category/product filters, reusable cards/status/risk components and clear loading/empty/error states. Use mock fixtures. Do not implement backend formulas or new features. The UI must be able to replace fixture data with backend outputs without architectural redesign. Run the app and stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 16 --- Inventory Health Dashboard

**Owner:** Rams

### KiloCode prompt

``` text
Implement ONLY Phase 16. Using mock data if needed, build Inventory Health and Top Priorities: overall status, products at risk, stockout exposure, excess inventory, capital tied up, revenue/profit risk and ranked priorities. Use the recommendation contract. Never recalculate backend metrics in the UI. Avoid duplicate KPIs and clearly label estimates. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 17 --- Product Explorer

**Owner:** Rams

### KiloCode prompt

``` text
Implement ONLY Phase 17. Build an interactive table: product, risk score, risk level, main issue and recommendation. Add search, sorting and filters for risk, category, stockout risk and excess inventory. Selecting a product opens Product Deep Dive. Do not calculate risk/recommendations in the UI. Use the approved contract and mock data if necessary. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 18 --- Product Deep Dive

**Owner:** Rams

### KiloCode prompt

``` text
Implement ONLY Phase 18. Present demand statistics, trend, outliers, patterns, inventory, inventory history, safety stock, ROP, days remaining, estimated stockout probability, financial metrics, estimated revenue/profit exposure, risk, recommendation and evidence. Use backend values; do not recreate formulas. Provide the Gemini button but do not invent AI functionality. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 19 --- Category Analysis UI

**Owner:** Rams

### KiloCode prompt

``` text
Implement ONLY Phase 19. Present category risk, inventory value, stockout exposure, excess inventory, high-risk counts and useful volatility indicators plus a clear category comparison visual. Use backend-provided category analysis. Do not recreate risk calculations or add features. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 20 --- Historical Analysis UI

**Owner:** Rams

### KiloCode prompt

``` text
Implement ONLY Phase 20. Build historical sales and inventory views with product/category and date-range selection. Where supported by backend, show stockout, replenishment, demand-spike and safety-stock-breach markers. Historical views show observations; they must not create a separate calculation engine. Keep historical exploration distinct from trend calculation. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 21 --- What-If UI

**Owner:** Rams

### KiloCode prompt

``` text
Implement ONLY Phase 21. Build demand-change and lead-time controls, baseline vs scenario comparison, impact summary and Reset Scenario. The UI must call the scenario contract and never mutate data or recalculate scenario metrics. Make the causal chain understandable. Do not add extra controls unless explicitly approved. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 22 --- Gemini UI

**Owner:** Rams + whitelist

### KiloCode prompt

``` text
Implement ONLY Phase 22. Connect the approved Gemini contract to the UI. Executive output: concise status plus roughly 3–5 useful bullets covering biggest problem, financial impact, demand situation, risks and actions. Product output explains the selected product and recommendation using verified information. Gemini failure must leave deterministic features working. No chatbot. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 23 --- Integration Slice 1

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Integrate validation → processing → analysis → dashboard and connect real outputs to Inventory Health, priorities, Product Explorer and Product Deep Dive where available. Compare real contracts with frontend fixtures before changing anything. Do not silently rename fields. Verify displayed values equal backend outputs. Run integration tests and report remaining mock data. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 24 --- Integration Slice 2

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Integrate category and historical analysis. Verify product/category/date filters propagate correctly, UI values match backend values, and empty results are handled. Test normal/high-risk product, category and date range. Do not add features. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 25 --- Integration Slice 3: Scenarios

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Integrate scenario engine and UI. Verify baseline remains unchanged, assumptions are temporary, the same analysis engine is used, demand and lead-time changes propagate, UI does not recalculate metrics, and Reset returns baseline. Test +20% demand, negative demand change, increased lead time, unchanged scenario and reset. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 26 --- Gemini End-to-End Integration

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Integrate Gemini end-to-end. Recheck the environment gate. Verify backend context → gemini.py → API → parsing → executive brief/product explanation. Test API failure. Deterministic analysis/recommendations must still work when Gemini is unavailable. Do not send unnecessary raw CSV. No chatbot. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 27 --- Mathematical Audit

**Owner:** whitelist

### KiloCode prompt

``` text
Perform a strict mathematical audit against InventoryIQv2_Calculations_and_Formulas.md. Check mean, median, sample SD, variance, CV, OLS trend, trend strength, IQR/MAD, pattern factors, lead-time demand, safety stock, ROP, days remaining, stockout probability, reorder quantity, excess, financials, exposure and risk. Check units, rounding, zero/missing/insufficient data and missing lead time. Report expected vs actual and severity. Do not add features. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 28 --- Recommendation & Business Audit

**Owner:** whitelist

### KiloCode prompt

``` text
Audit all five recommendation actions and their priorities/reasons/evidence. Test conflicting signals and verify business sense, reorder quantity, excess vs ROP distinction, healthy NO ACTION, zero-demand handling and missing-lead-time behaviour. Return PASS/FAIL/WARNING for each area. Do not add features. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 29 --- Data Quality & Failure Audit

**Owner:** whitelist

### KiloCode prompt

``` text
Audit missing columns, invalid dates/numbers, missing inventory, negative inventory, zero demand, zero SD, duplicate product/date, missing lead time, insufficient history, negative margin, empty data, single-product/day data and multiple categories/suppliers. Verify no invented data, no silent outlier deletion, no crashes and clear unavailable-calculation states. Run tests and report failures/warnings. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 30 --- Contract Audit

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Audit every backend/frontend contract: field names, meanings, types, null behaviour, ordering where relevant, risk/recommendation/category/scenario/Gemini structures. Find stale V1 fields, frontend misunderstandings, duplicated transformations and UI-side calculations. Fix only approved mismatches and run integration tests. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 31 --- UX Audit

**Owner:** Rams

### KiloCode prompt

``` text
Perform a strict UX audit. Check whether users can understand health, priorities, reasons, products, risk, recommendations, history, scenarios and Gemini. Check estimate labels, chart clarity, filters, duplicate KPIs, terminology, overload and empty/error/loading states. Improve presentation only; do not change backend methodology or add features. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 32 --- Scope-Creep Audit

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Compare implementation against InventoryIQv2.md. List every feature, undocumented feature, accidental V1 feature, duplicate, unnecessary dependency/module, UI-duplicated business logic, optional feature made mandatory, and removable feature. Do not add anything. Recommend removal/deferment outside scope. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 33 --- Optional Visualization Gate

**Owner:** Rams + whitelist

### KiloCode prompt

``` text
Evaluate the optional Advanced Visualization Layer. Do NOT implement yet. Decide BUILD or DEFER based on core completion, passing critical tests, schedule, understanding benefit and complexity risk. No other feature may be added. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 34 --- Full Regression

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Run the complete V2 suite: unit, edge, known-value math, recommendation scenarios, scenarios, integration, Gemini mocks, validation and frontend/rendering tests where available. Run the app end-to-end with representative data. Report total/passed/failed/skipped/warnings/limitations. Do not declare success with critical failures. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 35 --- Final Code Review

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Review the complete codebase for duplicated logic, oversized functions, unclear names, magic numbers, hidden assumptions, fragile parsing, swallowed exceptions, unsafe API handling, UI/backend coupling, unnecessary dependencies, dead code, inconsistent returns, undocumented rules and stale V1 code. Do not rewrite working code merely for style. Run regression tests after fixes. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 36 --- Git & Security Audit

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Before release, inspect git status and git diff. Check secrets, API keys, .env, Streamlit secrets, debug/temp files and unrelated modifications. Do not commit or push yet. Do not force push or reset --hard. Report exactly what is ready and what must be removed. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

## Phase 37 --- Final Product Verification

**Owner:** whitelist + Rams

### KiloCode prompt

``` text
Perform final release verification against all three V2 documents. Verify CSV upload → validation → processing → analysis → risk → recommendations → dashboard → explorer → deep dive → category → history → scenarios → Gemini → tests. Also verify calculations, contracts, error handling, dependencies, security, UX, scope and documentation. Return PASS/FAIL/WARNING. Release only with no unresolved critical failures. Do not add features. Stop.
```

### Exit gate

-   Scope is limited to this phase.
-   Relevant tests pass.
-   No unrelated files/features are changed.
-   ChatGPT review is completed before the next major phase.

------------------------------------------------------------------------

# 9. Final Quality Gates

The final system must satisfy three types of confidence:

1.  **Mathematical confidence** --- formulas produce correct numbers.
2.  **Integration confidence** --- correct values travel through every
    module.
3.  **Business confidence** --- recommendations make sense.

All three are required.

## Final architecture check

``` text
CSV
 ↓
Validation
 ↓
Processing
 ↓
Analysis
 ↓
Risk / Health
 ↓
Recommendation
 ↓
Dashboard
```

Gemini is an enhancement:

``` text
Verified outputs
 ↓
Gemini
 ↓
Explanation
```

If Gemini is unavailable, InventoryIQ's deterministic calculations and
recommendations must still work.

## Final release gate

``` text
□ Data contract verified
□ Validation verified
□ Processing verified
□ Mathematics verified
□ Risk verified
□ Recommendations verified
□ Scenarios verified
□ Backend/frontend contracts verified
□ Dashboard verified
□ Product Explorer verified
□ Product Deep Dive verified
□ Category Analysis verified
□ Historical Analysis verified
□ Gemini verified
□ Gemini failure path verified
□ Data-quality audit passed
□ UX audit passed
□ Scope audit passed
□ Security/Git audit passed
□ Full regression passed
□ No unresolved critical failures
```

# 10. The One Rule to Remember

> **Build in parallel, but integrate through contracts. Build one phase
> at a time, test it, have ChatGPT review it, then commit.**

InventoryIQ V2 remains:

**Python = truth → analysis/risk = interpretation → recommendation.py =
decision → UI = presentation → Gemini = explanation.**
