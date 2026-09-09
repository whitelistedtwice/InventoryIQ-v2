import numpy as np
import pandas as pd
import pytest

from analysis import (
    DemandStatistics,
    TrendResult,
    OutlierResult,
    InventoryPlanningResult,
    calculate_demand_statistics,
    calculate_trend,
    detect_outliers,
    calculate_inventory_planning,
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

