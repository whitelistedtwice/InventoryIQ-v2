import pytest

from analysis import (
    DemandStatistics,
    TrendResult,
    InventoryPlanningResult,
    FinancialMetrics,
    PatternResult,
    ProductRiskResult,
    calculate_inventory_planning,
    calculate_financial_and_excess_metrics,
)
from recommendation import generate_recommendation
from scenario import (
    ScenarioAssumptions,
    BaselineResult,
    ScenarioResult,
    ScenarioDeltas,
    WhatIfScenario,
    run_scenario,
)

from .test_helpers import _base_planning, _base_financial, _base_risk


def test_scenario_baseline_unchanged_after_scenario():
    baseline_mean_demand = 10.0
    baseline_std_dev = 3.0
    baseline_inventory = 60.0
    baseline_lead_time = 7.0

    scenario = run_scenario(
        mean_demand=baseline_mean_demand,
        std_dev=baseline_std_dev,
        current_inventory=baseline_inventory,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=baseline_lead_time,
        planning_horizon=30.0,
        units_sold=20.0,
        mean_demand_change_pct=0.20,
    )

    baseline_planning = calculate_inventory_planning(
        mean_demand=baseline_mean_demand,
        std_dev=baseline_std_dev,
        current_inventory=baseline_inventory,
        lead_time_days=baseline_lead_time,
    )
    baseline_financial = calculate_financial_and_excess_metrics(
        mean_demand=baseline_mean_demand,
        std_dev=baseline_std_dev,
        current_inventory=baseline_inventory,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=baseline_lead_time,
        planning_horizon=30.0,
        units_sold=20.0,
    )

    assert scenario.baseline.planning.lead_time_demand == pytest.approx(baseline_planning.lead_time_demand)
    assert scenario.baseline.planning.reorder_point == pytest.approx(baseline_planning.reorder_point)
    assert scenario.baseline.planning.stockout_probability == pytest.approx(baseline_planning.stockout_probability)
    assert scenario.baseline.financial.target_stock == pytest.approx(baseline_financial.target_stock)
    assert scenario.baseline.financial.excess_units == pytest.approx(baseline_financial.excess_units)


def test_scenario_positive_demand_change():
    scenario = run_scenario(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        planning_horizon=30.0,
        units_sold=20.0,
        mean_demand_change_pct=0.20,
    )

    assert scenario.scenario.planning.lead_time_demand == pytest.approx(10.0 * 1.20 * 7.0)
    assert scenario.scenario.financial.target_stock == pytest.approx(10.0 * 1.20 * 30.0 + scenario.scenario.planning.safety_stock)
    assert scenario.deltas.mean_demand == pytest.approx(2.0)
    assert scenario.deltas.lead_time_demand == pytest.approx(14.0)
    assert scenario.deltas.target_stock is not None
    assert scenario.deltas.target_stock > 0


def test_scenario_increased_lead_time():
    scenario = run_scenario(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        planning_horizon=30.0,
        units_sold=20.0,
        lead_time_days_change=3.0,
    )

    assert scenario.scenario.planning.lead_time_demand == pytest.approx(10.0 * 10.0)
    assert scenario.scenario.planning.safety_stock > scenario.baseline.planning.safety_stock
    assert scenario.scenario.planning.reorder_point > scenario.baseline.planning.reorder_point
    assert scenario.scenario.financial.target_stock > scenario.baseline.financial.target_stock
    assert scenario.deltas.lead_time_days == pytest.approx(3.0)
    assert scenario.deltas.safety_stock is not None
    assert scenario.deltas.safety_stock > 0


def test_scenario_reset_restores_baseline():
    scenario = run_scenario(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        planning_horizon=30.0,
        units_sold=20.0,
        mean_demand_change_pct=0.20,
        lead_time_days_change=3.0,
    )

    assert scenario.assumptions.mean_demand_change_pct == pytest.approx(0.20)
    assert scenario.assumptions.lead_time_days_change == pytest.approx(3.0)
    assert scenario.baseline.planning.lead_time_demand == pytest.approx(70.0)
    assert scenario.scenario.planning.lead_time_demand == pytest.approx(120.0)
    assert scenario.deltas.lead_time_demand == pytest.approx(50.0)


