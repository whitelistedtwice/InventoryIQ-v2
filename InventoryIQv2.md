# InventoryIQ V2
## Product Specification & Single Source of Truth

> **Status:** Planning / Architecture Specification  
> **Version:** V2  
> **Document role:** Defines **WHAT InventoryIQ V2 is**.  
> **Implementation roadmap:** `InventoryIQV2_PromptPlan.md`  
> **Calculation reference:** `InventoryIQV2_Calculations_and_Formulas.md`

---

## 1. What is InventoryIQ?

**InventoryIQ V2** is a business inventory intelligence dashboard designed to help a business answer four questions quickly:

1. **What is happening with our inventory?**
2. **Which products need attention first?**
3. **Why are they a problem?**
4. **What should we do about it?**

Instead of only showing inventory numbers, InventoryIQ combines **daily demand, inventory levels, supplier lead time, product economics, and category information** to turn raw inventory data into:

**data → analysis → risk → recommendation → explanation**

The product is intended to feel like a lightweight **inventory decision-support system**, not just a collection of charts.

---

# 2. Product Goals

InventoryIQ V2 should achieve five core goals.

### Goal 1 — Understand inventory health

Give the user an immediate business-level view of whether inventory is healthy, risky, or inefficient.

### Goal 2 — Find the most important problems

Identify products with issues such as:

- potential stockouts
- insufficient inventory coverage
- excessive inventory
- declining demand
- high demand volatility
- financial exposure

The user should not have to inspect every product manually.

### Goal 3 — Explain why a problem exists

A risk score alone is not useful.

InventoryIQ should show the evidence behind a finding, such as:

> **High Risk — REORDER**  
> Inventory covers approximately 4 days of demand, while supplier lead time is 10 days.

### Goal 4 — Turn analysis into action

The system should produce clear recommendations:

- **REORDER**
- **HOLD / PAUSE REORDERING**
- **REDUCE EXCESS INVENTORY**
- **MONITOR**
- **NO ACTION**

### Goal 5 — Allow investigation and experimentation

Users should be able to:

- investigate individual products
- compare categories
- inspect historical behaviour
- test hypothetical demand/lead-time changes
- understand how those changes affect risk and recommendations

---

# 3. Core Product Philosophy

InventoryIQ follows a strict separation of responsibilities:

```text
┌──────────────────────┐
│       Python         │
│ Calculate the truth  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  Analysis / Risk     │
│ Interpret the facts  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Recommendation       │
│ Decide what to do    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│       Gemini         │
│ Explain the findings │
└──────────────────────┘
```

### Python is the source of truth

Python calculates all official metrics.

Gemini must **not** independently calculate or alter them.

### Recommendation logic is deterministic

Recommendations come from verified analysis outputs and explicit decision rules.

### Gemini is the storyteller

Gemini turns verified findings into concise business explanations.

It does **not**:

- invent metrics
- replace Python calculations
- override recommendations
- make unsupported claims

---

# 4. V2 Input Data

InventoryIQ V2 uses daily product-level data.

## Canonical input schema

```csv
date,product,category,inventory,units_sold,unit_cost,selling_price,supplier,lead_time_days
```

### Field definitions

| Field | Meaning |
|---|---|
| `date` | Date of the observation |
| `product` | Product identifier/name |
| `category` | Product category |
| `inventory` | **End-of-day inventory level** |
| `units_sold` | Units sold during that day |
| `unit_cost` | Cost per unit |
| `selling_price` | Selling price per unit |
| `supplier` | Supplier associated with the product |
| `lead_time_days` | Supplier lead time in days |

### Why these inputs?

| Input | Enables |
|---|---|
| Daily sales | Demand statistics, volatility, trends, seasonality, outliers |
| Daily inventory | Inventory coverage, depletion, stockout detection, inventory history |
| Supplier + lead time | Replenishment and lead-time risk |
| Cost + selling price | Revenue, profit, margin, inventory value, financial exposure |
| Category | Category-level risk and business comparison |

