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
