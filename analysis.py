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

    if planning.lead_time_demand is not None:
        if current_inventory is None or np.isnan(current_inventory):
            shortage_units = None
        else:
            shortage_units = max(0.0, planning.lead_time_demand - current_inventory)
    else:
        shortage_units = None

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


@dataclass
class PatternResult:
    overall_mean_demand: Optional[float] = None
    weekday_factors: Optional[dict] = None
    monthly_factors: Optional[dict] = None
    weekday_pattern_available: bool = False
    monthly_pattern_label: Optional[str] = None
    peak_weekday: Optional[str] = None
    drop_weekday: Optional[str] = None
    peak_month: Optional[str] = None
    drop_month: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def analyze_seasonality(series: pd.Series) -> PatternResult:
    clean = series.dropna()
    observation_count = int(clean.count())
    warnings: List[str] = []

    if observation_count == 0:
        warnings.append("No valid demand observations for seasonality analysis.")
        return PatternResult(warnings=warnings)

    if not isinstance(series.index, pd.DatetimeIndex):
        warnings.append("Series index must be DatetimeIndex for seasonality analysis.")
        return PatternResult(
            overall_mean_demand=float(np.mean(clean.to_numpy(dtype=float))),
            warnings=warnings,
        )

    values = clean.to_numpy(dtype=float)
    overall_mean = float(np.mean(values))

    if overall_mean == 0:
        warnings.append("Overall mean demand is zero; seasonality factors unavailable.")
        return PatternResult(overall_mean_demand=0.0, warnings=warnings)

    dates = clean.index
    weekdays = dates.weekday
    months = dates.month

    weekday_means = clean.groupby(pd.Series(weekdays, index=clean.index)).mean()
    monthly_means = clean.groupby(pd.Series(months, index=clean.index)).mean()

    weekday_factors = {}
    for day_num, mean_val in weekday_means.items():
        weekday_factors[day_num] = float(mean_val / overall_mean)

    monthly_factors = {}
    for month_num, mean_val in monthly_means.items():
        monthly_factors[month_num] = float(mean_val / overall_mean)

    unique_days = clean.nunique()
    date_range_days = (dates.max() - dates.min()).days + 1
    unique_weeks = len(clean.groupby(clean.index.isocalendar().week))

    if unique_weeks >= 4 and len(weekday_factors) >= 2:
        weekday_pattern_available = True
    else:
        weekday_pattern_available = False
        warnings.append(
            f"Insufficient history for reliable weekday pattern ({unique_weeks} weeks observed)."
        )

    unique_months = len(monthly_factors)
    if unique_months >= 12:
        monthly_pattern_label = "Annual monthly seasonality"
    elif unique_months >= 2:
        monthly_pattern_label = "Observed monthly pattern"
        warnings.append(
            f"Short history ({unique_months} months); treating as observed monthly pattern, not annual seasonality."
        )
    else:
        monthly_pattern_label = None
        warnings.append("Insufficient months for monthly pattern analysis.")

    peak_weekday = None
    drop_weekday = None
    if weekday_factors:
        peak_day_num = max(weekday_factors, key=weekday_factors.get)
        drop_day_num = min(weekday_factors, key=weekday_factors.get)
        peak_weekday = pd.Timestamp("2024-01-0" + str(peak_day_num + 1)).day_name() if peak_day_num < 6 else "Sunday"
        drop_weekday = pd.Timestamp("2024-01-0" + str(drop_day_num + 1)).day_name() if drop_day_num < 6 else "Sunday"

    peak_month = None
    drop_month = None
    if monthly_factors:
        peak_month_num = max(monthly_factors, key=monthly_factors.get)
        drop_month_num = min(monthly_factors, key=monthly_factors.get)
        peak_month = pd.Timestamp("2024-" + str(peak_month_num).zfill(2) + "-01").month_name()
        drop_month = pd.Timestamp("2024-" + str(drop_month_num).zfill(2) + "-01").month_name()

    return PatternResult(
        overall_mean_demand=overall_mean,
        weekday_factors=weekday_factors if weekday_factors else None,
        monthly_factors=monthly_factors if monthly_factors else None,
        weekday_pattern_available=weekday_pattern_available,
        monthly_pattern_label=monthly_pattern_label,
        peak_weekday=peak_weekday,
        drop_weekday=drop_weekday,
        peak_month=peak_month,
        drop_month=drop_month,
        warnings=warnings,
    )