---

# 5. Data Pipeline

The complete processing flow is:

```text
                 RAW CSV
                    │
                    ▼
             ┌─────────────┐
             │ Validation  │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │  Cleaning   │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │ Date        │
             │ Handling    │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │ Daily Data  │
             │ Aggregation │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │  Derived    │
             │ Variables   │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │  Analysis   │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │ Risk &      │
             │ Health      │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │Recommendation│
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │ Dashboard   │
             └──────┬──────┘
                    ▼
                  Gemini
```

## Processing responsibilities

### Validation

Checks that the dataset:

- contains required columns
- has valid data types
- has valid dates
- has valid numeric values
- does not contain ambiguous duplicate product/date records
- satisfies required data assumptions

Invalid or ambiguous data should be surfaced rather than silently turned into misleading numbers.

### Cleaning

Handles safe data-quality operations such as:

- standardizing fields
- handling missing values where the meaning is known
- removing/handling invalid records according to explicit rules
- preserving legitimate zero sales

**Missing inventory must never automatically become zero inventory.**

### Date handling

Dates are converted into a consistent datetime representation.

Daily analysis must respect the actual calendar sequence.

Missing dates are not automatically treated as zero inventory.

For sales, missing calendar days may only be interpreted as zero sales when the dataset semantics establish that the dataset is a complete daily record.

### Daily aggregation

If the source contains multiple observations that can legitimately be combined, they are aggregated according to explicit semantics.

Because `inventory` represents an **end-of-day level**, ambiguous duplicate product/date inventory records should be rejected or explicitly resolved rather than blindly summed.

### Derived variables

The processing layer may derive:

- daily revenue
- daily gross profit
- inventory value
- inventory change
- sales velocity
- gross profit margin

**Inventory change is not demand.**

For example:

```text
Opening inventory: 20
Units sold:       10
New stock received: 50
Ending inventory:  60

Inventory change = +40
Demand = 10
```

Therefore inventory change must never be substituted for units sold in demand calculations.

---

# 6. Analysis Engine

InventoryIQ V2 contains the following locked analytical groups.

---

## 6.1 Demand Statistics

For each product, InventoryIQ calculates:

- mean demand
- median demand
- standard deviation
- variance
- coefficient of variation (CV)
- minimum demand
- maximum demand
- demand volatility classification

These describe the product's historical demand behaviour.

The mean tells us **how much demand exists**.

The variability measures tell us **how predictable that demand is**.

---

## 6.2 Demand Trend Analysis

InventoryIQ measures whether demand is:

- increasing
- stable
- decreasing

The trend is quantified using a linear regression over time.

Trend is used as a **behavioural risk signal**, not blindly inserted into every inventory formula.

---

## 6.3 Demand Outlier Detection

Unusually high or low sales observations are detected.

Primary method:

**IQR-based outlier detection**

A robust fallback is used when the IQR method is unsuitable, particularly for degenerate or highly intermittent demand.

### Important rule

Outliers are **flagged, not automatically deleted**.

An unusual sales day could represent:

- a promotion
- a special event
- a genuine demand spike
- a data-entry error

The system should preserve the observation and allow the user to understand it.

---

## 6.4 Replenishment, Safety Stock & Stockout Risk

This is one of the most important analytical groups.

InventoryIQ calculates:

- average daily demand
- lead-time demand
- demand variability during lead time
- safety stock
- reorder point
- days of inventory remaining
- estimated stockout probability during lead time
- shortage exposure
- estimated reorder quantity

### Core methodology

For fixed lead time:

```text
Lead-time demand
= average daily demand × lead time
```

Safety stock:

```text
Safety stock
= z × daily demand SD × √lead time
```

Reorder point:

```text
ROP
= lead-time demand + safety stock
```

The system uses a **95% service-level default**, while allowing the service level to be configured.

### Stockout probability

