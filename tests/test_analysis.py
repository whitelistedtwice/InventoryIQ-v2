import numpy as np
import pandas as pd
import pytest

from analysis import (
    DemandStatistics,
    TrendResult,
    OutlierResult,
    InventoryPlanningResult,
    FinancialMetrics,
    PatternResult,
    ProductRiskResult,
    ComponentScores,
    CategoryRiskResult,
    OverallHealthResult,
    calculate_demand_statistics,
    calculate_trend,
    detect_outliers,
    calculate_inventory_planning,
    calculate_financial_and_excess_metrics,
    analyze_seasonality,
    calculate_product_risk,
    calculate_category_risk,
    calculate_overall_health,
)


def _stats(series):
    return calculate_demand_statistics(series)


def test_known_values():
    series = pd.Series([8.0, 10.0, 12.0])
    result = _stats(series)
    assert result.mean == pytest.approx(10.0)
    assert result.median == pytest.approx(10.0)
    assert result.std_dev == pytest.approx(2.0)
    assert result.variance == pytest.approx(4.0)
    assert result.cv == pytest.approx(0.2)
    assert result.min == pytest.approx(8.0)
    assert result.max == pytest.approx(12.0)
    assert result.volatility == "LOW"
    assert result.observation_count == 3
    assert result.warnings == []


def test_median_even_count():
    series = pd.Series([3.0, 5.0, 8.0, 20.0])
    result = _stats(series)
    assert result.mean == pytest.approx(9.0)
    assert result.median == pytest.approx(6.5)
    assert result.std_dev == pytest.approx(np.std([3, 5, 8, 20], ddof=1))
    assert result.observation_count == 4


def test_volatility_medium():
    series = pd.Series([5.0, 10.0, 15.0, 20.0])
    result = _stats(series)
    assert result.volatility == "MEDIUM"


def test_volatility_high():
    series = pd.Series([1.0, 10.0, 1.0, 10.0])
    result = _stats(series)
    assert result.volatility == "HIGH"


def test_volatility_zero_variance():
    series = pd.Series([10.0, 10.0, 10.0])
    result = _stats(series)
    assert result.std_dev == pytest.approx(0.0)
    assert result.variance == pytest.approx(0.0)
    assert result.cv == pytest.approx(0.0)
    assert result.volatility == "ZERO_VARIANCE"


def test_zero_mean_demand():
    series = pd.Series([0.0, 0.0, 0.0])
    result = _stats(series)
    assert result.mean == pytest.approx(0.0)
    assert result.std_dev == pytest.approx(0.0)
    assert result.cv is None
    assert result.volatility == "ZERO_VARIANCE"
    assert any("zero" in warning.lower() and "variation" in warning.lower() for warning in result.warnings)


def test_single_observation():
    series = pd.Series([10.0])
    result = _stats(series)
    assert result.mean == pytest.approx(10.0)
    assert result.median == pytest.approx(10.0)
    assert result.std_dev is None
    assert result.variance is None
    assert result.cv is None
    assert result.min == pytest.approx(10.0)
    assert result.max == pytest.approx(10.0)
    assert result.observation_count == 1
    assert any("Insufficient observations" in warning for warning in result.warnings)


def test_empty_series():
    series = pd.Series([], dtype=float)
    result = _stats(series)
    assert result.observation_count == 0
    assert result.mean is None
    assert result.median is None
    assert result.std_dev is None
    assert result.variance is None
    assert result.cv is None
    assert result.min is None
    assert result.max is None
    assert result.volatility is None
    assert any("No valid demand observations" in warning for warning in result.warnings)


def test_all_nan_series():
    series = pd.Series([np.nan, np.nan])
    result = _stats(series)
    assert result.observation_count == 0
    assert result.mean is None
    assert any("No valid demand observations" in warning for warning in result.warnings)


def test_missing_values_ignored():
    series = pd.Series([10.0, np.nan, 20.0, np.nan, 30.0])
    result = _stats(series)
    assert result.observation_count == 3
    assert result.mean == pytest.approx(20.0)
    assert result.median == pytest.approx(20.0)
    assert result.min == pytest.approx(10.0)
    assert result.max == pytest.approx(30.0)


def test_trend_known_values_increasing():
    series = pd.Series([8.0, 10.0, 12.0])
    result = calculate_trend(series)
    assert result.slope == pytest.approx(2.0)
    assert result.intercept == pytest.approx(8.0)
    assert result.trend_strength == pytest.approx(0.4)
    assert result.trend == "INCREASING"
    assert result.warnings == []


def test_trend_known_values_decreasing():
    series = pd.Series([12.0, 10.0, 8.0])
    result = calculate_trend(series)
    assert result.slope == pytest.approx(-2.0)
    assert result.intercept == pytest.approx(12.0)
    assert result.trend_strength == pytest.approx(-0.4)
    assert result.trend == "DECREASING"
    assert result.warnings == []


def test_trend_stable():
    series = pd.Series([10.0, 10.0, 10.0])
    result = calculate_trend(series)
    assert result.slope == pytest.approx(0.0)
    assert result.trend_strength == pytest.approx(0.0)
    assert result.trend == "STABLE"
    assert result.warnings == []


def test_trend_boundary_increasing():
    series = pd.Series([9.4, 10.0, 10.6])
    result = calculate_trend(series)
    assert result.trend_strength == pytest.approx(0.12)
    assert result.trend == "INCREASING"


def test_trend_boundary_decreasing():
    series = pd.Series([10.6, 10.0, 9.4])
    result = calculate_trend(series)
    assert result.trend_strength == pytest.approx(-0.12)
    assert result.trend == "DECREASING"


def test_trend_stable_near_boundary():
    series = pd.Series([9.6, 10.0, 10.4])
    result = calculate_trend(series)
    assert result.trend_strength == pytest.approx(0.08)
    assert result.trend == "STABLE"


def test_trend_zero_mean():
    series = pd.Series([0.0, 0.0, 0.0])
    result = calculate_trend(series)
    assert result.slope == pytest.approx(0.0)
    assert result.trend_strength is None
    assert result.trend is None
    assert any("zero" in warning.lower() for warning in result.warnings)