@dataclass
class ComponentScores:
    stockout_exposure: Optional[float] = None
    demand_volatility: Optional[float] = None
    demand_trend: Optional[float] = None
    excess_inventory: Optional[float] = None
    financial_exposure: Optional[float] = None
    seasonality: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class ProductRiskResult:
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    component_scores: ComponentScores = field(default_factory=ComponentScores)
    weights_used: dict = field(default_factory=dict)
    available_weight_sum: float = 0.0
    warnings: List[str] = field(default_factory=list)


def _normalize_stockout(stockout_probability: Optional[float]) -> tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    if stockout_probability is None:
        warnings.append("Stockout probability unavailable; stockout component excluded.")
        return None, warnings
    return min(stockout_probability * 100, 100), warnings


def _normalize_volatility(cv: Optional[float]) -> tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    if cv is None:
        warnings.append("Coefficient of variation unavailable; volatility component excluded.")
        return None, warnings
    return min(cv * 50, 100), warnings


def _normalize_trend(
    trend_result: TrendResult,
    current_inventory: Optional[float],
    reorder_point: Optional[float],
    target_stock: Optional[float],
) -> tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    if trend_result.trend is None or trend_result.trend_strength is None:
        warnings.append("Trend unavailable; trend component excluded.")
        return None, warnings

    base_score = min(abs(trend_result.trend_strength) * 100, 100)

    if trend_result.trend == "STABLE":
        return 20.0, warnings

    if current_inventory is None:
        warnings.append("Current inventory unavailable; trend context unknown; trend component excluded.")
        return None, warnings

    if reorder_point is None or target_stock is None:
        warnings.append("Inventory thresholds unavailable; trend component excluded.")
        return None, warnings

    if trend_result.trend == "INCREASING":
        if current_inventory < reorder_point:
            multiplier = 1.0
        elif current_inventory > target_stock:
            multiplier = 0.5
        else:
            multiplier = 0.7
    elif trend_result.trend == "DECREASING":
        if current_inventory > target_stock:
            multiplier = 1.0
        elif current_inventory < reorder_point:
            multiplier = 0.5
        else:
            multiplier = 0.7
    else:
        multiplier = 0.3

    return min(base_score * multiplier, 100), warnings


def _normalize_excess(
    current_inventory: Optional[float],
    target_stock: Optional[float],
    excess_units: Optional[float],
) -> tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    if current_inventory is None or target_stock is None or excess_units is None:
        warnings.append("Excess inventory data unavailable; excess component excluded.")
        return None, warnings
    if excess_units <= 0:
        return 0.0, warnings
    if target_stock <= 0:
        warnings.append("Target stock is zero or negative; excess component excluded.")
        return None, warnings
    ratio = excess_units / target_stock
    return min(ratio * 100, 100), warnings


def _normalize_financial(
    revenue_at_risk: Optional[float],
    financial_reference: Optional[float],
) -> tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    if revenue_at_risk is None:
        warnings.append("Revenue at risk unavailable; financial component excluded.")
        return None, warnings
    if financial_reference is None or np.isnan(financial_reference) or financial_reference <= 0:
        warnings.append("Product-set financial reference unavailable; financial component excluded.")
        return None, warnings
    return min(revenue_at_risk / financial_reference * 100, 100), warnings