InventoryIQ estimates the probability that demand during the supplier lead time exceeds available inventory.

This is explicitly presented as:

> **Estimated stockout probability during lead time**

It is a model-based estimate, not a guarantee.

The calculation assumes approximately normal and independent demand behaviour. Intermittent, highly skewed, promotional, or otherwise unusual demand can reduce the reliability of this estimate.

### Important consistency check

If inventory is exactly equal to the calculated reorder point, the estimated stockout probability corresponds to the complement of the selected service level under the model assumptions.

This keeps the safety-stock and stockout-risk calculations mathematically connected.

### Reorder quantity

InventoryIQ does **not** calculate EOQ.

EOQ would require information such as ordering and holding costs that are not provided by the V2 input schema.

Instead:

```text
Estimated reorder quantity
= max(0, reorder point − current inventory)
```

This is a **target-restocking estimate**, not procurement optimization.

---

## 6.5 Excess Inventory & Capital Risk

InventoryIQ identifies products carrying more inventory than the selected planning target.

The target uses:

```text
Target stock
= demand × planning horizon + safety stock
```

The initial planning horizon is **30 days**.

Therefore:

```text
Excess units
= max(0, current inventory − target stock)
```

and:

```text
Excess inventory value
= excess units × unit cost
```

### Important distinction

**Reorder Point is not the maximum inventory target.**

ROP tells the business when inventory is becoming low enough to trigger replenishment.

The excess-inventory calculation therefore uses a separate planning horizon.

The 30-day horizon is a configurable planning assumption, not a universal business rule.

---

## 6.6 Demand Seasonality & Patterns

InventoryIQ investigates recurring demand patterns.

### Shorter history

With sufficient history, the system can examine:

- weekday vs weekend behaviour
- observed day-of-week demand factors

### Longer history

Annual monthly seasonality should only be described when sufficient historical coverage exists.

The system should distinguish between:

> **Observed monthly pattern**

and:

> **Annual seasonality**

rather than making strong seasonality claims from a short dataset.

Seasonality helps explain demand changes and provides additional context for risk and recommendations.

It is **not independently added to the core reorder formula**, preventing double-counting of demand signals.

---

## 6.7 Profitability & Revenue Risk

InventoryIQ calculates:

- daily revenue
- cost of goods sold
- gross profit
- profit per unit
- gross margin
- inventory value
- revenue exposure
- profit exposure
- capital tied up

Potential shortage exposure during lead time is estimated from the gap between lead-time demand and available inventory.

These are presented as:

> **Estimated revenue at risk**

and:

> **Estimated profit at risk**

They are **exposure estimates**, not claims that the business will definitely lose that amount.

---

# 7. Product Risk & Explorer

Every product receives a **0–100 risk score**.

The score combines multiple existing signals rather than relying on one metric.

The initial framework considers:

| Risk component | Initial weight |
|---|---:|
| Stockout exposure | 30% |
| Demand volatility | 20% |
| Demand trend | 15% |
| Excess inventory | 15% |
| Financial exposure | 10% |
| Seasonality | 10% |

### Important status of the weights

The **framework is locked**, but these exact weights are initial values.

They must be validated against synthetic test scenarios before being considered final.

The score must behave sensibly in scenarios such as:

- high stockout risk + stable demand
- extreme excess + declining demand
- expensive but otherwise healthy product
- cheap product + extreme volatility
- growing demand + long supplier lead time

### Risk levels

Initial classification:

```text
0–39    LOW
40–69   MEDIUM
70–100  HIGH
```

### Financial normalization

Raw dollar value must not automatically make an expensive product high risk.

Financial exposure should therefore be normalized relatively rather than simply inserted as raw currency.

### Outliers

Outlier detection is primarily contextual.

It should not become a large independent risk-score component because the information may already be reflected through volatility and other risk signals.

---

# 8. Recommendation Engine

InventoryIQ turns analysis into five possible actions.

## 🔴 REORDER