def test_trend_insufficient_data():
    series = pd.Series([10.0])
    result = calculate_trend(series)
    assert result.slope is None
    assert result.trend is None
    assert any("Insufficient observations" in warning for warning in result.warnings)


def test_outlier_iqr_known_values():
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0])
    result = detect_outliers(series)
    assert result.method == "IQR"
    assert result.lower_fence == pytest.approx(-1.0)
    assert result.upper_fence == pytest.approx(7.0)
    assert result.outlier_mask is not None
    assert result.outlier_mask.tolist() == [False, False, False, False, True]


def test_outlier_no_outliers():
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = detect_outliers(series)
    assert result.method == "IQR"
    assert result.outlier_mask is not None
    assert result.outlier_mask.tolist() == [False, False, False, False, False]


def test_outlier_mad_fallback():
    series = pd.Series([1.0, 2.0, 2.0, 100.0])
    result = detect_outliers(series)
    assert result.method == "MAD"
    assert result.lower_fence is None
    assert result.upper_fence is None
    assert result.outlier_mask is not None
    assert result.outlier_mask.tolist() == [False, False, False, True]


def test_outlier_zero_mad_unavailable():
    series = pd.Series([5.0, 5.0, 5.0, 5.0])
    result = detect_outliers(series)
    assert result.method is None
    assert result.outlier_mask is None
    assert any("Zero median absolute deviation" in warning for warning in result.warnings)


def test_outlier_empty_series():
    series = pd.Series([], dtype=float)
    result = detect_outliers(series)
    assert result.outlier_mask is None
    assert any("No valid observations" in warning for warning in result.warnings)


def test_outlier_all_nan():
    series = pd.Series([np.nan, np.nan])
    result = detect_outliers(series)
    assert result.outlier_mask is None
    assert any("No valid observations" in warning for warning in result.warnings)


def test_outliers_not_deleted():
    original = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0])
    result = detect_outliers(original)
    assert len(original) == 5
    assert result.outlier_mask is not None
    assert result.outlier_mask.sum() == 1
    assert original.tolist() == [1.0, 2.0, 3.0, 4.0, 100.0]


def test_inventory_planning_known_values():
    from scipy.stats import norm
    z = float(norm.ppf(0.95))
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        lead_time_days=7.0,
    )
    assert result.lead_time_demand == pytest.approx(70.0)
    assert result.lead_time_sd == pytest.approx(3.0 * np.sqrt(7.0))
    assert result.safety_stock == pytest.approx(z * 3.0 * np.sqrt(7.0))
    assert result.reorder_point == pytest.approx(70.0 + z * 3.0 * np.sqrt(7.0))
    assert result.days_remaining == pytest.approx(6.0)
    assert result.stockout_probability == pytest.approx(1.0 - norm.cdf((60.0 - 70.0) / (3.0 * np.sqrt(7.0))))
    assert result.reorder_quantity == pytest.approx(max(0.0, 70.0 + z * 3.0 * np.sqrt(7.0) - 60.0))
    assert result.service_level == pytest.approx(0.95)
    assert result.z_score == pytest.approx(z)
    assert result.warnings == []


def test_inventory_planning_consistency_at_rop():
    mean_demand = 10.0
    std_dev = 3.0
    lead_time_days = 7.0
    baseline = calculate_inventory_planning(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=60.0,
        lead_time_days=lead_time_days,
    )
    result = calculate_inventory_planning(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=baseline.reorder_point,
        lead_time_days=lead_time_days,
    )
    from scipy.stats import norm
    expected_stockout = 1.0 - norm.cdf(1.6448536269514722)
    assert result.stockout_probability == pytest.approx(expected_stockout)
    assert result.stockout_probability == pytest.approx(0.05, abs=1e-3)


def test_inventory_planning_zero_mean_demand():
    result = calculate_inventory_planning(
        mean_demand=0.0,
        std_dev=0.0,
        current_inventory=100.0,
        lead_time_days=7.0,
    )
    assert result.lead_time_demand == pytest.approx(0.0)
    assert result.days_remaining is None
    assert result.stockout_probability == pytest.approx(0.0)
    assert result.reorder_quantity == pytest.approx(0.0)
    assert any("Zero mean demand" in warning for warning in result.warnings)


def test_inventory_planning_zero_std_dev():
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=0.0,
        current_inventory=60.0,
        lead_time_days=7.0,
    )
    assert result.lead_time_sd == pytest.approx(0.0)
    assert result.safety_stock == pytest.approx(0.0)
    assert result.reorder_point == pytest.approx(70.0)
    assert result.stockout_probability == pytest.approx(1.0)
    assert result.reorder_quantity == pytest.approx(10.0)
    assert any("Zero demand variability" in warning for warning in result.warnings)


def test_inventory_planning_zero_std_dev_no_stockout():
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=0.0,
        current_inventory=80.0,
        lead_time_days=7.0,
    )
    assert result.stockout_probability == pytest.approx(0.0)


def test_inventory_planning_missing_inventory():
    from scipy.stats import norm
    z = float(norm.ppf(0.95))
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=None,
        lead_time_days=7.0,
    )
    assert result.lead_time_demand == pytest.approx(70.0)
    assert result.safety_stock == pytest.approx(z * 3.0 * np.sqrt(7.0))
    assert result.reorder_point == pytest.approx(70.0 + z * 3.0 * np.sqrt(7.0))
    assert result.days_remaining is None
    assert result.stockout_probability is None
    assert result.reorder_quantity is None
    assert any("Missing current inventory" in warning for warning in result.warnings)


def test_inventory_planning_invalid_lead_time_none():
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        lead_time_days=None,
    )
    assert result.lead_time_demand is None
    assert result.safety_stock is None
    assert result.reorder_point is None
    assert any("Invalid or unavailable lead time" in warning for warning in result.warnings)


def test_inventory_planning_invalid_lead_time_zero():
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        lead_time_days=0.0,
    )
    assert result.reorder_point is None
    assert any("Invalid or unavailable lead time" in warning for warning in result.warnings)