def _normalize_seasonality(pattern_result: PatternResult) -> tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    weekday_factors = pattern_result.weekday_factors
    monthly_factors = pattern_result.monthly_factors

    if not weekday_factors and not monthly_factors:
        warnings.append("Seasonality patterns unavailable; seasonality component excluded.")
        return None, warnings

    deviations: List[float] = []
    if weekday_factors:
        deviations.extend(abs(f - 1.0) for f in weekday_factors.values())
    if monthly_factors:
        deviations.extend(abs(f - 1.0) for f in monthly_factors.values())

    max_deviation = max(deviations) if deviations else 0.0
    return min(max_deviation * 100, 100), warnings


COMPONENT_WEIGHTS = {
    "stockout_exposure": 0.30,
    "demand_volatility": 0.20,
    "demand_trend": 0.15,
    "excess_inventory": 0.15,
    "financial_exposure": 0.10,
    "seasonality": 0.10,
}


def calculate_product_risk(
    demand_stats: DemandStatistics,
    trend_result: TrendResult,
    planning_result: InventoryPlanningResult,
    financial_result: FinancialMetrics,
    pattern_result: PatternResult,
    current_inventory: Optional[float],
    unit_cost: float,
    selling_price: float,
    financial_reference: Optional[float] = None,
) -> ProductRiskResult:
    warnings: List[str] = []
    component_scores = ComponentScores()

    stockout_score, stockout_warnings = _normalize_stockout(planning_result.stockout_probability)
    component_scores.stockout_exposure = stockout_score
    warnings.extend(stockout_warnings)

    volatility_score, volatility_warnings = _normalize_volatility(demand_stats.cv)
    component_scores.demand_volatility = volatility_score
    warnings.extend(volatility_warnings)

    trend_score, trend_warnings = _normalize_trend(
        trend_result=trend_result,
        current_inventory=current_inventory,
        reorder_point=planning_result.reorder_point,
        target_stock=financial_result.target_stock,
    )
    component_scores.demand_trend = trend_score
    warnings.extend(trend_warnings)

    excess_score, excess_warnings = _normalize_excess(
        current_inventory=current_inventory,
        target_stock=financial_result.target_stock,
        excess_units=financial_result.excess_units,
    )
    component_scores.excess_inventory = excess_score
    warnings.extend(excess_warnings)

    financial_score, financial_warnings = _normalize_financial(
        revenue_at_risk=financial_result.revenue_at_risk,
        financial_reference=financial_reference,
    )
    component_scores.financial_exposure = financial_score
    warnings.extend(financial_warnings)

    seasonality_score, seasonality_warnings = _normalize_seasonality(pattern_result)
    component_scores.seasonality = seasonality_score
    warnings.extend(seasonality_warnings)

    scores = {
        "stockout_exposure": stockout_score,
        "demand_volatility": volatility_score,
        "demand_trend": trend_score,
        "excess_inventory": excess_score,
        "financial_exposure": financial_score,
        "seasonality": seasonality_score,
    }

    available_components = {k: v for k, v in scores.items() if v is not None}
    available_weight_sum = sum(COMPONENT_WEIGHTS[k] for k in available_components)
    weights_used = {k: COMPONENT_WEIGHTS[k] for k in available_components}

    if available_weight_sum == 0:
        warnings.append("No risk components available; risk score unavailable.")
        return ProductRiskResult(
            component_scores=component_scores,
            weights_used=weights_used,
            available_weight_sum=0.0,
            warnings=warnings,
        )

    renormalized_score = sum(
        available_components[k] * (COMPONENT_WEIGHTS[k] / available_weight_sum) for k in available_components
    )
    risk_score = min(max(renormalized_score, 0), 100)

    if risk_score <= 39:
        risk_level = "LOW"
    elif risk_score <= 69:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return ProductRiskResult(
        risk_score=risk_score,
        risk_level=risk_level,
        component_scores=component_scores,
        weights_used=weights_used,
        available_weight_sum=available_weight_sum,
        warnings=warnings,
    )