Used when inventory coverage/replenishment signals indicate that stock should be replenished.

Includes:

- estimated reorder quantity
- priority
- reasons
- supporting evidence

## 🟠 HOLD / PAUSE REORDERING

Used when the business should avoid adding new stock despite a potentially non-ideal inventory situation.

Typical evidence:

- adequate inventory coverage
- low stockout exposure
- weak/declining demand
- elevated inventory

This is distinct from actively reducing existing excess.

## 🟡 REDUCE EXCESS INVENTORY

Used when inventory is materially above the planning target and carrying excess creates meaningful business risk.

Evidence can include:

- excess units
- excess inventory value
- declining demand
- low stockout exposure

## 🟢 MONITOR

Used when a product is not currently severe enough to require intervention but has signals worth watching.

Examples:

- increasing volatility
- emerging demand trend
- moderate stockout exposure
- unusual recent demand

## 🟢 NO ACTION

Used when the product is in a healthy state and no intervention is currently justified.

### Recommendation design principle

Recommendations must consider **multiple signals together**.

The system must not rely on simplistic single-metric logic when signals conflict.

Every recommendation should contain structured evidence:

```text
action
priority
reasons
supporting metrics
```

---

# 9. Internal Risk & Health Aggregation

InventoryIQ uses a shared internal interpretation layer to keep risk logic consistent.

It supports:

- product risk score
- overall inventory health
- category risk
- recommendation priority
- Gemini context

This is an **architecture layer, not a new dashboard feature**.

It does not need to become a separate `risk.py` file unless implementation complexity justifies splitting it.

The goal is to prevent the same metric from being interpreted differently in different parts of the application.

---

# 10. Category-Level Risk Analysis

InventoryIQ aggregates product-level findings into category-level insights.

A category view can show:

- inventory value
- capital tied up
- stockout exposure
- demand volatility
- average/category risk
- number of high-risk products
- excess inventory

The category system should reuse the same underlying product analysis rather than creating a completely separate methodology.

The user can move from:

```text
Business
  ↓
Category
  ↓
Product
```

---

# 11. Historical Analysis

Historical analysis shows what actually happened over time.

It includes:

- daily sales over time
- inventory over time
- product selection
- category selection
- date-range filtering

Potential event markers include:

- stockout events
- unusual demand spikes
- replenishment events
- safety-stock breaches

Historical analysis is primarily a **visual exploration layer** and should use the same processed data and analysis engine rather than becoming a second source of truth.

---

# 12. What-If Scenario Analysis

The What-If system lets users ask:

> "What would happen if demand or supplier lead time changed?"

### Example

```text
Average demand = 10 units/day
Demand scenario = +20%

Scenario demand = 12 units/day
```

The scenario is passed through the same analysis engine.

### Scenario flow

```text
Baseline data
     │
     ├───────────────┐
     │               │
     ▼               ▼
Baseline analysis   Scenario assumptions
                         │
                         ▼
                  Scenario analysis
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Baseline results      Scenario results
              │                     │
              └──────────┬──────────┘
                         ▼
                  Compare results
```

### Example propagation

```text
Demand ↑
  ↓
Days remaining ↓
  ↓
Stockout risk ↑
  ↓
Safety-stock requirement changes
  ↓
Reorder quantity ↑
  ↓
Potential financial exposure changes
```

### Rules

- Actual data must never be mutated.
- Scenarios are temporary assumptions.
- Baseline results remain unchanged.
- Scenario analysis must reuse the same calculation engine.
- A clear **Reset Scenario** action must exist.

Demand change and lead-time change are core controls. Additional controls should only be added if they provide meaningful decision value without unnecessary scope expansion.

---

# 13. Executive Business Health & Impact Summary

The dashboard needs a high-level answer before the user starts exploring individual products.

The executive layer summarizes:

- overall inventory health
- number of products at risk
- stockout exposure
- excess inventory
- capital tied up
- revenue/profit exposure
- highest-priority actions

