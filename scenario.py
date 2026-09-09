"""What-if scenario engine for InventoryIQ V2."""

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
    ComponentScores,
    CategoryRiskResult,
    OverallHealthResult,
    calculate_inventory_planning,
    calculate_financial_and_excess_metrics,
    calculate_product_risk,
    calculate_category_risk,
    calculate_overall_health,
)
from recommendation import generate_recommendation


@dataclass
class ScenarioAssumptions:
    mean_demand_change_pct: Optional[float] = None
    lead_time_days_change: Optional[float] = None


@dataclass
class BaselineResult:
    planning: InventoryPlanningResult
    financial: FinancialMetrics
    risk: ProductRiskResult
    recommendation: object


@dataclass
class ScenarioResult:
    planning: InventoryPlanningResult
    financial: FinancialMetrics
    risk: ProductRiskResult
    recommendation: object


@dataclass
class ScenarioDeltas:
    mean_demand: Optional[float] = None
    lead_time_days: Optional[float] = None
    lead_time_demand: Optional[float] = None
    safety_stock: Optional[float] = None
    reorder_point: Optional[float] = None
    stockout_probability: Optional[float] = None
    reorder_quantity: Optional[float] = None
    days_remaining: Optional[float] = None
    target_stock: Optional[float] = None
    excess_units: Optional[float] = None
    excess_inventory_value: Optional[float] = None
    revenue_at_risk: Optional[float] = None
    profit_at_risk: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None


@dataclass
class WhatIfScenario:
    assumptions: ScenarioAssumptions
    baseline: BaselineResult
    scenario: ScenarioResult
    deltas: ScenarioDeltas


def _validate_scenario_inputs(
    mean_demand: float,
    lead_time_days: Optional[float],
    mean_demand_change_pct: Optional[float],
    lead_time_days_change: Optional[float],
) -> None:
    if mean_demand_change_pct is not None:
        if not isinstance(mean_demand_change_pct, (int, float)):
            raise ValueError("mean_demand_change_pct must be a number.")
        scenario_mean_demand = mean_demand * (1 + mean_demand_change_pct)
        if scenario_mean_demand < 0:
            raise ValueError("mean_demand_change_pct produces negative mean demand.")

    if lead_time_days_change is not None:
        if not isinstance(lead_time_days_change, (int, float)):
            raise ValueError("lead_time_days_change must be a number.")
        if lead_time_days is None or np.isnan(lead_time_days) or lead_time_days <= 0:
            raise ValueError("Baseline lead_time_days must be positive to apply a lead-time change.")
        scenario_lead_time = lead_time_days + lead_time_days_change
        if scenario_lead_time <= 0:
            raise ValueError("lead_time_days_change produces non-positive lead time.")


def _compute_delta(baseline_value: Optional[float], scenario_value: Optional[float]) -> Optional[float]:
    if baseline_value is None or scenario_value is None:
        return None
    return scenario_value - baseline_value


