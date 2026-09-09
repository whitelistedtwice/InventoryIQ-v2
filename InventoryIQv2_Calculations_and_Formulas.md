# InventoryIQ V2 — Calculations & Formulas
## Mathematical Methodology + Self-Study Reference

> **Purpose:** This document explains **how InventoryIQ V2 calculates things** and why each calculation exists.
>
> **Companion:** `InventoryIQv2.md` defines **what the product is**. This document defines the mathematical methodology behind it.
>
> **Important:** Some implementation thresholds and risk-score weights are intentionally provisional until validated with synthetic scenarios.

---

## Table of Contents

1. [How to Read This Document](#1-how-to-read-this-document)
2. [Core Notation](#2-core-notation)
3. [Data Definitions & Preconditions](#3-data-definitions--preconditions)
4. [Derived Business Variables](#4-derived-business-variables)
5. [Demand Statistics](#5-demand-statistics)
6. [Demand Trend](#6-demand-trend)
7. [Outlier Detection](#7-outlier-detection)
8. [Seasonality & Demand Patterns](#8-seasonality--demand-patterns)
9. [Inventory Planning Calculations](#9-inventory-planning-calculations)
10. [Safety Stock & Reorder Point](#10-safety-stock--reorder-point)
11. [Stockout Probability](#11-stockout-probability)
12. [Reorder Quantity](#12-reorder-quantity)
13. [Excess Inventory](#13-excess-inventory)
14. [Financial Calculations](#14-financial-calculations)
15. [Revenue & Profit at Risk](#15-revenue--profit-at-risk)
16. [Product Risk Score](#16-product-risk-score)
17. [Category Risk & Overall Health](#17-category-risk--overall-health)
18. [Recommendation Logic](#18-recommendation-logic)
19. [What-If Scenario Calculations](#19-what-if-scenario-calculations)
20. [Historical Analysis](#20-historical-analysis)
21. [Data Sufficiency & Edge Cases](#21-data-sufficiency--edge-cases)
22. [Worked End-to-End Example](#22-worked-end-to-end-example)
23. [Methodology Boundaries](#23-methodology-boundaries)
24. [Formula Cheat Sheet](#24-formula-cheat-sheet)

---

# 1. How to Read This Document

InventoryIQ follows one central idea:

```text
Raw observations
      ↓
Clean / validate
      ↓
Calculate verified metrics
      ↓
Interpret risk
      ↓
Recommend an action
      ↓
Explain the result
```

There are three important layers:

| Layer | Responsibility |
|---|---|
| **Calculation** | Produce mathematically defined values |
| **Decision** | Turn those values into risk/recommendation |
| **Explanation** | Explain the verified result to the user |

Gemini belongs to the explanation layer. It is **not** the source of truth for any formula in this document.

---

# 2. Core Notation

| Symbol | Meaning |
|---|---|
| \(x_i\) | Demand observed on day \(i\) |
| \(n\) | Number of observations |
| \(\mu\) | Mean daily demand |
| \(s\) | Sample standard deviation of daily demand |
| \(s^2\) | Sample variance |
| \(CV\) | Coefficient of variation |
| \(t\) | Time index, normally \(0,1,\ldots,n-1\) |
| \(a\) | Regression intercept |
| \(b\) | Regression slope |
| \(L\) | Supplier lead time in days |
| \(I\) | Current/end-of-day inventory |
| \(z\) | Standard-normal critical value for the chosen service level |
| \(SS\) | Safety stock |
| \(ROP\) | Reorder point |
| \(H\) | Excess-inventory planning horizon |
| \(P\) | Selling price per unit |
| \(C\) | Unit cost |
| \(\Phi\) | Standard normal cumulative distribution function |

### Unit discipline

InventoryIQ should keep units consistent.

For example:

```text
Demand       → units/day
Lead time    → days
Lead-time demand → units
Safety stock → units
Inventory    → units
Revenue      → currency
Profit       → currency
```

A formula should not combine quantities with incompatible units.

---

# 3. Data Definitions & Preconditions

The canonical V2 input schema is:

```csv
date,product,category,inventory,units_sold,unit_cost,selling_price,supplier,lead_time_days
```

## 3.1 Inventory

`inventory` means:

> **End-of-day inventory level for that product on that date.**

This definition is critical.

It means inventory is a **stock level**, not a flow.

Therefore:

```text
Inventory ≠ units sold
Inventory change ≠ demand
```

## 3.2 Units sold

`units_sold` represents the demand observed during that day.

For core demand analysis, this is the demand variable.

## 3.3 Lead time

`lead_time_days` is treated as a fixed supplier lead time.

V2 does **not** have enough information to estimate historical lead-time variability.

## 3.4 Required validity

Before calculating inventory metrics, the system should verify:

- valid dates
- non-negative demand where appropriate
- non-negative inventory
- positive unit cost where required
- valid selling price
- valid positive lead time
- sufficient observations for the requested statistic

Invalid or ambiguous records should not silently become valid-looking data.

---

# 4. Derived Business Variables

These are deterministic calculations created from the input data.

## 4.1 Daily revenue

### Formula

\[
Revenue_i = UnitsSold_i \times SellingPrice_i
\]

### Meaning

How much sales revenue was generated from the units sold that day.

### Example

```text
20 units sold
× $10 selling price
= $200 revenue
```

---

## 4.2 Daily COGS

COGS = Cost of Goods Sold.

### Formula

\[
COGS_i = UnitsSold_i \times UnitCost_i
\]

### Example

```text
20 units sold
× $6 unit cost
= $120 COGS
```

---

## 4.3 Daily gross profit

### Formula

\[
GrossProfit_i = Revenue_i - COGS_i
\]

Equivalent:

\[
GrossProfit_i =
UnitsSold_i \times (SellingPrice_i-UnitCost_i)
\]

### Example

```text
Revenue = $200
COGS    = $120

Gross profit = $80
```

---

## 4.4 Profit per unit

\[
ProfitPerUnit = SellingPrice - UnitCost
\]

Example:

```text
$10 − $6 = $4/unit
```

---

## 4.5 Gross margin

\[
GrossMargin =
\frac{GrossProfit}{Revenue}
\]

Only calculate this when:

\[
Revenue > 0
\]

Example:

```text
Gross profit = $80
Revenue     = $200

Margin = 80 / 200 = 0.40 = 40%
```

---

## 4.6 Inventory value

\[
InventoryValue = Inventory \times UnitCost
\]

Example:

```text
100 units × $6
= $600 inventory value
```

This represents the approximate cost value of stock currently held.

---

## 4.7 Inventory change

If opening inventory is available:

\[
InventoryChange_i =
EndingInventory_i - OpeningInventory_i
\]

Example:

```text
Opening inventory = 20
Ending inventory  = 60

Inventory change = +40
```

This is **not demand**.

For example:

```text
20 opening
− 10 sold
+ 50 received
= 60 ending

Inventory change = +40
Demand = 10
```

Using inventory change as demand would produce the wrong answer.

---

## 4.8 Sales velocity

For V2, sales velocity is represented by historical average demand:

\[
SalesVelocity = \mu
\]

Unit:

```text
units/day
```

This is deliberately transparent rather than a separate forecasting model.

---

# 5. Demand Statistics

Let daily demand observations be:

\[
x_1,x_2,\ldots,x_n
\]

---

## 5.1 Mean

### Formula

\[
\mu =
\frac{1}{n}
\sum_{i=1}^{n}x_i
\]

### Meaning

Average units sold per day.

### Example

Demand:

```text
8, 10, 12
```

\[
\mu = \frac{8+10+12}{3}=10
\]

So:

> Average demand = **10 units/day**

### Why InventoryIQ uses it

The mean provides the baseline demand rate for:

- lead-time demand
- days of inventory remaining
- safety-stock methodology
- reorder point
- excess-inventory target

---

## 5.2 Median

The median is the middle value after sorting the observations.

Example:

```text
3, 5, 8, 10, 20
```

Median:

```text
8
```

For an even number of observations, the median is the average of the two middle values.

### Why show it?

The median helps compare typical demand with the mean.

A large difference can indicate skew or unusually large observations.

---

## 5.3 Sample standard deviation

InventoryIQ uses **sample standard deviation** for demand variability.

### Formula

\[
s =
\sqrt{
\frac{
\sum_{i=1}^{n}(x_i-\mu)^2
}{
n-1
}
}
\]

### Why \(n-1\)?

The sample SD is used because the observed historical days are treated as a sample of the broader demand process.

### Example

Demand:

```text
8, 10, 12
```

Mean:

\[
\mu=10
\]

Squared deviations:

```text
(8−10)²  = 4
(10−10)² = 0
(12−10)² = 4
```

Sum:

\[
8
\]

Sample variance:

\[
s^2=\frac{8}{3-1}=4
\]

Therefore:

\[
s=2
\]

---

## 5.4 Variance

### Formula

\[
s^2 =
\frac{
\sum_{i=1}^{n}(x_i-\mu)^2
}{
n-1
}
\]

Variance is simply the square of sample SD:

\[
Variance = SD^2
\]

### Interpretation

Variance measures the spread of demand in squared units.

Because squared units are less intuitive, SD is usually easier to interpret on the dashboard.

---

## 5.5 Coefficient of variation

### Formula

\[
CV=\frac{s}{\mu}
\]

when:

\[
\mu>0
\]

Often displayed as a percentage:

\[
CV_{\%}=100\times\frac{s}{\mu}
\]

### Example

```text
Mean = 10
SD   = 2

CV = 2/10 = 0.20 = 20%
```

### Interpretation

CV measures variability relative to the average.

A higher CV means demand is more variable relative to its typical level.

### Edge case

If:

\[
\mu=0
\]

CV is undefined.

InventoryIQ should display something like:

> CV unavailable — average demand is zero.

It should not divide by zero or invent a value.

---

# 6. Demand Trend

InventoryIQ uses linear regression to estimate whether demand is moving upward or downward over time.

## 6.1 Regression model

\[
Demand_t = a+bt
\]

where:

- \(t\) = time index
- \(a\) = intercept
- \(b\) = slope

### Interpretation of \(b\)

- \(b>0\) → demand tends upward
- \(b<0\) → demand tends downward
- \(b\approx0\) → little linear movement

The slope is measured in approximately:

```text
units/day per observation
```

---

## 6.2 Normalized trend strength

A raw slope is difficult to compare across products.

InventoryIQ therefore normalizes the slope:

\[
TrendStrength =
\frac{b(n-1)}{\mu}
\]

when:

\[
\mu>0
\]

### Interpretation

This approximates the trend's total change across the observed period relative to average demand.

Example:

```text
Mean demand = 10
Slope       = 0.5 units/day
n           = 21 days
```

\[
TrendStrength =
\frac{0.5(20)}{10}
=1.0
\]

That corresponds to an estimated 100% change in fitted demand across the observation span relative to mean demand.

### Initial classification

The initial rule is:

```text
TrendStrength > +0.10 → Increasing
TrendStrength < -0.10 → Decreasing
Otherwise             → Stable
```

These thresholds are implementation parameters and should be validated with synthetic examples.

### Important limitation

Trend classification is not proof of a future trend.

It describes the historical pattern observed in the dataset.

---

# 7. Outlier Detection

InventoryIQ's primary outlier method is the **Interquartile Range (IQR)**.

## 7.1 Quartiles

- \(Q_1\) = first quartile
- \(Q_3\) = third quartile

## 7.2 IQR

\[
IQR=Q_3-Q_1
\]

## 7.3 Lower and upper fences

\[
LowerFence=Q_1-1.5(IQR)
\]

\[
UpperFence=Q_3+1.5(IQR)
\]

Any observation outside those fences is flagged as an outlier.

### Example

Suppose:

```text
Q1 = 5
Q3 = 11
```

Then:

\[
IQR=11-5=6
\]

Lower fence:

\[
5-1.5(6)=-4
\]

Upper fence:

\[
11+1.5(6)=20
\]

A demand value of 25 is flagged.

---

## 7.4 Outliers are not deleted

An outlier could be:

- a promotion
- a holiday
- an actual demand spike
- an actual demand collapse
- a data-entry problem

Therefore:

> **Detection ≠ deletion**

The original observation remains available.

---

## 7.5 Robust fallback: MAD

A median-based robust measure may be used when IQR is unsuitable.

Median absolute deviation:

\[
MAD =
median(|x_i-median(x)|)
\]

A standardized robust score can be formed as:

\[
RobustZ_i =
\frac{0.6745(x_i-median(x))}{MAD}
\]

A common extreme-value screening threshold is approximately:

\[
|RobustZ_i|>3.5
\]

### Implementation note

The exact condition for switching to MAD and its threshold should be validated on synthetic/intermittent-demand data before implementation is frozen.

---

# 8. Seasonality & Demand Patterns

Seasonality is deliberately handled conservatively.

## 8.1 Day-of-week factor

For weekday/day-of-week \(d\):

\[
DayFactor_d=
\frac{MeanDemand_d}{OverallMeanDemand}
\]

Example:

```text
Overall mean = 10 units/day
Saturday mean = 15 units/day
```

\[
DayFactor_{Sat}=15/10=1.5
\]

Interpretation:

> Saturdays averaged 50% more demand than the overall daily average.

### Minimum-history rule

The exact implementation threshold remains a parameter, but the system should require enough calendar coverage before claiming a weekday pattern. The design target is approximately **4+ weeks**.

---

## 8.2 Monthly factor

For month \(m\):

\[
MonthFactor_m=
\frac{MeanDemand_m}{OverallMeanDemand}
\]

Example:

```text
Overall mean = 10
July mean    = 13

Monthly factor = 1.3
```

### Annual seasonality rule

A short dataset should not be described as having reliable annual seasonality.

The design target is:

```text
~12+ months → annual monthly seasonality may be assessed
```

With shorter history, use language such as:

> Observed monthly pattern

rather than:

> Annual seasonality

### Important anti-double-counting rule

Trend and seasonality are **signals**, not separate quantities that are automatically added to the baseline demand in every core formula.

---

# 9. Inventory Planning Calculations

The core planning model uses a transparent baseline:

\[
BaselineDemand=\mu
\]

This is deliberate.

Trend, seasonality, volatility, and outliers are useful for **risk interpretation**, but blindly adding all of them to demand would double-count information.

---

## 9.1 Lead-time demand

For fixed lead time \(L\):

\[
LeadTimeDemand=\mu L
\]

### Example

```text
Average demand = 10 units/day
Lead time      = 7 days
```

\[
LeadTimeDemand=10\times7=70
\]

The business needs approximately 70 units to cover average demand during the seven-day lead time.

---

# 10. Safety Stock & Reorder Point

## 10.1 Demand variability during lead time

Assuming independent daily demand with fixed lead time:

\[
\sigma_{LT}=s\sqrt{L}
\]

where:

- \(s\) = daily demand SD
- \(L\) = lead time

### Why \(\sqrt L\)?

For independent daily demand, variances add:

\[
Variance_{LT}=s^2L
\]

Taking the square root:

\[
SD_{LT}=s\sqrt L
\]

---

## 10.2 Safety stock

### Formula

\[
SS=z\,s\sqrt L
\]

The default service level is **95%**.

For a one-sided 95% normal service level:

\[
z\approx1.645
\]

### Example

```text
SD = 3 units/day
Lead time = 7 days
z = 1.645
```

\[
SS=1.645(3)\sqrt7
\]

\[
SS\approx13.04
\]

So safety stock is approximately:

> **13 units**

Operational rounding should be defined consistently during implementation.

---

## 10.3 Reorder point

### Formula

\[
ROP=\mu L+SS
\]

Combining the formulas:

\[
ROP=\mu L+z\,s\sqrt L
\]

### Example

```text
Mean demand = 10
SD          = 3
Lead time   = 7
z           = 1.645
```

Lead-time demand:

\[
10(7)=70
\]

Safety stock:

\[
\approx13.04
\]

Therefore:

\[
ROP\approx83.04
\]

The system would operationally compare current inventory against an appropriately rounded/continuous threshold according to implementation rules.

---

## 10.4 Why ROP and safety stock are not the same

```text
Lead-time demand
      +
Safety stock
      =
Reorder point
```

Lead-time demand covers expected demand.

Safety stock protects against uncertainty.

ROP is therefore a **trigger**, not a maximum stock level.

---

# 11. Stockout Probability

InventoryIQ estimates the probability that demand during lead time exceeds current inventory.

## 11.1 Model assumption

Under the normal approximation:

\[
D_{LT}\sim N(\mu L,s^2L)
\]

Therefore:

\[
SD_{LT}=s\sqrt L
\]

---

## 11.2 Probability formula

Current inventory:

\[
I
\]

Stockout occurs if:

\[
D_{LT}>I
\]

Therefore:

\[
P(stockout)=
1-\Phi
\left(
\frac{I-\mu L}{s\sqrt L}
\right)
\]

### Example

Suppose:

```text
Mean demand = 10
SD          = 3
Lead time   = 7
Inventory   = 60
```

Mean lead-time demand:

\[
70
\]

Lead-time SD:

\[
3\sqrt7\approx7.94
\]

Standardized value:

\[
z_I=
\frac{60-70}{7.94}
\approx-1.26
\]

Therefore:

\[
P(stockout)
=
1-\Phi(-1.26)
\]

Approximately:

\[
P(stockout)\approx0.896
\]

or about:

> **89.6% estimated probability**

This is high because current inventory is well below expected lead-time demand.

---

## 11.3 Consistency check with ROP

At:

\[
I=ROP=\mu L+z\sigma_{LT}
\]

the standardized value becomes:

\[
\frac{ROP-\mu L}{\sigma_{LT}}=z
\]

Therefore:

\[
P(stockout)=1-\Phi(z)
\]

For a 95% service level:

\[
z\approx1.645
\]

and:

\[
1-\Phi(1.645)\approx0.05
\]

So:

> **At the model's 95% reorder point, estimated stockout probability is approximately 5%.**

This is an important internal consistency check.

---

## 11.4 Edge cases

### Zero SD

If:

\[
s=0
\]

the probability formula would divide by zero.

In this case demand is historically constant, so the system should use deterministic logic rather than forcing the normal-probability formula.

Conceptually:

```text
If inventory < lead-time demand:
    stockout exposure = 100% under constant-demand model
Else:
    stockout exposure = 0%
```

### Zero mean demand

If:

\[
\mu=0
\]

days remaining and CV are undefined/infinite-style quantities.

The system should avoid misleading percentages and report insufficient/zero-demand conditions explicitly.

### Small or non-normal datasets

The probability should remain labelled:

> **Estimated stockout probability**

and its assumptions should be visible in documentation/UI where appropriate.

---

# 12. Reorder Quantity

InventoryIQ does not implement EOQ.

## 12.1 Why not EOQ?

EOQ requires additional business inputs such as:

- ordering cost
- holding cost
- demand assumptions
- potentially other procurement constraints

Those inputs are not in the V2 schema.

Therefore an EOQ result would create false precision.

---

## 12.2 Target-restocking quantity

InventoryIQ uses:

\[
ReorderQuantity=
max(0,ROP-I)
\]

### Example

```text
ROP = 83
Current inventory = 40
```

\[
ReorderQuantity=max(0,83-40)=43
\]

So:

> Estimated reorder quantity = **43 units**

This means:

> "Approximately 43 units would bring current inventory back to the calculated reorder point."

It does **not** mean 43 is the optimal supplier order.

---

# 13. Excess Inventory

ROP cannot be used as the maximum target.

Instead, V2 uses a separate planning horizon.

## 13.1 Target stock

Let:

\[
H=30\text{ days}
\]

as the initial configurable planning horizon.

Then:

\[
TargetStock=\mu H+SS
\]

---

## 13.2 Excess units

\[
ExcessUnits=
max(0,I-TargetStock)
\]

### Example

```text
Mean demand = 10/day
H = 30 days
Safety stock = 13
Inventory = 350
```

Target:

\[
10(30)+13=313
\]

Excess:

\[
350-313=37
\]

Therefore:

> Estimated excess = **37 units**

---

## 13.3 Excess inventory value

\[
ExcessValue=ExcessUnits\times UnitCost
\]

If unit cost is $6:

\[
37\times6=\$222
\]

### Important interpretation

The 30-day horizon is a **planning assumption**.

It is not a universal definition of overstock.

---

# 14. Financial Calculations

## 14.1 Revenue

\[
Revenue=UnitsSold\times SellingPrice
\]

## 14.2 COGS

\[
COGS=UnitsSold\times UnitCost
\]

## 14.3 Gross profit

\[
GrossProfit=Revenue-COGS
\]

or:

\[
GrossProfit=UnitsSold(SellingPrice-UnitCost)
\]

## 14.4 Profit per unit

\[
ProfitPerUnit=SellingPrice-UnitCost
\]

## 14.5 Gross margin

\[
GrossMargin=
\frac{GrossProfit}{Revenue}
\]

when:

\[
Revenue>0
\]

## 14.6 Inventory value

\[
InventoryValue=Inventory\times UnitCost
\]

---

# 15. Revenue & Profit at Risk

These metrics describe **estimated shortage exposure**, not guaranteed lost sales.

## 15.1 Shortage units

The baseline lead-time shortage exposure is:

\[
ShortageUnits=
max(0,\mu L-I)
\]

### Example

```text
Lead-time demand = 70
Inventory = 40
```

\[
ShortageUnits=max(0,70-40)=30
\]

---

## 15.2 Revenue at risk

\[
RevenueAtRisk=
ShortageUnits\times SellingPrice
\]

If:

```text
30 shortage units
× $10 selling price
```

then:

\[
RevenueAtRisk=\$300
\]

---

## 15.3 Profit at risk

\[
ProfitAtRisk=
ShortageUnits(SellingPrice-UnitCost)
\]

If:

```text
Selling price = $10
Unit cost = $6
```

then:

\[
30(10-6)=\$120
\]

---

## 15.4 Why this is not guaranteed loss

The model assumes the estimated shortage would otherwise correspond to sellable demand.

Actual outcomes can differ because:

- demand may change
- customers may wait
- customers may substitute another product
- replenishment may arrive early
- sales may not equal forecast baseline

Therefore the dashboard should say:

> **Estimated revenue at risk**

rather than:

> "You will lose $300."

---

# 16. Product Risk Score

The product risk score combines existing signals into one 0–100 score.

## 16.1 Initial framework

| Component | Initial weight |
|---|---:|
| Stockout exposure | 30% |
| Demand volatility | 20% |
| Demand trend | 15% |
| Excess inventory | 15% |
| Financial exposure | 10% |
| Seasonality | 10% |
| **Total** | **100%** |

### Critical note

The **multi-factor framework is locked**.

The exact weights are **initial values**, not scientifically universal constants.

They must be validated with synthetic scenarios before implementation is considered final.

---

## 16.2 Why normalization is necessary

Raw values have incompatible scales.

For example:

```text
Stockout probability → 0–1
CV                  → potentially >1
Revenue exposure    → dollars
Trend strength      → relative change
```

They cannot simply be added.

Each component must therefore be transformed into a comparable risk contribution, typically on a common 0–100 scale.

---

## 16.3 Financial normalization

A $1000 exposure should not automatically make a product riskier than a $50 exposure.

The financial component should therefore be normalized **relative to the relevant product set**, such as with a percentile/rank-based transformation.

This avoids expensive products automatically dominating risk.

---

## 16.4 Trend risk direction

Trend is contextual.

For inventory risk:

```text
Increasing demand + low inventory
→ potentially higher risk

Decreasing demand + high inventory
→ potentially higher excess risk
```

Therefore trend should not simply mean:

```text
positive trend = risk
negative trend = safe
```

Its contribution depends on the inventory situation.

---

## 16.5 Risk levels

Initial display bands:

```text
0–39    LOW
40–69   MEDIUM
70–100  HIGH
```

These are presentation/decision thresholds and should be tested with synthetic products.

---

## 16.6 Synthetic validation scenarios

Before finalizing weights, test at least:

### Scenario A — Stockout emergency

```text
Low inventory
Long lead time
High stockout probability
```

Expected:

> High risk

### Scenario B — Overstock emergency

```text
Very high inventory
Low stockout risk
Declining demand
Large excess value
```

Expected:

> High/meaningful risk

### Scenario C — Expensive but healthy

```text
High unit cost
Healthy coverage
Low volatility
No excess
```

Expected:

> Not automatically high risk

### Scenario D — Cheap but chaotic

```text
Low unit cost
Extreme demand volatility
Potential stockout
```

Expected:

> Risk can still be high

### Scenario E — Growing product

```text
Increasing demand
Low inventory
Long lead time
```

Expected:

> Elevated risk

---

# 17. Category Risk & Overall Health

These are aggregate interpretations of existing product-level outputs.

## 17.1 Category risk

A category should summarize signals such as:

- product risk
- stockout exposure
- excess inventory
- demand volatility
- financial exposure
- number of high-risk products

The category methodology should reuse the product-level analysis rather than inventing an unrelated second risk model.

### Important design principle

A category with expensive products should not automatically appear dangerous solely because its inventory is worth more.

Category risk should therefore expose **both risk and magnitude**:

```text
Risk level / score
+
Financial magnitude
+
Number of affected products
```

This makes the interpretation more useful.

---

## 17.2 Overall inventory health

Overall health is a business-level summary of the existing risk outputs.

It should consider:

- proportion of products at risk
- stockout exposure
- excess inventory
- financial exposure
- recommendation priorities

The implementation should use the shared risk/health interpretation layer rather than inventing multiple competing definitions of "health."

Exact status thresholds should be calibrated against representative datasets.

---

# 18. Recommendation Logic

The recommendation engine does not calculate new core metrics.

It consumes verified metrics and decides an action.

## 18.1 Five actions

```text
REORDER
HOLD / PAUSE REORDERING
REDUCE EXCESS INVENTORY
MONITOR
NO ACTION
```

---

## 18.2 Multi-signal reasoning

A recommendation should consider multiple signals.

### Example: reorder

Signals may include:

```text
Inventory < ROP
+
low days remaining
+
elevated stockout probability
+
long lead time
+
increasing demand
```

The final recommendation contains evidence rather than a single unexplained threshold.

---

## 18.3 Example: reduce excess

```text
High excess units
+
high excess value
+
low stockout exposure
+
weak/declining demand
```

→

**REDUCE EXCESS INVENTORY**

---

## 18.4 Example: hold

A product can be above ideal stock without requiring immediate liquidation.

For example:

```text
Adequate coverage
+
low stockout probability
+
some excess
```

→

**HOLD / PAUSE REORDERING**

This means:

> Do not add more inventory right now.

It is distinct from:

> Actively reduce existing inventory.

---

## 18.5 Monitor

Used when the signals are meaningful but not severe enough for intervention.

Examples:

- rising volatility
- emerging trend
- moderate stockout exposure
- unusual recent demand

---

## 18.6 No action

Used when the product is broadly healthy and no intervention is justified.

---

# 19. What-If Scenario Calculations

Scenario analysis changes assumptions temporarily and reruns the same formulas.

## 19.1 Demand scenario

If baseline demand is:

\[
\mu=10
\]

and demand changes by:

\[
+20\%
\]

then:

\[
\mu_{scenario}
=
10(1+0.20)
=12
\]

For a decrease of 20%:

\[
\mu_{scenario}
=
10(1-0.20)
=8
\]

---

## 19.2 Lead-time scenario

If:

\[
L=7
\]

and lead time increases by 3 days:

\[
L_{scenario}=10
\]

The scenario must then recalculate:

- lead-time demand
- safety stock
- reorder point
- stockout probability
- reorder quantity
- shortage exposure
- relevant risk/recommendation outputs

---

## 19.3 Same engine, different assumptions

This is critical:

```text
Baseline
   ↓
same formulas
   ↓
baseline results

Scenario assumptions
   ↓
same formulas
   ↓
scenario results
```

Do not create separate scenario formulas.

---

## 19.4 Scenario does not mutate actual data

The original dataset remains unchanged.

Scenario values exist only for the scenario calculation.

---

# 20. Historical Analysis

Historical analysis visualizes actual observations.

It should not create a competing calculation source.

## Useful historical values

For a selected product:

- daily units sold
- daily inventory
- date
- detected outlier flags
- stockout flags
- safety-stock reference
- replenishment events where inferable

The purpose is to answer:

> **What actually happened?**

rather than:

> What does the model predict will happen?

---

# 21. Data Sufficiency & Edge Cases

This section is deliberately explicit because a mathematically correct formula can still produce a bad business result if applied to unsuitable data.

## 21.1 Mean

Needs at least one valid observation.

If there are no observations:

> Mean unavailable.

---

## 21.2 Sample SD / variance

Needs at least two valid observations.

With one observation:

> SD/variance unavailable.

Do not manufacture a zero SD merely because there is insufficient data.

---

## 21.3 CV

Requires:

\[
n\ge2
\]

and:

\[
\mu>0
\]

Otherwise:

> CV unavailable.

---

## 21.4 Trend

Trend requires multiple observations across time.

The exact minimum-history threshold should be selected during implementation/testing.

Very short histories should not be given confident trend labels.

---

## 21.5 Outliers

IQR needs enough observations to make quartiles meaningful.

For very small or degenerate datasets:

> Outlier analysis may be unavailable.

MAD may be used as a robust fallback where appropriate.

---

## 21.6 Seasonality

Do not claim patterns from tiny samples.

Design targets:

```text
~4+ weeks
→ weekday pattern

~12+ months
→ annual monthly seasonality
```

Shorter periods can still be displayed as observed patterns when clearly labelled.

---

## 21.7 Zero demand

If:

\[
\mu=0
\]

then:

```text
CV → undefined
Days remaining → undefined/infinite
```

The system should distinguish between:

```text
No observed demand
```

and:

```text
Missing data
```

These are not the same thing.

---

## 21.8 Zero demand with positive inventory

This is potentially important business information.

It can indicate:

- dead stock
- inactive product
- excess inventory
- discontinued product

It should not simply be treated as an ordinary zero.

---

## 21.9 Zero variance

If:

\[
s=0
\]

then demand is historically constant.

Safety stock from the variability formula becomes:

\[
SS=0
\]

under this model.

Stockout probability should use deterministic handling rather than dividing by zero.

---

## 21.10 Missing inventory

Missing inventory is **not** zero inventory.

Do not generate:

```text
missing → stockout
```

This would create false risk.

---

## 21.11 Missing dates

A missing calendar date is not automatically a zero-sales day.

It can only be treated as zero demand if the dataset is known to be a complete daily record and the missing date represents an unrecorded zero-sales day.

Missing inventory should not be filled with zero merely because a date is absent.

---

## 21.12 Duplicate product/date rows

Because inventory is an end-of-day level, duplicate product/date records can be ambiguous.

Example:

```text
Product A | Jan 5 | inventory 50
Product A | Jan 5 | inventory 80
```

Should inventory be:

```text
50?
80?
130?
```

There is no universally correct answer.

Therefore ambiguous duplicates should be rejected or explicitly resolved rather than blindly summed.

---

## 21.13 Negative inventory

Negative inventory may represent backorders or data errors, but V2's basic inventory interpretation assumes a physical inventory level.

Unless backorders are explicitly supported, negative values should be treated as invalid/flagged rather than silently accepted.

---

## 21.14 Invalid lead time

Lead time must be valid for replenishment calculations.

If:

```text
lead_time_days ≤ 0
```

or missing:

> Replenishment/stockout calculations unavailable.

---

## 21.15 Selling price below unit cost

This produces a negative gross margin/profit per unit.

That is not necessarily a mathematical error.

It may represent:

- a loss-making product
- promotional pricing
- incorrect data

The system should preserve the value and potentially flag it for business review.

---

# 22. Worked End-to-End Example

Consider Product A:

```text
Average daily demand = 10 units/day
Daily demand SD     = 3 units/day
Current inventory   = 40 units
Lead time           = 7 days
Unit cost           = $5
Selling price       = $10
Service level       = 95%
```

## Step 1 — Lead-time demand

\[
10\times7=70
\]

**Lead-time demand = 70 units**

---

## Step 2 — Safety stock

\[
SS=1.645(3)\sqrt7
\]

\[
SS\approx13.04
\]

**Safety stock ≈ 13 units**

---

## Step 3 — Reorder point

\[
ROP=70+13.04
\]

\[
ROP\approx83.04
\]

**ROP ≈ 83 units**

---

## Step 4 — Compare inventory

Current inventory:

```text
40 units
```

ROP:

```text
83 units
```

Inventory is below ROP.

---

## Step 5 — Days remaining

\[
DaysRemaining=\frac{40}{10}=4
\]

**Approximately 4 days of coverage.**

Lead time is:

```text
7 days
```

So current coverage is shorter than supplier lead time.

---

## Step 6 — Stockout probability

\[
P(stockout)=
1-\Phi
\left(
\frac{40-70}{3\sqrt7}
\right)
\]

\[
3\sqrt7\approx7.94
\]

\[
z_I\approx-3.78
\]

Therefore the estimated stockout probability is extremely high under the model.

---

## Step 7 — Estimated reorder quantity

\[
ReorderQuantity=
max(0,83.04-40)
\]

\[
\approx43.04
\]

**Estimated reorder quantity ≈ 43 units.**

---

## Step 8 — Shortage exposure

\[
ShortageUnits=
max(0,70-40)=30
\]

Revenue exposure:

\[
30\times10=\$300
\]

Profit exposure:

\[
30(10-5)=\$150
\]

These are estimated exposure values, not guaranteed losses.

---

## Step 9 — Likely recommendation

The product has:

```text
Low coverage
+
inventory below ROP
+
high stockout exposure
+
lead time longer than current coverage
```

A reasonable recommendation is:

> **REORDER**

with evidence attached.

---

# 23. Methodology Boundaries

InventoryIQ V2 is intentionally not a complete enterprise forecasting/procurement optimizer.

## We do NOT claim to provide:

### EOQ optimization

Missing ordering/holding cost inputs.

### Lead-time variability modeling

No historical delivery-time observations.

### Perfect demand forecasting

The baseline planning demand is historical average demand.

### Guaranteed stockout probability

The probability is model-based and depends on assumptions.

### Guaranteed financial loss

Revenue/profit at risk is an estimated exposure.

### Universal definition of excess

The initial 30-day horizon is a configurable business assumption.

### Statistically proven risk weights

The initial risk-score weights require synthetic validation.

---

# 24. Formula Cheat Sheet

## Demand

\[
\boxed{
\mu=\frac{1}{n}\sum x_i
}
\]

\[
\boxed{
s=
\sqrt{
\frac{\sum(x_i-\mu)^2}{n-1}
}
}
\]

\[
\boxed{
Variance=s^2
}
\]

\[
\boxed{
CV=\frac{s}{\mu}
}
\]

---

## Trend

\[
\boxed{
Demand_t=a+bt
}
\]

\[
\boxed{
TrendStrength=\frac{b(n-1)}{\mu}
}
\]

Initial classification:

```text
> +10% → Increasing
< -10% → Decreasing
else   → Stable
```

---

## Outliers

\[
\boxed{
IQR=Q_3-Q_1
}
\]

\[
\boxed{
LowerFence=Q_1-1.5IQR
}
\]

\[
\boxed{
UpperFence=Q_3+1.5IQR
}
\]

Robust fallback:

\[
\boxed{
MAD=median(|x_i-median(x)|)
}
\]

\[
\boxed{
RobustZ_i=
\frac{0.6745(x_i-median(x))}{MAD}
}
\]

---

## Patterns

\[
\boxed{
DayFactor_d=
\frac{MeanDemand_d}{OverallMeanDemand}
}
\]

\[
\boxed{
MonthFactor_m=
\frac{MeanDemand_m}{OverallMeanDemand}
}
\]

---

## Inventory planning

\[
\boxed{
LeadTimeDemand=\mu L
}
\]

\[
\boxed{
\sigma_{LT}=s\sqrt L
}
\]

\[
\boxed{
SS=z\,s\sqrt L
}
\]

\[
\boxed{
ROP=\mu L+SS
}
\]

\[
\boxed{
DaysRemaining=\frac{I}{\mu}
}
\]

---

## Stockout probability

\[
\boxed{
P(stockout)=
1-\Phi
\left(
\frac{I-\mu L}{s\sqrt L}
\right)
}
\]

At the reorder point:

\[
\boxed{
P(stockout\mid I=ROP)=1-\Phi(z)
}
\]

For 95% service level:

\[
\boxed{
P(stockout)\approx5\%
}
\]

under the model assumptions.

---

## Reorder

\[
\boxed{
ReorderQuantity=max(0,ROP-I)
}
\]

---

## Excess

\[
\boxed{
TargetStock=\mu H+SS
}
\]

with initial:

\[
H=30\text{ days}
\]

\[
\boxed{
ExcessUnits=max(0,I-TargetStock)
}
\]

\[
\boxed{
ExcessValue=ExcessUnits\times UnitCost
}
\]

---

## Financials

\[
\boxed{
Revenue=UnitsSold\times SellingPrice
}
\]

\[
\boxed{
COGS=UnitsSold\times UnitCost
}
\]

\[
\boxed{
GrossProfit=Revenue-COGS
}
\]

\[
\boxed{
ProfitPerUnit=SellingPrice-UnitCost
}
\]

\[
\boxed{
GrossMargin=\frac{GrossProfit}{Revenue}
}
\]

\[
\boxed{
InventoryValue=Inventory\times UnitCost
}
\]

---

## Financial exposure

\[
\boxed{
ShortageUnits=max(0,\mu L-I)
}
\]

\[
\boxed{
RevenueAtRisk=ShortageUnits\times SellingPrice
}
\]

\[
\boxed{
ProfitAtRisk=
ShortageUnits(SellingPrice-UnitCost)
}
\]

---

# Final Mental Model

The most important relationships to remember are:

```text
                 AVERAGE DEMAND
                       │
                       ▼
              Lead-time demand
                       │
                       ├──────────────┐
                       │              │
                       ▼              ▼
                 Demand SD       Current inventory
                       │              │
                       ▼              │
                  Safety stock         │
                       │              │
                       └──────┬───────┘
                              ▼
                        Reorder Point
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
           Stockout risk   Reorder      Excess
                           quantity     inventory
                 │            │            │
                 └────────────┼────────────┘
                              ▼
                         RISK SCORE
                              │
                              ▼
                       RECOMMENDATION
                              │
                              ▼
                            GEMINI
```

And remember the fundamental separation:

> **Demand tells us what the business consumes.**  
> **Inventory tells us what the business has.**  
> **Lead time tells us how long replenishment takes.**  
> **Variability tells us how uncertain demand is.**  
> **Safety stock protects against that uncertainty.**  
> **Risk combines the signals.**  
> **Recommendations turn risk into action.**  
> **Gemini explains the verified result.**

---

## Methodology Status

### Locked conceptually

- Historical-average baseline demand
- Sample SD / variance / CV
- OLS trend
- IQR outlier detection + robust fallback
- Conservative seasonality/pattern interpretation
- Fixed-lead-time safety stock
- Reorder point
- Estimated stockout probability
- Target-restocking reorder quantity
- 30-day initial excess horizon
- Financial calculations
- Estimated shortage exposure
- Multi-factor product risk
- Five recommendation types
- Same-engine scenario analysis
- Python as source of truth
- Gemini as explanation layer

### Still requires implementation validation

- Exact minimum-history thresholds
- Exact IQR/MAD fallback trigger
- Exact MAD threshold
- Final risk-score weights
- Exact risk-component normalization functions
- Exact category/overall-health aggregation thresholds
- Final recommendation precedence when signals conflict
- Operational rounding rules

These are **parameters of the methodology**, not new features.