def test_inventory_planning_invalid_lead_time_negative():
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        lead_time_days=-5.0,
    )
    assert result.reorder_point is None
    assert any("Invalid or unavailable lead time" in warning for warning in result.warnings)


def test_inventory_planning_configurable_service_level():
    from scipy.stats import norm
    z = float(norm.ppf(0.90))
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=60.0,
        lead_time_days=7.0,
        service_level=0.90,
    )
    assert result.service_level == pytest.approx(0.90)
    assert result.z_score == pytest.approx(z)
    assert result.safety_stock == pytest.approx(z * 3.0 * np.sqrt(7.0))
    assert result.reorder_point == pytest.approx(70.0 + z * 3.0 * np.sqrt(7.0))


def test_inventory_planning_reorder_quantity_not_negative():
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=100.0,
        lead_time_days=7.0,
    )
    assert result.reorder_quantity == pytest.approx(0.0)
    assert result.reorder_quantity >= 0.0


def test_inventory_planning_days_remaining():
    result = calculate_inventory_planning(
        mean_demand=5.0,
        std_dev=2.0,
        current_inventory=20.0,
        lead_time_days=7.0,
    )
    assert result.days_remaining == pytest.approx(4.0)


def test_inventory_planning_missing_inventory_nan():
    result = calculate_inventory_planning(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=np.nan,
        lead_time_days=7.0,
    )
    assert result.days_remaining is None
    assert result.reorder_quantity is None
    assert any("Missing current inventory" in warning for warning in result.warnings)


def test_financial_known_values():
    from scipy.stats import norm
    z = float(norm.ppf(0.95))
    mean_demand = 10.0
    std_dev = 3.0
    lead_time_days = 7.0
    safety_stock = z * std_dev * np.sqrt(lead_time_days)
    target_stock = mean_demand * 30.0 + safety_stock

    result = calculate_financial_and_excess_metrics(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=350.0,
        unit_cost=6.0,
        selling_price=10.0,
        lead_time_days=lead_time_days,
        planning_horizon=30.0,
        units_sold=20.0,
    )
    assert result.daily_revenue == pytest.approx(200.0)
    assert result.daily_cogs == pytest.approx(120.0)
    assert result.daily_profit == pytest.approx(80.0)
    assert result.profit_per_unit == pytest.approx(4.0)
    assert result.gross_margin == pytest.approx(0.4)
    assert result.inventory_value == pytest.approx(2100.0)
    assert result.capital_tied_up == pytest.approx(2100.0)
    assert result.target_stock == pytest.approx(target_stock)
    assert result.excess_units == pytest.approx(max(0.0, 350.0 - target_stock))
    assert result.excess_inventory_value == pytest.approx(max(0.0, 350.0 - target_stock) * 6.0)
    assert result.planning_horizon == pytest.approx(30.0)
    assert result.shortage_units == pytest.approx(max(0.0, mean_demand * lead_time_days - 350.0))
    assert result.revenue_at_risk == pytest.approx(max(0.0, mean_demand * lead_time_days - 350.0) * 10.0)
    assert result.profit_at_risk == pytest.approx(max(0.0, mean_demand * lead_time_days - 350.0) * 4.0)


def test_financial_target_stock_not_rop():
    mean_demand = 10.0
    std_dev = 3.0
    lead_time_days = 7.0
    planning_horizon = 30.0

    planning = calculate_inventory_planning(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=60.0,
        lead_time_days=lead_time_days,
    )
    result = calculate_financial_and_excess_metrics(
        mean_demand=mean_demand,
        std_dev=std_dev,
        current_inventory=60.0,
        unit_cost=6.0,
        selling_price=10.0,
        lead_time_days=lead_time_days,
        planning_horizon=planning_horizon,
    )
    assert result.target_stock != planning.reorder_point
    assert result.target_stock == pytest.approx(mean_demand * planning_horizon + planning.safety_stock)
    assert planning.reorder_point == pytest.approx(mean_demand * lead_time_days + planning.safety_stock)


def test_financial_zero_revenue_margin():
    result = calculate_financial_and_excess_metrics(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=100.0,
        unit_cost=5.0,
        selling_price=0.0,
        lead_time_days=7.0,
        units_sold=10.0,
    )
    assert result.daily_revenue == pytest.approx(0.0)
    assert result.daily_profit == pytest.approx(-50.0)
    assert result.gross_margin == pytest.approx(0.0)
    assert result.profit_per_unit == pytest.approx(-5.0)


def test_financial_negative_margin_preserved():
    result = calculate_financial_and_excess_metrics(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=100.0,
        unit_cost=8.0,
        selling_price=5.0,
        lead_time_days=7.0,
        units_sold=10.0,
    )
    assert result.daily_revenue == pytest.approx(50.0)
    assert result.daily_cogs == pytest.approx(80.0)
    assert result.daily_profit == pytest.approx(-30.0)
    assert result.profit_per_unit == pytest.approx(-3.0)
    assert result.gross_margin == pytest.approx(-0.6)


def test_financial_missing_inventory():
    result = calculate_financial_and_excess_metrics(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=None,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        units_sold=10.0,
    )
    assert result.daily_revenue == pytest.approx(100.0)
    assert result.daily_cogs == pytest.approx(50.0)
    assert result.daily_profit == pytest.approx(50.0)
    assert result.inventory_value is None
    assert result.capital_tied_up is None
    assert result.excess_units is None
    assert result.excess_inventory_value is None
    assert any("Missing current inventory" in warning for warning in result.warnings)


def test_financial_zero_demand():
    result = calculate_financial_and_excess_metrics(
        mean_demand=0.0,
        std_dev=0.0,
        current_inventory=100.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        units_sold=0.0,
    )
    assert result.daily_revenue == pytest.approx(0.0)
    assert result.daily_cogs == pytest.approx(0.0)
    assert result.daily_profit == pytest.approx(0.0)
    assert result.shortage_units == pytest.approx(0.0)
    assert result.revenue_at_risk == pytest.approx(0.0)
    assert result.profit_at_risk == pytest.approx(0.0)


