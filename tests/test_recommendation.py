import numpy as np
import pytest

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
from recommendation import RecommendationResult, generate_recommendation


def _base_planning(mean_demand=10.0, std_dev=3.0, current_inventory=60.0, lead_time_days=7.0, service_level=0.95):
    return calculate_inventory_planning(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=current_inventory,
        lead_time_days=lead_time_days,
        service_level=service_level,
    )


def _base_financial(mean_demand=10.0, std_dev=3.0, current_inventory=60.0, unit_cost=5.0, selling_price=10.0, lead_time_days=7.0, planning_horizon=30.0, units_sold=20.0):
    return calculate_financial_and_excess_metrics(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        selling_price=selling_price,
        lead_time_days=lead_time_days,
        planning_horizon=planning_horizon,
        units_sold=units_sold,
    )


def _base_risk(demand_stats, trend_result, planning_result, financial_result, pattern_result, current_inventory=60.0, unit_cost=5.0, selling_price=10.0, financial_reference=1000.0):
    return calculate_product_risk(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning_result,
        financial_result=financial_result,
        pattern_result=pattern_result,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        selling_price=selling_price,
        financial_reference=financial_reference,
    )


def _recommendation(**kwargs):
    planning = kwargs.get("planning_result")
    financial = kwargs.get("financial_result")
    risk = kwargs.get("risk_result")
    category = kwargs.get("category_result")
    overall = kwargs.get("overall_health")
    current_inventory = kwargs.get("current_inventory")
    unit_cost = kwargs.get("unit_cost")
    lead_time_days = kwargs.get("lead_time_days")

    if planning is None:
        planning = _base_planning()
    if financial is None:
        financial = _base_financial()
    if risk is None:
        demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
        trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
        pattern_result = PatternResult()
        risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result)

    if lead_time_days is None and planning is not None:
        lead_time_days = 7.0

    return generate_recommendation(
        demand_stats=kwargs.get("demand_stats", DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)),
        trend_result=kwargs.get("trend_result", TrendResult(trend="STABLE", trend_strength=0.0)),
        planning_result=planning,
        financial_result=financial,
        pattern_result=kwargs.get("pattern_result", PatternResult()),
        risk_result=risk,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        lead_time_days=lead_time_days,
        category_result=category,
        overall_health=overall,
    )


def test_reorder_critical_stockout():
    planning = _base_planning(current_inventory=20.0)
    financial = _base_financial(current_inventory=20.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=20.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=20.0,
    )
    assert result.action == "REORDER"
    assert result.priority == "CRITICAL"
    assert result.reorder_quantity == pytest.approx(planning.reorder_quantity)
    assert any("coverage" in reason.lower() for reason in result.reasons)


def test_reorder_quantity_present():
    planning = _base_planning(current_inventory=20.0)
    financial = _base_financial(current_inventory=20.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=20.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=20.0,
    )
    assert result.reorder_quantity is not None
    assert result.reorder_quantity > 0


def test_hold_pause_reordering_low_demand():
    planning = _base_planning(mean_demand=0.0, current_inventory=50.0)
    financial = _base_financial(mean_demand=0.0, current_inventory=50.0, units_sold=0.0)
    demand_stats = DemandStatistics(mean=0.0, std_dev=0.0, cv=None, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=50.0)

    result = _recommendation(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=50.0,
    )
    assert result.action == "HOLD"
    assert result.priority == "MEDIUM"
    assert any("zero" in reason.lower() for reason in result.reasons)


def test_reduce_excess_inventory_significant():
    planning = _base_planning(current_inventory=400.0)
    financial = _base_financial(current_inventory=400.0, units_sold=10.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="DECREASING", trend_strength=-0.2)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=400.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=400.0,
    )
    assert result.action == "REDUCE"
    assert result.priority in ("HIGH", "MEDIUM")
    assert any("excess" in reason.lower() for reason in result.reasons)


def test_monitor_volatile_demand_adequate_coverage():
    planning = _base_planning(current_inventory=150.0)
    financial = _base_financial(current_inventory=150.0, units_sold=20.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=15.0, cv=1.5, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=150.0)

    result = _recommendation(
        demand_stats=demand_stats,
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=150.0,
    )
    assert result.action == "MONITOR"
    assert result.priority == "MEDIUM"
    assert any("volatile" in reason.lower() or "monitor" in reason.lower() for reason in result.reasons)


def test_no_action_healthy():
    planning = _base_planning(current_inventory=100.0)
    financial = _base_financial(current_inventory=100.0, units_sold=15.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=2.0, cv=0.2, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=100.0)

    result = _recommendation(
        demand_stats=demand_stats,
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=100.0,
    )
    assert result.action == "NO_ACTION"
    assert result.priority == "NONE"
    assert any("healthy" in reason.lower() for reason in result.reasons)


def test_missing_data_unavailable():
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    planning = _base_planning(current_inventory=60.0)
    financial = _base_financial(current_inventory=60.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=60.0)

    empty_risk = ProductRiskResult(
        risk_score=None,
        risk_level=None,
        component_scores=ComponentScores(),
        weights_used={},
        available_weight_sum=0.0,
        warnings=["No risk components available"],
    )
    result = _recommendation(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning,
        financial_result=financial,
        pattern_result=pattern_result,
        risk_result=empty_risk,
        current_inventory=60.0,
    )
    assert result.action == "UNAVAILABLE"
    assert result.priority == "LOW"
    assert any("insufficient" in reason.lower() for reason in result.reasons)


def test_conflict_stockout_plus_excess_stockout_wins():
    planning = _base_planning(current_inventory=30.0)
    financial = _base_financial(current_inventory=30.0, units_sold=5.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="INCREASING", trend_strength=0.3)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=30.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=30.0,
        trend_result=trend_result,
    )
    assert result.action == "REORDER"
    assert result.priority == "CRITICAL"
    assert any("stockout" in reason.lower() for reason in result.reasons)


