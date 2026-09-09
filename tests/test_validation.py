import pandas as pd
import pytest

from validation import ValidationResult, validate_input


def _valid_df():
    return pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "product": ["A", "A"],
            "category": ["Cat1", "Cat1"],
            "inventory": [100.0, 90.0],
            "units_sold": [10.0, 0.0],
            "unit_cost": [5.0, 5.0],
            "selling_price": [10.0, 10.0],
            "supplier": ["Sup1", "Sup1"],
            "lead_time_days": [7.0, 7.0],
        }
    )


def test_valid_data():
    result = validate_input(_valid_df())
    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []
    assert result.df is not None


def test_missing_columns():
    df = _valid_df().drop(columns=["lead_time_days"])
    result = validate_input(df)
    assert result.is_valid is False
    assert any("Missing required columns" in error for error in result.errors)


def test_invalid_dates():
    df = _valid_df()
    df.loc[0, "date"] = "not-a-date"
    result = validate_input(df)
    assert result.is_valid is False
    assert any("Invalid date values" in error for error in result.errors)


def test_invalid_numbers():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["A"],
            "category": ["Cat1"],
            "inventory": ["not-a-number"],
            "units_sold": [10.0],
            "unit_cost": [5.0],
            "selling_price": [10.0],
            "supplier": ["Sup1"],
            "lead_time_days": [7.0],
        }
    )
    result = validate_input(df)
    assert result.is_valid is False
    assert any("must be numeric" in error for error in result.errors)


def test_invalid_lead_time_zero():
    df = _valid_df()
    df.loc[0, "lead_time_days"] = 0
    result = validate_input(df)
    assert result.is_valid is False
    assert any("lead_time_days" in error and "positive" in error for error in result.errors)


def test_invalid_lead_time_negative():
    df = _valid_df()
    df.loc[0, "lead_time_days"] = -3
    result = validate_input(df)
    assert result.is_valid is False
    assert any("lead_time_days" in error and "positive" in error for error in result.errors)


def test_duplicate_product_date():
    df = pd.concat([_valid_df(), _valid_df().iloc[[0]]], ignore_index=True)
    result = validate_input(df)
    assert result.is_valid is True
    assert any("duplicate product/date" in warning.lower() for warning in result.warnings)


def test_missing_inventory_not_zero():
    df = _valid_df()
    df.loc[0, "inventory"] = None
    result = validate_input(df)
    assert result.is_valid is True
    assert any("Missing inventory" in warning for warning in result.warnings)
    assert pd.isna(result.df.loc[0, "inventory"])
    assert result.df.loc[0, "inventory"] != 0


def test_zero_sales_preserved():
    df = _valid_df()
    df.loc[0, "units_sold"] = 0
    result = validate_input(df)
    assert result.is_valid is True
    assert result.df.loc[0, "units_sold"] == 0


def test_negative_inventory():
    df = _valid_df()
    df.loc[0, "inventory"] = -10
    result = validate_input(df)
    assert result.is_valid is False
    assert any("inventory" in error and "negative" in error for error in result.errors)


def test_missing_values_in_required_fields():
    df = _valid_df()
    df.loc[0, "product"] = None
    result = validate_input(df)
    assert result.is_valid is False
    assert any("product" in error and "missing values" in error for error in result.errors)