def run_scenario(
    mean_demand: float,
    std_dev: float,
    current_inventory: Optional[float],
    unit_cost: float,
    selling_price: float,
    lead_time_days: Optional[float],
    planning_horizon: float = 30.0,
    service_level: float = 0.95,
    units_sold: Optional[float] = None,
    *,
    mean_demand_change_pct: Optional[float] = None,
    lead_time_days_change: Optional[float] = None,
) -> WhatIfScenario:
    _validate_scenario_inputs(
        mean_demand=mean_demand,
        lead_time_days=lead_time_days,
        mean_demand_change_pct=mean_demand_change_pct,
        lead_time_days_change=lead_time_days_change,
    )

    scenario_mean_demand = mean_demand * (1 + mean_demand_change_pct) if mean_demand_change_pct is not None else mean_demand
    scenario_lead_time_days = (lead_time_days + lead_time_days_change) if (lead_time_days is not None and lead_time_days_change is not None) else lead_time_days

    baseline_planning = calculate_inventory_planning(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=current_inventory,
        lead_time_days=lead_time_days,
        service_level=service_level,
    )
    baseline_financial = calculate_financial_and_excess_metrics(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        selling_price=selling_price,
        lead_time_days=lead_time_days,
        planning_horizon=planning_horizon,
        units_sold=units_sold,
    )

    demand_stats = DemandStatistics(
        mean=mean_demand,
        std_dev=std_dev,
        observation_count=30,
    )
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    baseline_risk = calculate_product_risk(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=baseline_planning,
        financial_result=baseline_financial,
        pattern_result=pattern_result,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        selling_price=selling_price,
    )
    baseline_recommendation = generate_recommendation(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=baseline_planning,
        financial_result=baseline_financial,
        pattern_result=pattern_result,
        risk_result=baseline_risk,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        lead_time_days=lead_time_days,
    )
    baseline = BaselineResult(
        planning=baseline_planning,
        financial=baseline_financial,
        risk=baseline_risk,
        recommendation=baseline_recommendation,
    )

    scenario_planning = calculate_inventory_planning(
        mean_demand=scenario_mean_demand,
        std_dev=std_dev,
        current_inventory=current_inventory,
        lead_time_days=scenario_lead_time_days,
        service_level=service_level,
    )
    scenario_financial = calculate_financial_and_excess_metrics(
        mean_demand=scenario_mean_demand,
        std_dev=std_dev,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        selling_price=selling_price,
        lead_time_days=scenario_lead_time_days,
        planning_horizon=planning_horizon,
        units_sold=units_sold,
    )
    scenario_demand_stats = DemandStatistics(
        mean=scenario_mean_demand,
        std_dev=std_dev,
        observation_count=30,
    )
    scenario_risk = calculate_product_risk(
        demand_stats=scenario_demand_stats,
        trend_result=trend_result,
        planning_result=scenario_planning,
        financial_result=scenario_financial,
        pattern_result=pattern_result,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        selling_price=selling_price,
    )
    scenario_recommendation = generate_recommendation(
        demand_stats=scenario_demand_stats,
        trend_result=trend_result,
        planning_result=scenario_planning,
        financial_result=scenario_financial,
        pattern_result=pattern_result,
        risk_result=scenario_risk,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        lead_time_days=scenario_lead_time_days,
    )
    scenario = ScenarioResult(
        planning=scenario_planning,
        financial=scenario_financial,
        risk=scenario_risk,
        recommendation=scenario_recommendation,
    )

    deltas = ScenarioDeltas(
        mean_demand=_compute_delta(mean_demand, scenario_mean_demand),
        lead_time_days=_compute_delta(lead_time_days, scenario_lead_time_days),
        lead_time_demand=_compute_delta(baseline_planning.lead_time_demand, scenario_planning.lead_time_demand),
        safety_stock=_compute_delta(baseline_planning.safety_stock, scenario_planning.safety_stock),
        reorder_point=_compute_delta(baseline_planning.reorder_point, scenario_planning.reorder_point),
        stockout_probability=_compute_delta(baseline_planning.stockout_probability, scenario_planning.stockout_probability),
        reorder_quantity=_compute_delta(baseline_planning.reorder_quantity, scenario_planning.reorder_quantity),
        days_remaining=_compute_delta(baseline_planning.days_remaining, scenario_planning.days_remaining),
        target_stock=_compute_delta(baseline_financial.target_stock, scenario_financial.target_stock),
        excess_units=_compute_delta(baseline_financial.excess_units, scenario_financial.excess_units),
        excess_inventory_value=_compute_delta(baseline_financial.excess_inventory_value, scenario_financial.excess_inventory_value),
        revenue_at_risk=_compute_delta(baseline_financial.revenue_at_risk, scenario_financial.revenue_at_risk),
        profit_at_risk=_compute_delta(baseline_financial.profit_at_risk, scenario_financial.profit_at_risk),
        risk_score=_compute_delta(baseline_risk.risk_score, scenario_risk.risk_score),
        risk_level=None,
    )

    return WhatIfScenario(
        assumptions=ScenarioAssumptions(
            mean_demand_change_pct=mean_demand_change_pct,
            lead_time_days_change=lead_time_days_change,
        ),
        baseline=baseline,
        scenario=scenario,
        deltas=deltas,
    )
