"""Recommendation engine for InventoryIQ V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from analysis import (
    DemandStatistics,
    TrendResult,
    InventoryPlanningResult,
    FinancialMetrics,
    PatternResult,
    ProductRiskResult,
    CategoryRiskResult,
    OverallHealthResult,
)


@dataclass
class RecommendationResult:
    action: str = "UNAVAILABLE"
    priority: str = "NONE"
    reorder_quantity: Optional[float] = None
    reasons: List[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def _safe_float(value: Optional[float]) -> Optional[float]:
    if value is None or np.isnan(value):
        return None
    return float(value)


def _has_signal(value: Optional[float]) -> bool:
    return value is not None and not np.isnan(value)


def generate_recommendation(
    demand_stats: DemandStatistics,
    trend_result: TrendResult,
    planning_result: InventoryPlanningResult,
    financial_result: FinancialMetrics,
    pattern_result: PatternResult,
    risk_result: ProductRiskResult,
    current_inventory: Optional[float] = None,
    unit_cost: Optional[float] = None,
    lead_time_days: Optional[float] = None,
    category_result: Optional[CategoryRiskResult] = None,
    overall_health: Optional[OverallHealthResult] = None,
) -> RecommendationResult:
    warnings: List[str] = []
    reasons: List[str] = []
    evidence: dict = {}

    mean_demand = _safe_float(demand_stats.mean)
    cv = _safe_float(demand_stats.cv)
    trend = trend_result.trend
    trend_strength = _safe_float(trend_result.trend_strength)
    stockout_probability = _safe_float(planning_result.stockout_probability)
    days_remaining = _safe_float(planning_result.days_remaining)
    lead_time_demand = _safe_float(planning_result.lead_time_demand)
    reorder_point = _safe_float(planning_result.reorder_point)
    reorder_quantity = _safe_float(planning_result.reorder_quantity)
    current_inventory = _safe_float(current_inventory)
    target_stock = _safe_float(financial_result.target_stock)
    excess_units = _safe_float(financial_result.excess_units)
    excess_inventory_value = _safe_float(financial_result.excess_inventory_value)
    revenue_at_risk = _safe_float(financial_result.revenue_at_risk)
    profit_at_risk = _safe_float(financial_result.profit_at_risk)
    risk_level = risk_result.risk_level
    risk_score = _safe_float(risk_result.risk_score)

    evidence.update({
        "mean_demand": mean_demand,
        "cv": cv,
        "trend": trend,
        "trend_strength": trend_strength,
        "stockout_probability": stockout_probability,
        "days_remaining": days_remaining,
        "lead_time_demand": lead_time_demand,
        "reorder_point": reorder_point,
        "reorder_quantity": reorder_quantity,
        "target_stock": target_stock,
        "excess_units": excess_units,
        "excess_inventory_value": excess_inventory_value,
        "revenue_at_risk": revenue_at_risk,
        "profit_at_risk": profit_at_risk,
        "risk_level": risk_level,
        "risk_score": risk_score,
    })

    if category_result is not None:
        evidence.update({
            "category_risk_level": category_result.risk_level,
            "category_risk_score": _safe_float(category_result.risk_score),
            "category_stockout_exposure": _safe_float(category_result.category_stockout_exposure),
            "category_excess_inventory_value": _safe_float(category_result.category_excess_inventory_value),
        })

    if overall_health is not None:
        evidence["overall_health_status"] = overall_health.overall_health_status

    data_quality_issues = []
    if demand_stats.observation_count == 0:
        data_quality_issues.append("No demand observations available")
    if planning_result.lead_time_demand is None:
        data_quality_issues.append("Lead-time demand unavailable")
    if financial_result.target_stock is None:
        data_quality_issues.append("Target stock unavailable")
    if risk_result.risk_score is None:
        data_quality_issues.append("Product risk score unavailable")

    if data_quality_issues:
        warnings.extend(data_quality_issues)
        reasons.append("Insufficient verified data for a confident recommendation; analysis signals are incomplete.")
        return RecommendationResult(
            action="UNAVAILABLE",
            priority="LOW",
            reasons=reasons,
            evidence=evidence,
            warnings=warnings,
        )

    coverage_ratio = days_remaining / lead_time_days if days_remaining is not None and lead_time_days and lead_time_days > 0 else None
    excess_ratio = excess_units / target_stock if target_stock and target_stock > 0 and excess_units is not None else None

    stockout_signal = _safe_float(planning_result.stockout_probability) is not None and _safe_float(planning_result.stockout_probability) > 0.3
    excess_signal = excess_ratio is not None and excess_ratio > 0.2
    low_demand_signal = mean_demand is not None and mean_demand == 0
    high_volatility_signal = cv is not None and cv > 1.0
    increasing_trend_signal = trend == "INCREASING"
    decreasing_trend_signal = trend == "DECREASING"
    high_risk_signal = risk_level == "HIGH"
    medium_risk_signal = risk_level == "MEDIUM"

    if stockout_signal and excess_signal:
        if stockout_probability is not None and stockout_probability > 0.6:
            reasons.append("Critical stockout probability overrides excess concern; stockout is the more immediate threat.")
            action = "REORDER"
            priority = "CRITICAL"
        elif excess_ratio is not None and excess_ratio > 0.5:
            reasons.append("Excess inventory is severe despite elevated stockout probability; excess takes precedence.")
            action = "REDUCE"
            priority = "HIGH"
        else:
            reasons.append("Conflicting stockout and excess signals detected; monitor for demand pattern clarification.")
            action = "MONITOR"
            priority = "MEDIUM"
    elif stockout_signal:
        if increasing_trend_signal:
            if days_remaining is not None and days_remaining <= 3:
                priority = "CRITICAL"
                reasons.append(f"Inventory coverage ({days_remaining:.1f} days) is below lead time ({lead_time_days:.1f} days).")
            elif days_remaining is not None and days_remaining <= 5:
                priority = "HIGH"
                if stockout_probability is not None and stockout_probability > 0.5:
                    reasons.append(f"Stockout probability is elevated at {stockout_probability:.1%}.")
                else:
                    reasons.append(f"Inventory coverage ({days_remaining:.1f} days) is below lead time ({lead_time_days:.1f} days).")
            else:
                priority = "MEDIUM"
                reasons.append("Stockout risk is present but not yet critical.")
            if trend == "INCREASING":
                reasons.append("Demand is increasing; monitor closely to maintain adequate stock levels.")
        else:
            if days_remaining is not None and days_remaining <= 2:
                priority = "CRITICAL"
                reasons.append(f"Inventory coverage ({days_remaining:.1f} days) is below lead time ({lead_time_days:.1f} days).")
            elif days_remaining is not None and days_remaining <= 4:
                priority = "HIGH"
                if stockout_probability is not None and stockout_probability > 0.5:
                    reasons.append(f"Stockout probability is elevated at {stockout_probability:.1%}.")
                else:
                    reasons.append(f"Inventory coverage ({days_remaining:.1f} days) is below lead time ({lead_time_days:.1f} days).")
            else:
                priority = "MEDIUM"
                reasons.append("Stockout risk is present but not yet critical.")
        action = "REORDER"
    elif high_volatility_signal and coverage_ratio is not None and coverage_ratio > 1.0:
        reasons.append("Demand is highly volatile but current coverage is adequate; monitor for sudden changes.")
        action = "MONITOR"
        priority = "MEDIUM"
    elif low_demand_signal:
        reasons.append("Mean demand is zero; no stock movement justifies reordering.")
        action = "HOLD"
        priority = "MEDIUM"
    elif excess_signal:
        if excess_ratio is not None and excess_ratio > 0.5:
            reasons.append(f"Excess inventory is significant at {excess_ratio:.1%} above target stock.")
            action = "REDUCE"
            priority = "HIGH"
        else:
            reasons.append("Excess inventory is present but not yet critical.")
            action = "REDUCE"
            priority = "MEDIUM"
    elif increasing_trend_signal and coverage_ratio is not None and coverage_ratio < 1.0:
        reasons.append("Demand is increasing and coverage is below lead time; reorder to keep pace.")
        action = "REORDER"
        priority = "HIGH"
    elif decreasing_trend_signal and coverage_ratio is not None and coverage_ratio > 1.5:
        reasons.append("Demand is decreasing and coverage is well above lead time; no reorder needed.")
        action = "HOLD"
        priority = "LOW"
    elif high_risk_signal:
        reasons.append("Product risk score is HIGH; review signals before taking action.")
        action = "MONITOR"
        priority = "MEDIUM"
    elif medium_risk_signal:
        reasons.append("Product risk score is MEDIUM; watch for changes.")
        action = "MONITOR"
        priority = "LOW"
    else:
        if coverage_ratio is not None and coverage_ratio < 0.5:
            reasons.append("Coverage is very low despite low risk score; reorder to maintain buffer.")
            action = "REORDER"
            priority = "LOW"
        else:
            reasons.append("All verified signals are within healthy ranges.")
            action = "NO_ACTION"
            priority = "NONE"

    if action == "REORDER" and reorder_quantity is not None:
        reasons.append(f"Recommended reorder quantity: {reorder_quantity:.1f} units.")
    elif action == "REORDER" and reorder_quantity is None:
        reasons.append("Reorder quantity cannot be determined with current data.")

    if stockout_probability is not None and stockout_probability > 0:
        reasons.append(f"Estimated stockout probability during lead time: {stockout_probability:.1%} (model estimate).")

    if revenue_at_risk is not None and revenue_at_risk > 0:
        reasons.append(f"Revenue at risk from shortage exposure: {revenue_at_risk:.2f}.")

    if profit_at_risk is not None and profit_at_risk > 0:
        reasons.append(f"Profit at risk from shortage exposure: {profit_at_risk:.2f}.")

    if excess_inventory_value is not None and excess_inventory_value > 0:
        reasons.append(f"Excess inventory value: {excess_inventory_value:.2f}.")

    if category_result is not None and category_result.risk_level == "HIGH":
        reasons.append(f"Category risk is HIGH ({category_result.category}); review category-level signals.")

    if overall_health is not None and overall_health.overall_health_status == "CRITICAL":
        reasons.append("Overall inventory health is CRITICAL; prioritize interventions.")

    return RecommendationResult(
        action=action,
        priority=priority,
        reorder_quantity=reorder_quantity,
        reasons=reasons,
        evidence=evidence,
        warnings=warnings,
    )