def test_scenario_negative_demand_change_rejected():
    with pytest.raises(ValueError, match="negative mean demand"):
        run_scenario(
            mean_demand=10.0,
            std_dev=3.0,
            current_inventory=60.0,
            unit_cost=5.0,
            selling_price=10.0,
            lead_time_days=7.0,
            mean_demand_change_pct=-1.5,
        )


def test_scenario_negative_lead_time_rejected():
    with pytest.raises(ValueError, match="non-positive lead time"):
        run_scenario(
            mean_demand=10.0,
            std_dev=3.0,
            current_inventory=60.0,
            unit_cost=5.0,
            selling_price=10.0,
            lead_time_days=7.0,
            lead_time_days_change=-10.0,
        )


def test_scenario_does_not_mutate_inputs():
    original_mean_demand = 10.0
    original_std_dev = 3.0
    original_inventory = 60.0
    original_lead_time = 7.0

    run_scenario(
        mean_demand=original_mean_demand,
        std_dev=original_std_dev,
        current_inventory=original_inventory,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=original_lead_time,
        mean_demand_change_pct=0.50,
        lead_time_days_change=5.0,
    )

    assert original_mean_demand == 10.0
    assert original_std_dev == 3.0
    assert original_inventory == 60.0
    assert original_lead_time == 7.0


def test_scenario_reuses_same_methodology():
    baseline_planning = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        lead_time_days=7.0,
    )
    scenario = run_scenario(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        mean_demand_change_pct=0.20,
    )

    expected_planning = calculate_inventory_planning(
        mean_demand=12.0,
        std_dev=3.0,
        current_inventory=60.0,
        lead_time_days=7.0,
    )
    assert scenario.scenario.planning.lead_time_demand == pytest.approx(expected_planning.lead_time_demand)
    assert scenario.scenario.planning.reorder_point == pytest.approx(expected_planning.reorder_point)
    assert scenario.scenario.planning.stockout_probability == pytest.approx(expected_planning.stockout_probability)


def test_scenario_risk_and_recommendation_respond():
    scenario = run_scenario(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=20.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        planning_horizon=30.0,
        units_sold=20.0,
        mean_demand_change_pct=0.50,
        lead_time_days_change=4.0,
    )

    assert scenario.baseline.risk.risk_score is not None
    assert scenario.scenario.risk.risk_score is not None
    assert scenario.deltas.risk_score is not None

    assert scenario.baseline.recommendation.action in {
        "REORDER", "HOLD", "REDUCE", "MONITOR", "NO_ACTION", "UNAVAILABLE"
    }
    assert scenario.scenario.recommendation.action in {
        "REORDER", "HOLD", "REDUCE", "MONITOR", "NO_ACTION", "UNAVAILABLE"
    }


def test_scenario_invalid_demand_change_type():
    with pytest.raises(ValueError, match="mean_demand_change_pct must be a number"):
        run_scenario(
            mean_demand=10.0,
            std_dev=3.0,
            current_inventory=60.0,
            unit_cost=5.0,
            selling_price=10.0,
            lead_time_days=7.0,
            mean_demand_change_pct="invalid",
        )


def test_scenario_invalid_lead_time_change_type():
    with pytest.raises(ValueError, match="lead_time_days_change must be a number"):
        run_scenario(
            mean_demand=10.0,
            std_dev=3.0,
            current_inventory=60.0,
            unit_cost=5.0,
            selling_price=10.0,
            lead_time_days=7.0,
            lead_time_days_change="invalid",
        )


def test_scenario_zero_demand_with_change():
    scenario = run_scenario(
        mean_demand=0.0,
        std_dev=3.0,
        current_inventory=50.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        mean_demand_change_pct=1.0,
    )
    assert scenario.scenario.planning.lead_time_demand == pytest.approx(0.0)


def test_scenario_deltas_are_none_when_no_change():
    scenario = run_scenario(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
    )
    assert scenario.deltas.mean_demand == pytest.approx(0.0)
    assert scenario.deltas.lead_time_days == pytest.approx(0.0)
    assert scenario.deltas.lead_time_demand == pytest.approx(0.0)
    assert scenario.deltas.safety_stock == pytest.approx(0.0)
    assert scenario.deltas.reorder_point == pytest.approx(0.0)