The system should answer:

> **"What should I care about right now?"**

rather than simply displaying statistics.

---

# 14. Gemini AI Layer

Gemini has two primary responsibilities.

## 14.1 Executive Business Brief

Gemini receives verified aggregate findings and recommendations.

It produces a concise business brief containing approximately **3–5 key points**.

Possible structure:

```text
AI BUSINESS BRIEF

Status: Inventory requires attention

• Biggest problem
• Financial impact
• Demand situation
• Main risk
• Priority action
```

Python determines the underlying status and numbers.

Gemini explains and prioritizes the findings.

## 14.2 Product Deep-Dive Explanation

Gemini can be called for a selected product.

The product context can include:

- demand behaviour
- trend
- volatility
- inventory position
- stockout exposure
- excess inventory
- financial exposure
- risk score
- recommendation
- recommendation evidence

Gemini explains:

> Why is this product risky?

> What is causing the risk?

> What should the business pay attention to?

This is **on-demand**, rather than automatically generating AI text for every product.

### Gemini input rule

Gemini should receive:

```text
verified analysis outputs
+
structured recommendation
+
relevant business context
```

It should **not need the raw CSV** for normal explanation tasks.

---

# 15. Dashboard Experience

The dashboard follows this user journey:

```text
HEALTH
  ↓
PRIORITIES
  ↓
AI BRIEF
  ↓
PRODUCT / CATEGORY EXPLORATION
  ↓
HISTORICAL ANALYSIS
  ↓
WHAT-IF ANALYSIS
```

## 15.1 Global Controls

At the top:

- date range
- category selector
- product selector/search

These controls should consistently affect relevant dashboard content.

## 15.2 Inventory Health

High-level KPI cards:

```text
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Overall Health │ │ Products Risk  │ │ Stockout       │
│    HEALTHY     │ │       8        │ │ Exposure       │
└────────────────┘ └────────────────┘ └────────────────┘

┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Excess         │ │ Capital        │ │ Revenue /      │
│ Inventory      │ │ Tied Up        │ │ Profit Risk    │
└────────────────┘ └────────────────┘ └────────────────┘
```

Exact visual design is flexible. The user should understand the business state immediately.

## 15.3 Top Priorities

A ranked list/card layout:

```text
#1  🔴 REORDER
    Product A
    High Priority
    3 days coverage vs 10 day lead time

#2  🟡 REDUCE EXCESS
    Product B
    Medium Priority
    240 excess units

#3  🟢 MONITOR
    Product C
    Medium Priority
    Demand volatility increasing
```

The **reason** for each action should be visible.

## 15.4 Product Explorer

Interactive table:

| Product | Risk | Main Issue |
|---|---:|---|
| Product A | 86 | Stockout |
| Product B | 74 | Excess |
| Product C | 52 | Volatility |
| Product D | 18 | Healthy |

Users should be able to:

- sort by risk
- filter by risk level
- filter by category
- filter by stockout risk
- filter by excess inventory
- click a product to open its deep dive

The explorer should show the **whole product list**, not force users through a single dropdown.

---

# 16. Product Deep Dive

Selecting a product opens a detailed investigation view.

Suggested structure:

```text
PRODUCT: Product A
Risk Score: 86  |  HIGH

────────────────────────────────────

DEMAND
[Mean] [Median] [SD] [CV]

Trend: ↗ Increasing
Volatility: HIGH

        Demand over time
        ────────────────╱

Outliers
        •    •
       ╱ ╲  ╱ ╲
──────╱──╲─╱──╲────────

SEASONAL PATTERN
[weekday / monthly pattern]

────────────────────────────────────

INVENTORY

Current Inventory: 42
Days Remaining: 4.2
Safety Stock: 35
Reorder Point: 115

        Inventory over time
        ╲
         ╲____
              ╲___

────────────────────────────────────

STOCKOUT RISK

Estimated probability:
             78%

────────────────────────────────────

FINANCIALS

[Revenue] [Gross Profit] [Margin]
[Inventory Value] [Revenue Risk] [Profit Risk]

────────────────────────────────────

RECOMMENDATION

🔴 REORDER
Estimated quantity: 73 units

Reasons:
• Inventory below reorder point
• Lead time exceeds current coverage
• Elevated stockout exposure

[ Ask Gemini ]
```

