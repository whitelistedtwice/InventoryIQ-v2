"""Shared test helpers for InventoryIQ V2 tests."""

from analysis import (
    DemandStatistics,
    TrendResult,
    InventoryPlanningResult,
    FinancialMetrics,
    PatternResult,
    ProductRiskResult,
    calculate_inventory_planning,
    calculate_financial_and_excess_metrics,
    calculate_product_risk,
)


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