def test_financial_configurable_planning_horizon():
    result_30 = calculate_financial_and_excess_metrics(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=100.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        planning_horizon=30.0,
    )
    result_60 = calculate_financial_and_excess_metrics(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=100.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        planning_horizon=60.0,
    )
    assert result_30.planning_horizon == pytest.approx(30.0)
    assert result_60.planning_horizon == pytest.approx(60.0)
    assert result_60.target_stock > result_30.target_stock
    assert result_60.target_stock == pytest.approx(result_30.target_stock + 10.0 * 30.0)


def test_financial_no_units_sold():
    result = calculate_financial_and_excess_metrics(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=100.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
    )
    assert result.daily_revenue is None
    assert result.daily_cogs is None
    assert result.daily_profit is None
    assert result.gross_margin is None
    assert result.profit_per_unit == pytest.approx(5.0)
    assert result.inventory_value == pytest.approx(500.0)
    assert result.capital_tied_up == pytest.approx(500.0)


def test_financial_invalid_lead_time():
    result = calculate_financial_and_excess_metrics(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=100.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=None,
    )
    assert result.shortage_units is None
    assert result.revenue_at_risk is None
    assert result.profit_at_risk is None
    assert result.target_stock is None
    assert result.excess_units is None
    assert any("Invalid or unavailable lead time" in warning for warning in result.warnings)


def _seasonality_series(dates, values):
    return pd.Series(values, index=pd.DatetimeIndex(dates), name="demand")


def test_seasonality_known_weekday_factors():
    dates = pd.date_range("2024-01-01", periods=28, freq="D")
    values = [5.0, 10.0, 15.0, 20.0, 5.0, 10.0, 15.0] * 4
    series = _seasonality_series(dates, values)
    result = analyze_seasonality(series)
    assert result.weekday_pattern_available is True
    assert result.weekday_factors is not None
    assert result.weekday_factors[0] == pytest.approx(5.0 / 11.428571428571429)
    assert result.weekday_factors[1] == pytest.approx(10.0 / 11.428571428571429)
    assert result.weekday_factors[2] == pytest.approx(15.0 / 11.428571428571429)
    assert result.weekday_factors[3] == pytest.approx(20.0 / 11.428571428571429)
    assert result.weekday_factors[4] == pytest.approx(5.0 / 11.428571428571429)
    assert result.weekday_factors[5] == pytest.approx(10.0 / 11.428571428571429)
    assert result.weekday_factors[6] == pytest.approx(15.0 / 11.428571428571429)