The exact UI is flexible. The information hierarchy is the important part.

---

# 17. Category Analysis

Category-level view should allow the user to identify which parts of the business are causing the most inventory problems.

Possible presentation:

```text
CATEGORY HEALTH

Category       Risk      Stockout      Excess
──────────────────────────────────────────────
Electronics    HIGH      $12,400       $3,200
Food           LOW       $1,200        $800
Clothing       MEDIUM    $4,100        $7,900
```

A comparison chart can accompany the table.

The exact chart type is a frontend decision as long as it communicates the underlying metrics clearly.

---

# 18. Historical Visualization

Historical analysis should visually answer:

> "What actually happened?"

Possible views:

### Sales over time

```text
Units
  │       ╭─╮
  │   ╭───╯ ╰──╮
  │───╯        ╰────
  └────────────────── Date
```

### Inventory over time

```text
Units
  │╲
  │ ╲____
  │      ╲____
  │           ╲
  └────────────────── Date
```

### Optional combined Demand vs Inventory chart

```text
Units
  │  Demand ─────────╮
  │                  ╰──╮
  │ Inventory ───╮      ╰──
  │              ╰────
  └──────────────────────── Date
```

The combined interactive chart is currently **optional/on-hold** as part of the Advanced Visualization Layer.

---

# 19. Optional / On-Hold: Advanced Visualization Layer

This is deliberately **not a required core feature**.

The strongest candidate is an interactive **Demand vs Inventory** chart with:

- date on X-axis
- demand line
- inventory line
- safety-stock reference
- hover values
- zoom
- date range
- product selector
- stockout markers
- replenishment markers

Other possible visualizations:

- risk matrix
- demand heatmap
- inventory timeline
- category comparison
- risk distribution

These are presentation enhancements, not a second analysis engine. If time is limited, the core V2 remains complete without this layer.

---

# 20. Overall Architecture

Recommended project structure:

```text
InventoryIQ/
│
├── app.py
├── validation.py
├── data_processing.py
├── analysis.py
├── recommendation.py
├── scenario.py
├── gemini.py
│
├── data/
│   └── ...
│
├── tests/
│   └── ...
│
├── InventoryIQV2.md
├── InventoryIQV2_PromptPlan.md
└── InventoryIQV2_Calculations_and_Formulas.md
```

### `validation.py`

Schema validation and data-quality checks.

### `data_processing.py`

Date handling, aggregation, and derived variables.

### `analysis.py`

Demand statistics, trend, outliers, replenishment, safety stock, stockout probability, excess inventory, patterns, profitability, financial exposure, product risk, category analysis, and historical analysis.

### Risk & Health Aggregation

Can remain within `analysis.py` unless complexity justifies separation.

### `recommendation.py`

Recommendation types, priorities, reasons, and evidence.

### `scenario.py`

Temporary scenario assumptions and baseline/scenario comparison.

### `app.py`

Dashboard, filters, KPI presentation, priorities, explorer, category views, history, scenarios, and Gemini interface.

### `gemini.py`

Executive business brief and product deep-dive explanation.

---

# 21. Data Flow Contract

Modules communicate through **verified structured outputs**.

```text
CSV
 ↓
validation.py
 ↓
clean dataframe
 ↓
data_processing.py
 ↓
processed dataframe
 ↓
analysis.py
 ↓
verified analysis outputs
 ↓
risk/health aggregation
 ↓
recommendation.py
 ↓
structured recommendations
 ↓
app.py
 ↓
dashboard

verified outputs + recommendations
 ↓
gemini.py
 ↓
AI explanation
```

