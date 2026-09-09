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