def test_seasonality_known_monthly_factors():
    dates = pd.date_range("2024-01-01", periods=365, freq="D")
    values = [10.0 if d.month == 1 else 5.0 for d in dates]
    series = _seasonality_series(dates, values)
    result = analyze_seasonality(series)
    assert result.monthly_factors is not None
    jan_factor = 10.0 / ((31 * 10.0 + 334 * 5.0) / 365)
    assert result.monthly_factors[1] == pytest.approx(jan_factor)
    assert result.monthly_factors[2] == pytest.approx(5.0 / ((31 * 10.0 + 334 * 5.0) / 365))
    assert result.monthly_pattern_label == "Annual monthly seasonality"
    assert result.peak_month == "January"
    assert result.drop_month in ["February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def test_seasonality_peak_drop_identification():
    dates = pd.date_range("2024-01-01", periods=28, freq="D")
    values = [5.0, 10.0, 15.0, 20.0, 5.0, 10.0, 15.0] * 4
    series = _seasonality_series(dates, values)
    result = analyze_seasonality(series)
    assert result.peak_weekday == "Thursday"
    assert result.drop_weekday == "Monday"


def test_seasonality_insufficient_weekday_history():
    dates = pd.date_range("2024-01-01", periods=14, freq="D")
    values = [10.0] * 14
    series = _seasonality_series(dates, values)
    result = analyze_seasonality(series)
    assert result.weekday_pattern_available is False
    assert any("Insufficient history for reliable weekday pattern" in warning for warning in result.warnings)


def test_seasonality_insufficient_monthly_history():
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    values = [10.0] * 60
    series = _seasonality_series(dates, values)
    result = analyze_seasonality(series)
    assert result.monthly_pattern_label == "Observed monthly pattern"
    assert any("Short history" in warning for warning in result.warnings)


def test_seasonality_zero_demand():
    dates = pd.date_range("2024-01-01", periods=28, freq="D")
    values = [0.0] * 28
    series = _seasonality_series(dates, values)
    result = analyze_seasonality(series)
    assert result.overall_mean_demand == pytest.approx(0.0)
    assert result.weekday_factors is None
    assert result.monthly_factors is None
    assert any("Overall mean demand is zero" in warning for warning in result.warnings)


def test_seasonality_distinction_observed_vs_annual():
    dates_short = pd.date_range("2024-01-01", periods=180, freq="D")
    values_short = [10.0] * 180
    series_short = _seasonality_series(dates_short, values_short)
    result_short = analyze_seasonality(series_short)
    assert result_short.monthly_pattern_label == "Observed monthly pattern"

    dates_long = pd.date_range("2024-01-01", periods=365, freq="D")
    values_long = [10.0] * 365
    series_long = _seasonality_series(dates_long, values_long)
    result_long = analyze_seasonality(series_long)
    assert result_long.monthly_pattern_label == "Annual monthly seasonality"


def test_seasonality_missing_datetime_index():
    series = pd.Series([10.0, 20.0, 30.0])
    result = analyze_seasonality(series)
    assert result.weekday_factors is None
    assert result.monthly_factors is None
    assert any("DatetimeIndex" in warning for warning in result.warnings)


def test_seasonality_empty_series():
    series = pd.Series([], dtype=float)
    result = analyze_seasonality(series)
    assert result.overall_mean_demand is None
    assert result.weekday_factors is None
    assert result.monthly_factors is None
    assert any("No valid demand observations" in warning for warning in result.warnings)


def _risk_components(
    mean_demand=10.0,
    std_dev=3.0,
    current_inventory=60.0,
    unit_cost=5.0,
    selling_price=10.0,
    lead_time_days=7.0,
    planning_horizon=30.0,
    service_level=0.95,
    financial_reference=None,
    trend_strength=None,
    trend=None,
    cv=None,
    stockout_prob=None,
    excess_units=None,
    target_stock=None,
    reorder_point=None,
    revenue_at_risk=None,
    weekday_factors=None,
    monthly_factors=None,
    monthly_pattern_label=None,
):
    demand_stats = DemandStatistics(mean=mean_demand, std_dev=std_dev, cv=cv)
    trend_result = TrendResult(trend_strength=trend_strength, trend=trend)
    planning_result = InventoryPlanningResult(
        stockout_probability=stockout_prob,
        reorder_point=reorder_point,
    )
    financial_res = FinancialMetrics(
        excess_units=excess_units,
        target_stock=target_stock,
        revenue_at_risk=revenue_at_risk,
        planning_horizon=planning_horizon,
    )
    pattern_result = PatternResult(
        weekday_factors=weekday_factors,
        monthly_factors=monthly_factors,
        monthly_pattern_label=monthly_pattern_label,
    )
    return calculate_product_risk(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning_result,
        financial_result=financial_res,
        pattern_result=pattern_result,
        current_inventory=current_inventory,
        unit_cost=unit_cost,
        selling_price=selling_price,
        financial_reference=financial_reference,
    )


def test_risk_score_known_values():
    result = _risk_components(
        cv=0.8,
        trend_strength=0.3,
        trend="INCREASING",
        stockout_prob=0.8,
        excess_units=20.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=200.0,
        financial_reference=1000.0,
        monthly_pattern_label="Observed monthly pattern",
        monthly_factors={1: 1.5},
    )
    stockout_contrib = 0.30 * 80
    volatility_contrib = 0.20 * min(0.8 * 50, 100)
    trend_contrib = 0.15 * min(0.3 * 100, 100) * 1.0
    excess_contrib = 0.15 * min(20.0 / 100.0 * 100, 100)
    financial_contrib = 0.10 * min(200.0 / 1000.0 * 100, 100)
    seasonality_contrib = 0.10 * min(abs(1.5 - 1.0) * 100, 100)
    expected_score = stockout_contrib + volatility_contrib + trend_contrib + excess_contrib + financial_contrib + seasonality_contrib
    assert result.risk_score == pytest.approx(expected_score)
    assert result.risk_level == "MEDIUM"


def test_risk_level_low():
    result = _risk_components(
        cv=0.1,
        trend_strength=0.05,
        trend="STABLE",
        stockout_prob=0.05,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
    )
    assert result.risk_score <= 39
    assert result.risk_level == "LOW"


def test_risk_level_medium():
    result = _risk_components(
        cv=0.8,
        trend_strength=0.4,
        trend="INCREASING",
        stockout_prob=0.6,
        excess_units=20.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=200.0,
        financial_reference=1000.0,
        monthly_factors={1: 1.5},
    )
    assert 40 <= result.risk_score <= 69
    assert result.risk_level == "MEDIUM"


def test_risk_level_high():
    result = _risk_components(
        cv=1.5,
        trend_strength=0.5,
        trend="INCREASING",
        stockout_prob=0.9,
        excess_units=50.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=500.0,
        financial_reference=500.0,
        monthly_factors={1: 2.0},
    )
    assert result.risk_score >= 70
    assert result.risk_level == "HIGH"


def test_risk_financial_normalization_relative():
    result_expensive = _risk_components(
        cv=0.3,
        trend_strength=0.1,
        trend="STABLE",
        stockout_prob=0.1,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=5000.0,
        financial_reference=10000.0,
    )
    result_cheap = _risk_components(
        cv=0.3,
        trend_strength=0.1,
        trend="STABLE",
        stockout_prob=0.1,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=50.0,
        financial_reference=100.0,
    )
    assert result_expensive.component_scores.financial_exposure == pytest.approx(50.0)
    assert result_cheap.component_scores.financial_exposure == pytest.approx(50.0)
    assert result_expensive.component_scores.financial_exposure == pytest.approx(result_cheap.component_scores.financial_exposure)


def test_risk_financial_missing_reference_is_unavailable():
    result = _risk_components(
        cv=0.3,
        trend_strength=0.1,
        trend="STABLE",
        stockout_prob=0.1,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=200.0,
        financial_reference=None,
    )
    assert result.component_scores.financial_exposure is None
    assert any("Product-set financial reference unavailable" in warning for warning in result.warnings)
    assert result.available_weight_sum == pytest.approx(0.80)
    assert result.risk_score < 100


def test_risk_financial_zero_reference_is_unavailable():
    result = _risk_components(
        cv=0.3,
        trend_strength=0.1,
        trend="STABLE",
        stockout_prob=0.1,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=200.0,
        financial_reference=0.0,
    )
    assert result.component_scores.financial_exposure is None
    assert any("Product-set financial reference unavailable" in warning for warning in result.warnings)


def test_risk_high_stockout_scenario():
    result = _risk_components(
        cv=2.0,
        trend_strength=0.8,
        trend="INCREASING",
        stockout_prob=0.95,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=500.0,
        financial_reference=500.0,
        monthly_factors={1: 2.0},
    )
    assert result.component_scores.stockout_exposure == pytest.approx(95.0)
    assert result.risk_score >= 70
    assert result.risk_level == "HIGH"


def test_risk_high_volatility_scenario():
    result = _risk_components(
        cv=2.0,
        trend_strength=0.8,
        trend="INCREASING",
        stockout_prob=0.6,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=500.0,
        financial_reference=500.0,
        monthly_factors={1: 2.0},
    )
    assert result.component_scores.demand_volatility == pytest.approx(100.0)
    assert result.risk_score >= 70
    assert result.risk_level == "HIGH"


def test_risk_increasing_trend_low_inventory():
    result = _risk_components(
        cv=0.3,
        trend_strength=0.4,
        trend="INCREASING",
        stockout_prob=0.6,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
        current_inventory=50.0,
    )
    assert result.component_scores.demand_trend == pytest.approx(40.0)


def test_risk_decreasing_trend_high_inventory():
    result = _risk_components(
        cv=0.3,
        trend_strength=-0.4,
        trend="DECREASING",
        stockout_prob=0.1,
        excess_units=30.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
        current_inventory=150.0,
    )
    assert result.component_scores.demand_trend == pytest.approx(40.0)


def test_risk_excess_inventory_scenario():
    result = _risk_components(
        cv=0.2,
        trend_strength=-0.1,
        trend="DECREASING",
        stockout_prob=0.05,
        excess_units=50.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
        current_inventory=150.0,
    )
    assert result.component_scores.excess_inventory == pytest.approx(50.0)


def test_risk_seasonality_contribution():
    result = _risk_components(
        cv=0.2,
        trend_strength=0.0,
        trend="STABLE",
        stockout_prob=0.1,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
        weekday_factors={0: 1.5, 1: 0.8},
        monthly_factors={1: 2.0},
    )
    assert result.component_scores.seasonality == pytest.approx(100.0)


def test_risk_missing_stockout_data():
    result = _risk_components(
        cv=0.3,
        trend_strength=0.1,
        trend="STABLE",
        stockout_prob=None,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
    )
    assert result.component_scores.stockout_exposure is None
    assert result.available_weight_sum == pytest.approx(0.60)
    assert any("Stockout probability unavailable" in warning for warning in result.warnings)


def test_risk_missing_trend_data():
    result = _risk_components(
        cv=0.3,
        trend_strength=None,
        trend=None,
        stockout_prob=0.1,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
    )
    assert result.component_scores.demand_trend is None
    assert any("Trend unavailable" in warning for warning in result.warnings)


def test_risk_all_components_missing():
    result = _risk_components(
        cv=None,
        trend_strength=None,
        trend=None,
        stockout_prob=None,
        excess_units=None,
        target_stock=None,
        reorder_point=None,
        revenue_at_risk=None,
        financial_reference=1000.0,
    )
    assert result.risk_score is None
    assert result.risk_level is None
    assert any("No risk components available" in warning for warning in result.warnings)


def test_risk_score_clamping():
    result = _risk_components(
        cv=3.0,
        trend_strength=1.0,
        trend="INCREASING",
        stockout_prob=1.0,
        excess_units=200.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=5000.0,
        financial_reference=1000.0,
        monthly_factors={1: 3.0},
    )
    assert result.risk_score == pytest.approx(100.0)
    assert result.risk_level == "HIGH"


def test_risk_synthetic_scenario_a_stockout_emergency():
    result = _risk_components(
        mean_demand=10.0,
        std_dev=3.0,
        current_inventory=10.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=14.0,
        planning_horizon=30.0,
        service_level=0.95,
        cv=0.5,
        trend_strength=0.2,
        trend="INCREASING",
        stockout_prob=0.9,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=200.0,
        financial_reference=1000.0,
        monthly_factors={1: 2.0},
    )
    assert result.component_scores.stockout_exposure == pytest.approx(90.0)
    assert result.risk_score >= 40
    assert result.risk_level == "MEDIUM"


def test_risk_synthetic_scenario_b_overstock_emergency():
    result = _risk_components(
        mean_demand=10.0,
        std_dev=1.0,
        current_inventory=500.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=7.0,
        planning_horizon=30.0,
        service_level=0.95,
        cv=0.1,
        trend_strength=-0.3,
        trend="DECREASING",
        stockout_prob=0.0,
        excess_units=300.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
    )
    assert result.component_scores.excess_inventory == pytest.approx(100.0)
    assert result.component_scores.demand_trend == pytest.approx(30.0)
    assert result.risk_score >= 20
    assert result.risk_level == "LOW"


def test_risk_synthetic_scenario_c_expensive_but_healthy():
    result = _risk_components(
        mean_demand=10.0,
        std_dev=1.0,
        current_inventory=120.0,
        unit_cost=100.0,
        selling_price=120.0,
        lead_time_days=7.0,
        planning_horizon=30.0,
        service_level=0.95,
        cv=0.1,
        trend_strength=0.0,
        trend="STABLE",
        stockout_prob=0.05,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=10000.0,
    )
    assert result.risk_level == "LOW"


def test_risk_synthetic_scenario_d_cheap_but_chaotic():
    result = _risk_components(
        mean_demand=10.0,
        std_dev=10.0,
        current_inventory=30.0,
        unit_cost=1.0,
        selling_price=2.0,
        lead_time_days=7.0,
        planning_horizon=30.0,
        service_level=0.95,
        cv=1.0,
        trend_strength=0.0,
        trend="STABLE",
        stockout_prob=0.6,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=100.0,
        monthly_factors={1: 2.0},
    )
    assert result.component_scores.demand_volatility == pytest.approx(50.0)
    assert result.risk_score >= 20
    assert result.risk_level in ("LOW", "MEDIUM")


def test_risk_synthetic_scenario_e_growing_product():
    result = _risk_components(
        mean_demand=10.0,
        std_dev=2.0,
        current_inventory=40.0,
        unit_cost=5.0,
        selling_price=10.0,
        lead_time_days=10.0,
        planning_horizon=30.0,
        service_level=0.95,
        cv=0.2,
        trend_strength=0.4,
        trend="INCREASING",
        stockout_prob=0.7,
        excess_units=0.0,
        target_stock=100.0,
        reorder_point=80.0,
        revenue_at_risk=0.0,
        financial_reference=1000.0,
    )
    assert result.component_scores.demand_trend == pytest.approx(40.0)
    assert result.risk_score >= 30
    assert result.risk_level in ("LOW", "MEDIUM")


def test_risk_weights_are_locked_structure():
    from analysis import COMPONENT_WEIGHTS
    assert "stockout_exposure" in COMPONENT_WEIGHTS
    assert COMPONENT_WEIGHTS["stockout_exposure"] == pytest.approx(0.30)
    assert COMPONENT_WEIGHTS["demand_volatility"] == pytest.approx(0.20)
    assert COMPONENT_WEIGHTS["demand_trend"] == pytest.approx(0.15)
    assert COMPONENT_WEIGHTS["excess_inventory"] == pytest.approx(0.15)
    assert COMPONENT_WEIGHTS["financial_exposure"] == pytest.approx(0.10)
    assert COMPONENT_WEIGHTS["seasonality"] == pytest.approx(0.10)
    assert abs(sum(COMPONENT_WEIGHTS.values()) - 1.0) < 1e-9


def test_category_risk_aggregation():
    products = [
        {
            "category": "Electronics",
            "risk_score": 80.0,
            "risk_level": "HIGH",
            "inventory_value": 1000.0,
            "capital_tied_up": 1000.0,
            "shortage_units": 5.0,
            "selling_price": 10.0,
            "excess_inventory_value": 200.0,
            "cv": 0.8,
        },
        {
            "category": "Electronics",
            "risk_score": 60.0,
            "risk_level": "MEDIUM",
            "inventory_value": 500.0,
            "capital_tied_up": 500.0,
            "shortage_units": 2.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.5,
        },
        {
            "category": "Clothing",
            "risk_score": 20.0,
            "risk_level": "LOW",
            "inventory_value": 300.0,
            "capital_tied_up": 300.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 50.0,
            "cv": 0.2,
        },
    ]
    results = calculate_category_risk(products, total_inventory_value=1800.0)
    assert "Electronics" in results
    assert "Clothing" in results

    electronics = results["Electronics"]
    assert electronics.product_count == 2
    assert electronics.high_risk_product_count == 1
    assert electronics.average_product_risk_score == pytest.approx(70.0)
    assert electronics.category_inventory_value == pytest.approx(1500.0)
    assert electronics.category_capital_tied_up == pytest.approx(1500.0)
    assert electronics.category_stockout_exposure == pytest.approx(70.0)
    assert electronics.category_excess_inventory_value == pytest.approx(200.0)
    assert electronics.category_demand_volatility == pytest.approx(0.65)

    clothing = results["Clothing"]
    assert clothing.product_count == 1
    assert clothing.high_risk_product_count == 0
    assert clothing.average_product_risk_score == pytest.approx(20.0)
    assert clothing.category_inventory_value == pytest.approx(300.0)
    assert clothing.category_excess_inventory_value == pytest.approx(50.0)


def test_category_risk_scoring_known_values():
    products = [
        {
            "category": "A",
            "risk_score": 50.0,
            "risk_level": "MEDIUM",
            "inventory_value": 500.0,
            "capital_tied_up": 500.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.5,
        },
        {
            "category": "A",
            "risk_score": 70.0,
            "risk_level": "HIGH",
            "inventory_value": 500.0,
            "capital_tied_up": 500.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.8,
        },
    ]
    results = calculate_category_risk(products, total_inventory_value=1000.0)
    category_a = results["A"]
    assert category_a.average_product_risk_score == pytest.approx(60.0)
    financial_ratio = 1000.0 / 1000.0
    financial_score = min(financial_ratio * 100, 100)
    high_risk_ratio = 1 / 2
    high_risk_score = min(high_risk_ratio * 200, 100)
    expected_category_score = 0.70 * 60.0 + 0.15 * financial_score + 0.15 * high_risk_score
    assert category_a.risk_score == pytest.approx(expected_category_score)
    assert category_a.risk_level == "HIGH"


def test_category_risk_high_risk_product_count():
    products = [
        {
            "category": "A",
            "risk_score": 80.0,
            "risk_level": "HIGH",
            "inventory_value": 100.0,
            "capital_tied_up": 100.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.5,
        },
        {
            "category": "A",
            "risk_score": 80.0,
            "risk_level": "HIGH",
            "inventory_value": 100.0,
            "capital_tied_up": 100.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.5,
        },
        {
            "category": "A",
            "risk_score": 20.0,
            "risk_level": "LOW",
            "inventory_value": 100.0,
            "capital_tied_up": 100.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.2,
        },
    ]
    results = calculate_category_risk(products)
    assert results["A"].high_risk_product_count == 2
    assert results["A"].product_count == 3


def test_category_risk_stockout_and_excess_exposure():
    products = [
        {
            "category": "A",
            "risk_score": 50.0,
            "risk_level": "MEDIUM",
            "inventory_value": 100.0,
            "capital_tied_up": 100.0,
            "shortage_units": 5.0,
            "selling_price": 10.0,
            "excess_inventory_value": 50.0,
            "cv": 0.5,
        },
        {
            "category": "A",
            "risk_score": 50.0,
            "risk_level": "MEDIUM",
            "inventory_value": 100.0,
            "capital_tied_up": 100.0,
            "shortage_units": 3.0,
            "selling_price": 10.0,
            "excess_inventory_value": 20.0,
            "cv": 0.5,
        },
    ]
    results = calculate_category_risk(products)
    assert results["A"].category_stockout_exposure == pytest.approx(80.0)
    assert results["A"].category_excess_inventory_value == pytest.approx(70.0)


def test_category_risk_different_financial_magnitudes():
    products = [
        {
            "category": "Expensive",
            "risk_score": 30.0,
            "risk_level": "LOW",
            "inventory_value": 10000.0,
            "capital_tied_up": 10000.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.3,
        },
        {
            "category": "Cheap",
            "risk_score": 30.0,
            "risk_level": "LOW",
            "inventory_value": 100.0,
            "capital_tied_up": 100.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.3,
        },
    ]
    results = calculate_category_risk(products, total_inventory_value=10100.0)
    expensive = results["Expensive"]
    cheap = results["Cheap"]
    assert expensive.average_product_risk_score == pytest.approx(30.0)
    assert cheap.average_product_risk_score == pytest.approx(30.0)
    assert expensive.category_inventory_value == pytest.approx(10000.0)
    assert cheap.category_inventory_value == pytest.approx(100.0)
    assert expensive.risk_score > cheap.risk_score


def test_category_missing_insufficient_data():
    products = [
        {
            "category": "A",
            "risk_score": None,
            "risk_level": None,
            "inventory_value": None,
            "capital_tied_up": None,
            "shortage_units": None,
            "selling_price": None,
            "excess_inventory_value": None,
            "cv": None,
        },
    ]
    results = calculate_category_risk(products)
    assert results["A"].risk_score is None
    assert results["A"].risk_level is None
    assert any("No valid product risk scores" in warning for warning in results["A"].warnings)


def test_overall_health_aggregation():
    categories = {
        "Electronics": CategoryRiskResult(
            category="Electronics",
            risk_score=70.0,
            risk_level="HIGH",
            product_count=5,
            high_risk_product_count=2,
            category_stockout_exposure=500.0,
            category_excess_inventory_value=100.0,
            category_capital_tied_up=2000.0,
        ),
        "Clothing": CategoryRiskResult(
            category="Clothing",
            risk_score=30.0,
            risk_level="LOW",
            product_count=3,
            high_risk_product_count=0,
            category_stockout_exposure=0.0,
            category_excess_inventory_value=50.0,
            category_capital_tied_up=500.0,
        ),
    }
    products = [
        {"risk_level": "HIGH", "revenue_at_risk": 300.0, "profit_at_risk": 100.0},
        {"risk_level": "HIGH", "revenue_at_risk": 200.0, "profit_at_risk": 50.0},
        {"risk_level": "MEDIUM", "revenue_at_risk": 0.0, "profit_at_risk": 0.0},
        {"risk_level": "LOW", "revenue_at_risk": 0.0, "profit_at_risk": 0.0},
        {"risk_level": "LOW", "revenue_at_risk": 0.0, "profit_at_risk": 0.0},
        {"risk_level": "LOW", "revenue_at_risk": 0.0, "profit_at_risk": 0.0},
        {"risk_level": "LOW", "revenue_at_risk": 0.0, "profit_at_risk": 0.0},
        {"risk_level": "LOW", "revenue_at_risk": 0.0, "profit_at_risk": 0.0},
    ]
    result = calculate_overall_health(categories, products)
    assert result.overall_risk_score == pytest.approx(50.0)
    assert result.overall_health_status == "ATTENTION"
    assert result.total_products == 8
    assert result.products_at_risk == 3
    assert result.total_categories == 2
    assert result.high_risk_categories == 1
    assert result.total_stockout_exposure == pytest.approx(500.0)
    assert result.total_excess_inventory_value == pytest.approx(150.0)
    assert result.total_capital_tied_up == pytest.approx(2500.0)
    assert result.total_revenue_at_risk == pytest.approx(500.0)
    assert result.total_profit_at_risk == pytest.approx(150.0)


def test_overall_health_empty_data():
    result = calculate_overall_health({}, [])
    assert result.overall_risk_score is None
    assert result.overall_health_status is None
    assert result.total_products == 0
    assert result.products_at_risk == 0
    assert any("No category or product data" in warning for warning in result.warnings)


def test_overall_health_no_stockout_or_excess():
    categories = {
        "A": CategoryRiskResult(
            category="A",
            risk_score=30.0,
            risk_level="LOW",
            product_count=2,
            high_risk_product_count=0,
            category_stockout_exposure=0.0,
            category_excess_inventory_value=0.0,
            category_capital_tied_up=100.0,
        ),
    }
    products = [
        {"risk_level": "LOW", "revenue_at_risk": 0.0, "profit_at_risk": 0.0},
        {"risk_level": "LOW", "revenue_at_risk": 0.0, "profit_at_risk": 0.0},
    ]
    result = calculate_overall_health(categories, products)
    assert result.overall_risk_score == pytest.approx(30.0)
    assert result.overall_health_status == "HEALTHY"
    assert result.total_stockout_exposure is None
    assert result.total_excess_inventory_value is None
    assert result.total_capital_tied_up == pytest.approx(100.0)


def test_overall_health_all_high_risk():
    categories = {
        "A": CategoryRiskResult(
            category="A",
            risk_score=85.0,
            risk_level="HIGH",
            product_count=3,
            high_risk_product_count=3,
            category_stockout_exposure=100.0,
            category_excess_inventory_value=0.0,
            category_capital_tied_up=500.0,
        ),
    }
    products = [
        {"risk_level": "HIGH", "revenue_at_risk": 100.0, "profit_at_risk": 30.0},
        {"risk_level": "HIGH", "revenue_at_risk": 100.0, "profit_at_risk": 30.0},
        {"risk_level": "HIGH", "revenue_at_risk": 100.0, "profit_at_risk": 30.0},
    ]
    result = calculate_overall_health(categories, products)
    assert result.overall_risk_score == pytest.approx(85.0)
    assert result.overall_health_status == "CRITICAL"
    assert result.products_at_risk == 3
    assert result.high_risk_categories == 1


def test_consistency_product_category_overall():
    products = [
        {
            "category": "A",
            "risk_score": 80.0,
            "risk_level": "HIGH",
            "inventory_value": 1000.0,
            "capital_tied_up": 1000.0,
            "shortage_units": 10.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 1.0,
        },
        {
            "category": "A",
            "risk_score": 60.0,
            "risk_level": "MEDIUM",
            "inventory_value": 500.0,
            "capital_tied_up": 500.0,
            "shortage_units": 5.0,
            "selling_price": 10.0,
            "excess_inventory_value": 100.0,
            "cv": 0.5,
        },
        {
            "category": "B",
            "risk_score": 20.0,
            "risk_level": "LOW",
            "inventory_value": 200.0,
            "capital_tied_up": 200.0,
            "shortage_units": 0.0,
            "selling_price": 10.0,
            "excess_inventory_value": 0.0,
            "cv": 0.2,
        },
    ]
    category_results = calculate_category_risk(products, total_inventory_value=1700.0)
    overall = calculate_overall_health(category_results, products)

    assert overall.total_products == 3
    assert overall.products_at_risk == 2
    assert overall.total_categories == 2
    assert overall.high_risk_categories == 1
    assert overall.total_stockout_exposure == pytest.approx(150.0)
    assert overall.total_excess_inventory_value == pytest.approx(100.0)
    assert overall.total_capital_tied_up == pytest.approx(1700.0)

    category_a = category_results["A"]
    category_b = category_results["B"]
    assert category_a.risk_level == "HIGH"
    assert category_b.risk_level == "LOW"
    assert overall.overall_health_status == "ATTENTION"