This separation allows the frontend to change without changing the underlying business logic.

---

# 22. Data Integrity Rules

InventoryIQ should prefer **honest uncertainty over fabricated precision**.

### Rule 1 — Missing ≠ zero

A missing inventory value is not automatically an out-of-stock event.

### Rule 2 — Outliers are not automatically errors

Flag them; do not silently delete them.

### Rule 3 — Do not double-count signals

Trend, volatility, seasonality, and outliers provide behavioural information. They should not all be independently inserted into every core inventory formula.

### Rule 4 — Do not invent unavailable information

The dataset does not provide historical supplier delivery times, ordering costs, holding costs, MOQ, or EOQ inputs. InventoryIQ should not pretend to optimize these quantities.

### Rule 5 — Clearly label estimates

Use language such as:

- Estimated stockout probability
- Estimated excess inventory
- Estimated reorder quantity
- Estimated revenue at risk
- Estimated profit at risk

### Rule 6 — Preserve one source of truth

A metric should be calculated once and reused throughout the application.

---

# 23. Methodology Assumptions & Limitations

### Demand model

Some calculations assume demand behaves approximately normally and independently, particularly the stockout-probability model.

This can be less reliable for:

- intermittent demand
- highly skewed demand
- promotions
- sudden structural changes
- very small datasets

### Lead time

Lead time is treated as fixed because historical delivery-time data is not provided.

### Reorder quantity

The recommended quantity is a target-restocking estimate, not EOQ or full procurement optimization.

### Excess inventory

The initial 30-day target horizon is a planning assumption and should be configurable.

### Seasonality

Seasonality claims require sufficient historical coverage.

### Risk score

The scoring framework is multi-factor, but its initial weights require scenario testing and calibration.

---

# 24. Insufficient Data Behaviour

InventoryIQ should not manufacture sophisticated-looking results from insufficient data.

Examples:

```text
Insufficient history
        ↓
Do not calculate / classify aggressively
        ↓
Show:
"Insufficient data"
```

Examples include:

- insufficient history for reliable trend
- insufficient history for seasonality
- zero/near-zero average demand
- zero variance
- missing inventory
- invalid lead time
- insufficient observations for a statistical calculation

Where possible, the dashboard should explain **why** a metric is unavailable.

---

# 25. What InventoryIQ Does NOT Do

To keep V2 focused, the following are intentionally outside scope:

- PDF/business report export
- authentication
- database infrastructure
- notification system
- supplier ordering integration
- EOQ optimization
- full procurement optimization
- historical lead-time modeling
- advanced forecasting models
- unnecessary AI-generated text everywhere
- unrelated dashboard pages
- separate duplicate analysis systems

The product should be **deep enough to be impressive, but narrow enough to remain reliable**.

---

# 26. Feature Map

| Feature Group | Main Question Answered |
|---|---|
| Input & Processing | Can we trust and prepare the data? |
| Demand Statistics | What does normal demand look like? |
| Demand Trend | Is demand changing? |
| Outlier Detection | What days look unusual? |
| Replenishment & Stockout | Will we have enough inventory? |
| Excess Inventory | Are we holding too much? |
| Seasonality & Patterns | When does demand change predictably? |
| Profitability & Risk | What is the financial impact? |
| Product Risk & Explorer | Which products matter most? |
| Category Risk | Which business areas matter most? |
| Historical Analysis | What actually happened? |
| What-If | What happens if conditions change? |
| Executive Health + Gemini | What should management care about? |

---

# 27. End-to-End Example

Imagine Product A has:

```text
Average demand:       10 units/day
Demand SD:             3 units/day
Inventory:            40 units
Lead time:            7 days
Unit cost:            $5
Selling price:        $10
```

InventoryIQ can reason through the system:

