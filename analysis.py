"""Demand statistics for InventoryIQ V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass
class DemandStatistics:
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    variance: Optional[float] = None
    cv: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    volatility: Optional[str] = None
    observation_count: int = 0
    warnings: List[str] = field(default_factory=list)


def calculate_demand_statistics(series: pd.Series) -> DemandStatistics:
    clean = series.dropna()
    observation_count = int(clean.count())
    warnings: List[str] = []

    if observation_count == 0:
        warnings.append("No valid demand observations available.")
        return DemandStatistics(observation_count=0, warnings=warnings)

    values = clean.to_numpy(dtype=float)
    mean = float(np.mean(values))
    median = float(np.median(values))
    minimum = float(np.min(values))
    maximum = float(np.max(values))

    if observation_count < 2:
        warnings.append(
            "Insufficient observations for sample standard deviation."
        )
        return DemandStatistics(
            mean=mean,
            median=median,
            min=minimum,
            max=maximum,
            observation_count=observation_count,
            warnings=warnings,
        )

    variance = float(np.var(values, ddof=1))
    std_dev = float(np.sqrt(variance))

    if mean > 0:
        cv = std_dev / mean
    else:
        cv = None
        warnings.append("Average demand is zero; coefficient of variation is unavailable.")

    if std_dev == 0:
        volatility = "ZERO_VARIANCE"
    elif cv is not None and cv <= 0.25:
        volatility = "LOW"
    elif cv is not None and cv <= 0.75:
        volatility = "MEDIUM"
    else:
        volatility = "HIGH"

    return DemandStatistics(
        mean=mean,
        median=median,
        std_dev=std_dev,
        variance=variance,
        cv=cv,
        min=minimum,
        max=maximum,
        volatility=volatility,
        observation_count=observation_count,
        warnings=warnings,
    )


@dataclass
class TrendResult:
    slope: Optional[float] = None
    intercept: Optional[float] = None
    trend_strength: Optional[float] = None
    trend: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def calculate_trend(series: pd.Series) -> TrendResult:
    clean = series.dropna()
    n = int(clean.count())
    warnings: List[str] = []

    if n < 2:
        warnings.append("Insufficient observations for trend analysis.")
        return TrendResult(warnings=warnings)

    values = clean.to_numpy(dtype=float)
    t = np.arange(n, dtype=float)

    slope, intercept = np.polyfit(t, values, 1)

    mean = float(np.mean(values))
    if mean == 0:
        warnings.append("Mean demand is zero; trend strength is unavailable.")
        return TrendResult(
            slope=float(slope),
            intercept=float(intercept),
            warnings=warnings,
        )

    trend_strength = float(slope * (n - 1) / mean)

    if trend_strength > 0.10:
        trend = "INCREASING"
    elif trend_strength < -0.10:
        trend = "DECREASING"
    else:
        trend = "STABLE"

    return TrendResult(
        slope=float(slope),
        intercept=float(intercept),
        trend_strength=trend_strength,
        trend=trend,
        warnings=warnings,
    )


@dataclass
class OutlierResult:
    outlier_mask: Optional[pd.Series] = None
    lower_fence: Optional[float] = None
    upper_fence: Optional[float] = None
    method: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def detect_outliers(series: pd.Series) -> OutlierResult:
    clean = series.dropna()
    n = int(clean.count())
    warnings: List[str] = []

    if n < 2:
        warnings.append("No valid observations for outlier detection.")
        return OutlierResult(warnings=warnings)

    values = clean.to_numpy(dtype=float)
    q1 = float(np.percentile(values, 25))
    q3 = float(np.percentile(values, 75))
    iqr = q3 - q1

    lower_fence: Optional[float] = None
    upper_fence: Optional[float] = None
    use_mad = iqr == 0 or n < 5

    if use_mad:
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        if mad == 0:
            warnings.append(
                "Zero median absolute deviation; outlier detection unavailable."
            )
            return OutlierResult(warnings=warnings)

        robust_z = 0.6745 * (values - median) / mad
        outlier_flags = np.abs(robust_z) > 3.5
        method = "MAD"
    else:
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        outlier_flags = (values < lower_fence) | (values > upper_fence)
        method = "IQR"

    full_mask = pd.Series(False, index=series.index)
    clean_indices = series.dropna().index
    for i, idx in enumerate(clean_indices):
        full_mask[idx] = bool(outlier_flags[i])

    return OutlierResult(
        outlier_mask=full_mask,
        lower_fence=float(lower_fence) if lower_fence is not None else None,
        upper_fence=float(upper_fence) if upper_fence is not None else None,
        method=method,
        warnings=warnings,
    )


@dataclass
class InventoryPlanningResult:
    lead_time_demand: Optional[float] = None
    lead_time_sd: Optional[float] = None
    safety_stock: Optional[float] = None
    reorder_point: Optional[float] = None
    days_remaining: Optional[float] = None
    stockout_probability: Optional[float] = None
    reorder_quantity: Optional[float] = None
    service_level: float = 0.95
    z_score: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


def calculate_inventory_planning(
    mean_demand: float,
    std_dev: float,
    current_inventory: Optional[float],
    lead_time_days: Optional[float],
    service_level: float = 0.95,
) -> InventoryPlanningResult:
    from scipy.stats import norm

    warnings: List[str] = []

    if lead_time_days is None or np.isnan(lead_time_days) or lead_time_days <= 0:
        warnings.append("Invalid or unavailable lead time; replenishment calculations unavailable.")
        return InventoryPlanningResult(service_level=service_level, warnings=warnings)

    z_score = float(norm.ppf(service_level))
    lead_time_demand = mean_demand * float(lead_time_days)
    lead_time_sd = std_dev * float(np.sqrt(lead_time_days))
    safety_stock = z_score * lead_time_sd
    reorder_point = lead_time_demand + safety_stock

    if current_inventory is None or np.isnan(current_inventory):
        warnings.append("Missing current inventory; days remaining and reorder quantity unavailable.")
        return InventoryPlanningResult(
            lead_time_demand=lead_time_demand,
            lead_time_sd=lead_time_sd,
            safety_stock=safety_stock,
            reorder_point=reorder_point,
            service_level=service_level,
            z_score=z_score,
            warnings=warnings,
        )

    if mean_demand > 0:
        days_remaining = current_inventory / mean_demand
    else:
        days_remaining = None
        warnings.append("Zero mean demand; days remaining unavailable.")

    if lead_time_sd == 0:
        if current_inventory < lead_time_demand:
            stockout_probability = 1.0
        else:
            stockout_probability = 0.0
        warnings.append("Zero demand variability; deterministic stockout logic used.")
    else:
        z_value = (current_inventory - lead_time_demand) / lead_time_sd
        stockout_probability = float(1.0 - norm.cdf(z_value))

    reorder_quantity = max(0.0, reorder_point - current_inventory)

    return InventoryPlanningResult(
        lead_time_demand=lead_time_demand,
        lead_time_sd=lead_time_sd,
        safety_stock=safety_stock,
        reorder_point=reorder_point,
        days_remaining=days_remaining,
        stockout_probability=stockout_probability,
        reorder_quantity=reorder_quantity,
        service_level=service_level,
        z_score=z_score,
        warnings=warnings,
    )


@dataclass
class FinancialMetrics:
    daily_revenue: Optional[float] = None
    daily_cogs: Optional[float] = None
    daily_profit: Optional[float] = None
    profit_per_unit: Optional[float] = None
    gross_margin: Optional[float] = None
    inventory_value: Optional[float] = None
    capital_tied_up: Optional[float] = None
    shortage_units: Optional[float] = None
    revenue_at_risk: Optional[float] = None
    profit_at_risk: Optional[float] = None
    target_stock: Optional[float] = None
    excess_units: Optional[float] = None
    excess_inventory_value: Optional[float] = None
    planning_horizon: float = 30.0
    warnings: List[str] = field(default_factory=list)


def calculate_financial_and_excess_metrics(
    mean_demand: float,
    std_dev: float,
    current_inventory: Optional[float],
    unit_cost: float,
    selling_price: float,
    lead_time_days: Optional[float],
    planning_horizon: float = 30.0,
    service_level: float = 0.95,
    units_sold: Optional[float] = None,
) -> FinancialMetrics:
    warnings: List[str] = []

    if units_sold is not None:
        daily_revenue = units_sold * selling_price
        daily_cogs = units_sold * unit_cost
        daily_profit = daily_revenue - daily_cogs
        profit_per_unit = selling_price - unit_cost
        if daily_revenue > 0:
            gross_margin = daily_profit / daily_revenue
        else:
            gross_margin = 0.0
            if units_sold > 0:
                warnings.append("Zero revenue; gross margin set to 0.")
    else:
        daily_revenue = None
        daily_cogs = None
        daily_profit = None
        profit_per_unit = selling_price - unit_cost
        gross_margin = None

    if current_inventory is None or np.isnan(current_inventory):
        inventory_value = None
        capital_tied_up = None
        excess_units = None
        excess_inventory_value = None
        warnings.append("Missing current inventory; inventory value, capital tied up, and excess metrics unavailable.")
    else:
        inventory_value = current_inventory * unit_cost
        capital_tied_up = current_inventory * unit_cost

    planning = calculate_inventory_planning(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=current_inventory,
        lead_time_days=lead_time_days,
        service_level=service_level,
    )
    warnings.extend(planning.warnings)

    shortage_units = max(0.0, planning.lead_time_demand - (current_inventory or 0.0)) if planning.lead_time_demand is not None else None

    if shortage_units is not None:
        revenue_at_risk = shortage_units * selling_price
        profit_at_risk = shortage_units * (selling_price - unit_cost)
    else:
        revenue_at_risk = None
        profit_at_risk = None

    if planning.safety_stock is not None:
        target_stock = mean_demand * planning_horizon + planning.safety_stock
        if current_inventory is not None and not np.isnan(current_inventory):
            excess_units = max(0.0, current_inventory - target_stock)
            excess_inventory_value = excess_units * unit_cost
        else:
            excess_units = None
            excess_inventory_value = None
    else:
        target_stock = None
        excess_units = None
        excess_inventory_value = None

    return FinancialMetrics(
        daily_revenue=daily_revenue,
        daily_cogs=daily_cogs,
        daily_profit=daily_profit,
        profit_per_unit=profit_per_unit,
        gross_margin=gross_margin,
        inventory_value=inventory_value,
        capital_tied_up=capital_tied_up,
        shortage_units=shortage_units,
        revenue_at_risk=revenue_at_risk,
        profit_at_risk=profit_at_risk,
        target_stock=target_stock,
        excess_units=excess_units,
        excess_inventory_value=excess_inventory_value,
        planning_horizon=planning_horizon,
        warnings=warnings,
    )