@dataclass
class CategoryRiskResult:
    category: str = ""
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    product_count: int = 0
    high_risk_product_count: int = 0
    average_product_risk_score: Optional[float] = None
    category_inventory_value: Optional[float] = None
    category_capital_tied_up: Optional[float] = None
    category_stockout_exposure: Optional[float] = None
    category_excess_inventory_value: Optional[float] = None
    category_demand_volatility: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class OverallHealthResult:
    overall_risk_score: Optional[float] = None
    overall_health_status: Optional[str] = None
    total_products: int = 0
    products_at_risk: int = 0
    total_categories: int = 0
    high_risk_categories: int = 0
    total_stockout_exposure: Optional[float] = None
    total_excess_inventory_value: Optional[float] = None
    total_capital_tied_up: Optional[float] = None
    total_revenue_at_risk: Optional[float] = None
    total_profit_at_risk: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


def calculate_category_risk(
    products: List[dict],
    total_inventory_value: Optional[float] = None,
) -> dict[str, CategoryRiskResult]:
    from collections import defaultdict

    warnings: List[str] = []
    grouped: dict[str, List[dict]] = defaultdict(list)
    for product in products:
        category = product.get("category")
        if category is not None:
            grouped[category].append(product)

    results: dict[str, CategoryRiskResult] = {}

    for category, category_products in grouped.items():
        category_warnings: List[str] = []
        product_count = len(category_products)

        risk_scores: List[float] = []
        high_risk_count = 0
        inventory_values: List[float] = []
        capital_tied_ups: List[float] = []
        stockout_exposures: List[float] = []
        excess_values: List[float] = []
        cvs: List[float] = []

        for product in category_products:
            risk_score = product.get("risk_score")
            risk_level = product.get("risk_level")
            if risk_score is not None:
                risk_scores.append(float(risk_score))
            if risk_level == "HIGH":
                high_risk_count += 1

            inventory_value = product.get("inventory_value")
            if inventory_value is not None and not np.isnan(inventory_value):
                inventory_values.append(float(inventory_value))

            capital_tied_up = product.get("capital_tied_up")
            if capital_tied_up is not None and not np.isnan(capital_tied_up):
                capital_tied_ups.append(float(capital_tied_up))

            shortage_units = product.get("shortage_units")
            selling_price = product.get("selling_price")
            if (
                shortage_units is not None
                and not np.isnan(shortage_units)
                and selling_price is not None
                and not np.isnan(selling_price)
            ):
                stockout_exposures.append(float(shortage_units) * float(selling_price))

            excess_inventory_value = product.get("excess_inventory_value")
            if excess_inventory_value is not None and not np.isnan(excess_inventory_value):
                excess_values.append(float(excess_inventory_value))

            cv = product.get("cv")
            if cv is not None and not np.isnan(cv):
                cvs.append(float(cv))

        average_risk_score = float(np.mean(risk_scores)) if risk_scores else None
        category_inventory_value = float(np.sum(inventory_values)) if inventory_values else None
        category_capital_tied_up = float(np.sum(capital_tied_ups)) if capital_tied_ups else None
        category_stockout_exposure = float(np.sum(stockout_exposures)) if stockout_exposures else None
        category_excess_inventory_value = float(np.sum(excess_values)) if excess_values else None
        category_demand_volatility = float(np.mean(cvs)) if cvs else None

        if not risk_scores:
            category_warnings.append(
                f"No valid product risk scores available for category '{category}'."
            )

        risk_score = None
        risk_level = None

        if average_risk_score is not None:
            financial_score = 0.0
            if (
                total_inventory_value is not None
                and not np.isnan(total_inventory_value)
                and total_inventory_value > 0
                and category_inventory_value is not None
            ):
                financial_ratio = category_inventory_value / total_inventory_value
                financial_score = min(financial_ratio * 100, 100)

            high_risk_ratio = high_risk_count / product_count if product_count > 0 else 0.0
            high_risk_score = min(high_risk_ratio * 200, 100)

            risk_score = min(
                0.70 * average_risk_score + 0.15 * financial_score + 0.15 * high_risk_score,
                100,
            )
            risk_score = max(risk_score, 0)

            if risk_score <= 39:
                risk_level = "LOW"
            elif risk_score <= 69:
                risk_level = "MEDIUM"
            else:
                risk_level = "HIGH"

        results[category] = CategoryRiskResult(
            category=category,
            risk_score=risk_score,
            risk_level=risk_level,
            product_count=product_count,
            high_risk_product_count=high_risk_count,
            average_product_risk_score=average_risk_score,
            category_inventory_value=category_inventory_value,
            category_capital_tied_up=category_capital_tied_up,
            category_stockout_exposure=category_stockout_exposure,
            category_excess_inventory_value=category_excess_inventory_value,
            category_demand_volatility=category_demand_volatility,
            warnings=category_warnings,
        )

    return results