```text
10 units/day
     ↓
7-day lead-time demand
     ↓
Safety stock
     ↓
Reorder point
     ↓
Compare current inventory
     ↓
Estimate stockout probability
     ↓
Calculate target reorder quantity
     ↓
Combine with trend/volatility/excess signals
     ↓
Product risk score
     ↓
Recommendation
     ↓
Gemini explanation
```

The user ultimately sees something like:

> **HIGH RISK — REORDER**  
> Current inventory is below the replenishment threshold and does not provide enough coverage for the supplier lead time. Demand variability increases the uncertainty of the stock position.

Every statement should trace back to a verified calculation or structured recommendation.

---

# 28. Definition of Done

### Data

- [ ] Required CSV schema works
- [ ] Validation catches invalid data
- [ ] Cleaning is safe and explicit
- [ ] Date handling is reliable
- [ ] Derived variables are correct

### Analysis

- [ ] Demand statistics work
- [ ] Trend analysis works
- [ ] Outlier detection works
- [ ] Safety stock works
- [ ] Reorder point works
- [ ] Stockout probability works
- [ ] Days remaining works
- [ ] Reorder quantity works
- [ ] Excess inventory works
- [ ] Seasonality/pattern analysis handles insufficient data
- [ ] Financial calculations work
- [ ] Product risk works
- [ ] Category risk works
- [ ] Historical analysis works

### Recommendations

- [ ] Five recommendation types work
- [ ] Conflicting signals are handled
- [ ] Every recommendation includes evidence
- [ ] Priority is produced consistently

### Scenarios

- [ ] Scenario assumptions do not mutate real data
- [ ] Same analysis engine is reused
- [ ] Baseline vs scenario is clear
- [ ] Reset works

### Gemini

- [ ] Executive brief works
- [ ] Product deep dive works
- [ ] Gemini receives verified outputs
- [ ] Gemini cannot override Python results

### Dashboard

- [ ] Health is visible immediately
- [ ] Priorities are ranked
- [ ] Product explorer is interactive
- [ ] Category analysis works
- [ ] Product deep dive works
- [ ] Historical analysis works
- [ ] Scenario analysis works

### Quality

- [ ] Edge cases are tested
- [ ] Risk-score synthetic scenarios behave sensibly
- [ ] Calculations have unit tests
- [ ] No duplicated sources of truth
- [ ] No misleading labels
- [ ] UI remains understandable to a non-technical business user

---

# 29. Scope Lock

This document is the **single source of truth for what InventoryIQ V2 is**.

If an implementation idea conflicts with this document, the implementation idea should be reviewed rather than automatically added.

New features should only be added if they:

1. solve a genuine business problem,
2. do not duplicate an existing feature,
3. have a defensible methodology,
4. can be implemented reliably,
5. improve the product enough to justify their complexity.

The goal is not to maximize the number of features.

The goal is to build a system where:

> **Every important number has a reason to exist, every recommendation has evidence, and every AI explanation traces back to verified analysis.**

---

# 30. Reference Documents

### `InventoryIQV2.md`
This document — the **WHAT**.

### `InventoryIQV2_PromptPlan.md`
Implementation roadmap — the **HOW**.

### `InventoryIQV2_Calculations_and_Formulas.md`
Calculation and methodology reference — the **WHY/HOW mathematically**.

---

## Final Product Mental Model

If you remember only one thing about InventoryIQ V2:

```text
             RAW BUSINESS DATA
                    │
                    ▼
             ┌──────────────┐
             │   CLEAN IT   │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │  UNDERSTAND  │
             │    DEMAND    │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │  UNDERSTAND  │
             │   INVENTORY  │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │ CALCULATE    │
             │     RISK     │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │  RECOMMEND   │
             │    ACTION    │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │   EXPLAIN    │
             │   WITH AI    │
             └──────────────┘
```

**InventoryIQ V2 is not just an inventory dashboard.**

It is a transparent decision-support pipeline that turns daily operational data into **business priorities and actionable inventory decisions**.
