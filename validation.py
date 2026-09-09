"""Data validation and schema checks for InventoryIQ V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

REQUIRED_COLUMNS = [
    "date",
    "product",
    "category",
    "inventory",
    "units_sold",
    "unit_cost",
    "selling_price",
    "supplier",
    "lead_time_days",
]

NUMERIC_COLUMNS = [
    "inventory",
    "units_sold",
    "unit_cost",
    "selling_price",
    "lead_time_days",
]


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    df: Optional[pd.DataFrame] = None


def validate_input(df: pd.DataFrame) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")
        return ValidationResult(is_valid=False, errors=errors)

    parsed_dates = pd.to_datetime(df["date"], errors="coerce")
    invalid_date_mask = parsed_dates.isna() & df["date"].notna()
    if invalid_date_mask.any():
        errors.append(
            f"Invalid date values found: {int(invalid_date_mask.sum())} row(s)"
        )

    for column in NUMERIC_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[column]):
            errors.append(f"Column '{column}' must be numeric")

    if errors:
        return ValidationResult(is_valid=False, errors=errors, df=df)

    for column in ["inventory", "units_sold", "unit_cost", "selling_price"]:
        if (df[column] < 0).any():
            errors.append(f"Column '{column}' contains negative values")

    if (df["lead_time_days"] <= 0).any():
        errors.append("Column 'lead_time_days' must be positive")

    duplicate_mask = df.duplicated(subset=["product", "date"], keep=False)
    if duplicate_mask.any():
        warnings.append(
            f"Ambiguous duplicate product/date records: {int(duplicate_mask.sum())} row(s)"
        )

    missing_inventory_mask = df["inventory"].isna()
    if missing_inventory_mask.any():
        warnings.append(
            f"Missing inventory values found: {int(missing_inventory_mask.sum())} row(s). "
            "These remain missing/unavailable and must not be treated as zero."
        )

    for column in ["product", "category", "supplier", "unit_cost", "selling_price", "lead_time_days"]:
        if df[column].isna().any():
            errors.append(f"Column '{column}' contains missing values")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        df=df,
    )