def calculate_overall_health(
    category_results: dict[str, CategoryRiskResult],
    products: List[dict],
    total_inventory_value: Optional[float] = None,
) -> OverallHealthResult:
    warnings: List[str] = []

    if not category_results and not products:
        warnings.append("No category or product data available for overall health.")
        return OverallHealthResult(warnings=warnings)

    category_scores: List[float] = []
    high_risk_categories = 0
    total_stockout_exposure = 0.0
    total_excess_inventory_value = 0.0
    total_capital_tied_up = 0.0
    total_revenue_at_risk = 0.0
    total_profit_at_risk = 0.0
    products_at_risk = 0
    stockout_observed = False
    excess_observed = False

    for category_result in category_results.values():
        if category_result.risk_score is not None:
            category_scores.append(category_result.risk_score)
        if category_result.risk_level == "HIGH":
            high_risk_categories += 1
        if category_result.category_stockout_exposure is not None and category_result.category_stockout_exposure > 0:
            total_stockout_exposure += category_result.category_stockout_exposure
            stockout_observed = True
        if category_result.category_excess_inventory_value is not None and category_result.category_excess_inventory_value > 0:
            total_excess_inventory_value += category_result.category_excess_inventory_value
            excess_observed = True
        if category_result.category_capital_tied_up is not None and category_result.category_capital_tied_up > 0:
            total_capital_tied_up += category_result.category_capital_tied_up

    for product in products:
        risk_level = product.get("risk_level")
        if risk_level in ("MEDIUM", "HIGH"):
            products_at_risk += 1

        revenue_at_risk = product.get("revenue_at_risk")
        if revenue_at_risk is not None and not np.isnan(revenue_at_risk):
            total_revenue_at_risk += float(revenue_at_risk)

        profit_at_risk = product.get("profit_at_risk")
        if profit_at_risk is not None and not np.isnan(profit_at_risk):
            total_profit_at_risk += float(profit_at_risk)

    overall_risk_score = float(np.mean(category_scores)) if category_scores else None
    overall_health_status = None

    if overall_risk_score is not None:
        if overall_risk_score <= 39:
            overall_health_status = "HEALTHY"
        elif overall_risk_score <= 69:
            overall_health_status = "ATTENTION"
        else:
            overall_health_status = "CRITICAL"

    if total_stockout_exposure == 0 and stockout_observed is False:
        total_stockout_exposure = None
    if total_excess_inventory_value == 0 and excess_observed is False:
        total_excess_inventory_value = None

    return OverallHealthResult(
        overall_risk_score=overall_risk_score,
        overall_health_status=overall_health_status,
        total_products=len(products),
        products_at_risk=products_at_risk,
        total_categories=len(category_results),
        high_risk_categories=high_risk_categories,
        total_stockout_exposure=total_stockout_exposure if stockout_observed else None,
        total_excess_inventory_value=total_excess_inventory_value if excess_observed else None,
        total_capital_tied_up=total_capital_tied_up if total_capital_tied_up > 0 else None,
        total_revenue_at_risk=total_revenue_at_risk if total_revenue_at_risk > 0 else None,
        total_profit_at_risk=total_profit_at_risk if total_profit_at_risk > 0 else None,
        warnings=warnings,
    )