def test_conflict_stockout_plus_excess_excess_wins():
    planning = _base_planning(current_inventory=500.0)
    financial = _base_financial(current_inventory=500.0, units_sold=5.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="DECREASING", trend_strength=-0.2)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=500.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=500.0,
    )
    assert result.action == "REDUCE"
    assert result.priority == "HIGH"
    assert any("excess" in reason.lower() for reason in result.reasons)


def test_high_demand_increasing_trend_low_inventory():
    planning = _base_planning(current_inventory=40.0)
    financial = _base_financial(current_inventory=40.0, units_sold=25.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="INCREASING", trend_strength=0.4)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=40.0)

    result = _recommendation(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=40.0,
    )
    assert result.action == "REORDER"
    assert result.priority == "HIGH"
    assert any("increasing" in reason.lower() for reason in result.reasons)


def test_low_inventory_low_demand_hold():
    planning = _base_planning(mean_demand=0.0, current_inventory=5.0)
    financial = _base_financial(mean_demand=0.0, current_inventory=5.0, units_sold=0.0)
    demand_stats = DemandStatistics(mean=0.0, std_dev=0.0, cv=None, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=5.0)

    result = _recommendation(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=5.0,
    )
    assert result.action == "HOLD"
    assert result.priority == "MEDIUM"


def test_healthy_inventory_volatile_demand_monitor():
    planning = _base_planning(current_inventory=150.0)
    financial = _base_financial(current_inventory=150.0, units_sold=20.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=15.0, cv=1.5, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=150.0)

    result = _recommendation(
        demand_stats=demand_stats,
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=150.0,
    )
    assert result.action == "MONITOR"
    assert result.priority == "MEDIUM"
    assert any("volatile" in reason.lower() or "monitor" in reason.lower() for reason in result.reasons)


def test_evidence_contains_verified_metrics():
    planning = _base_planning(current_inventory=20.0)
    financial = _base_financial(current_inventory=20.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=20.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=20.0,
    )
    assert "stockout_probability" in result.evidence
    assert "days_remaining" in result.evidence
    assert "reorder_point" in result.evidence
    assert "excess_units" in result.evidence
    assert "risk_level" in result.evidence
    assert "trend" in result.evidence
    assert result.evidence["stockout_probability"] == pytest.approx(planning.stockout_probability)


def test_missing_lead_time_unavailable():
    planning = _base_planning(current_inventory=60.0)
    planning.lead_time_demand = None
    planning.reorder_point = None
    planning.stockout_probability = None
    planning.reorder_quantity = None
    planning.warnings.append("Invalid or unavailable lead time; replenishment calculations unavailable.")

    financial = _base_financial(current_inventory=60.0)
    financial.target_stock = None
    financial.excess_units = None
    financial.excess_inventory_value = None
    financial.revenue_at_risk = None
    financial.profit_at_risk = None
    financial.warnings.append("Invalid or unavailable lead time; replenishment calculations unavailable.")

    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=60.0)

    result = _recommendation(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=60.0,
    )
    assert result.action == "UNAVAILABLE"
    assert any("lead-time" in warning.lower() for warning in result.warnings)


def test_consistency_with_analysis_outputs():
    planning = _base_planning(current_inventory=20.0)
    financial = _base_financial(current_inventory=20.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=20.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=20.0,
    )

    assert result.evidence["reorder_quantity"] == pytest.approx(planning.reorder_quantity)
    assert result.evidence["stockout_probability"] == pytest.approx(planning.stockout_probability)
    assert result.evidence["days_remaining"] == pytest.approx(planning.days_remaining)
    assert result.evidence["excess_units"] == pytest.approx(financial.excess_units)
    assert result.evidence["target_stock"] == pytest.approx(financial.target_stock)
    assert result.evidence["risk_level"] == risk.risk_level


def test_priority_ordering():
    scenarios = [
        (_base_planning(current_inventory=10.0), 10.0, "CRITICAL"),
        (_base_planning(current_inventory=30.0), 30.0, "HIGH"),
        (_base_planning(current_inventory=50.0), 50.0, "MEDIUM"),
    ]

    for planning, inv, expected_priority in scenarios:
        financial = _base_financial(current_inventory=inv)
        demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
        trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
        pattern_result = PatternResult()
        risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=inv)
        result = _recommendation(
            planning_result=planning,
            financial_result=financial,
            risk_result=risk,
            current_inventory=inv,
        )
        assert result.priority == expected_priority, f"Expected {expected_priority}, got {result.priority} for inventory={inv}"


def test_reasons_are_non_empty():
    planning = _base_planning(current_inventory=100.0)
    financial = _base_financial(current_inventory=100.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=100.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=100.0,
    )
    assert len(result.reasons) > 0
    for reason in result.reasons:
        assert len(reason) > 0


def test_action_is_one_of_locked_types():
    planning = _base_planning(current_inventory=100.0)
    financial = _base_financial(current_inventory=100.0)
    demand_stats = DemandStatistics(mean=10.0, std_dev=3.0, cv=0.3, observation_count=30)
    trend_result = TrendResult(trend="STABLE", trend_strength=0.0)
    pattern_result = PatternResult()
    risk = _base_risk(demand_stats, trend_result, planning, financial, pattern_result, current_inventory=100.0)

    result = _recommendation(
        planning_result=planning,
        financial_result=financial,
        risk_result=risk,
        current_inventory=100.0,
    )
    assert result.action in {"REORDER", "HOLD", "REDUCE", "MONITOR", "NO_ACTION", "UNAVAILABLE"}
