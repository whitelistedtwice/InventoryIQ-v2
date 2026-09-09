import numpy as np
import pandas as pd
import pytest

from analysis import (
    DemandStatistics,
    TrendResult,
    OutlierResult,
    calculate_demand_statistics,
    calculate_trend,
    detect_outliers,
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
