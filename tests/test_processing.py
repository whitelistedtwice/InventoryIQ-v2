import pandas as pd
import pytest

from data_processing import process_data, REQUIRED_DERIVED_COLUMNS


def _base_df():
    return pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "product": ["A", "A", "A"],
            "category": ["Cat1", "Cat1", "Cat1"],
            "inventory": [100.0, 120.0, 80.0],
            "units_sold": [10.0, 15.0, 20.0],
            "unit_cost": [5.0, 5.0, 5.0],
            "selling_price": [10.0, 10.0, 10.0],
            "supplier": ["Sup1", "Sup1", "Sup1"],
            "lead_time_days": [7.0, 7.0, 7.0],
        }
    )


def test_process_valid_data():
    result = process_data(_base_df())
    assert isinstance(result, pd.DataFrame)
    for column in REQUIRED_DERIVED_COLUMNS:
        assert column in result.columns


def test_receiving_stock_inventory_change_is_not_demand():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "product": ["A", "A"],
            "category": ["Cat1", "Cat1"],
            "inventory": [100.0, 150.0],
            "units_sold": [10.0, 5.0],
            "unit_cost": [5.0, 5.0],
            "selling_price": [10.0, 10.0],
            "supplier": ["Sup1", "Sup1"],
            "lead_time_days": [7.0, 7.0],
        }
    )
    result = process_data(df)
    row = result.iloc[1]
    assert row["inventory_change"] == 50.0
    assert row["units_sold"] == 5.0
    assert row["sales_velocity"] == 5.0
    assert row["inventory_change"] != row["units_sold"]


def test_zero_sales_preserved():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["A"],
            "category": ["Cat1"],
            "inventory": [100.0],
            "units_sold": [0.0],
            "unit_cost": [5.0],
            "selling_price": [10.0],
            "supplier": ["Sup1"],
            "lead_time_days": [7.0],
        }
    )
    result = process_data(df)
    row = result.iloc[0]
    assert row["units_sold"] == 0.0
    assert row["sales_velocity"] == 0.0
    assert row["daily_revenue"] == 0.0
    assert row["daily_profit"] == 0.0


def test_zero_selling_price():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["A"],
            "category": ["Cat1"],
            "inventory": [100.0],
            "units_sold": [10.0],
            "unit_cost": [5.0],
            "selling_price": [0.0],
            "supplier": ["Sup1"],
            "lead_time_days": [7.0],
        }
    )
    result = process_data(df)
    row = result.iloc[0]
    assert row["daily_revenue"] == 0.0
    assert row["daily_profit"] == -50.0
    assert row["profit_margin"] == 0.0


def test_negative_margin():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["A"],
            "category": ["Cat1"],
            "inventory": [100.0],
            "units_sold": [10.0],
            "unit_cost": [8.0],
            "selling_price": [10.0],
            "supplier": ["Sup1"],
            "lead_time_days": [7.0],
        }
    )
    result = process_data(df)
    row = result.iloc[0]
    assert row["daily_revenue"] == 100.0
    assert row["daily_profit"] == 20.0
    assert row["profit_margin"] == 0.2


def test_missing_inventory_preserved():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "product": ["A", "A"],
            "category": ["Cat1", "Cat1"],
            "inventory": [100.0, None],
            "units_sold": [10.0, 5.0],
            "unit_cost": [5.0, 5.0],
            "selling_price": [10.0, 10.0],
            "supplier": ["Sup1", "Sup1"],
            "lead_time_days": [7.0, 7.0],
        }
    )
    result = process_data(df)
    assert pd.isna(result.iloc[1]["inventory"])
    assert pd.isna(result.iloc[1]["inventory_value"])
    assert pd.isna(result.iloc[1]["inventory_change"])


def test_daily_aggregation_of_duplicates():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-01"],
            "product": ["A", "A"],
            "category": ["Cat1", "Cat1"],
            "inventory": [100.0, 100.0],
            "units_sold": [5.0, 5.0],
            "unit_cost": [5.0, 5.0],
            "selling_price": [10.0, 10.0],
            "supplier": ["Sup1", "Sup1"],
            "lead_time_days": [7.0, 7.0],
        }
    )
    result = process_data(df)
    assert len(result) == 1
    assert result.iloc[0]["units_sold"] == 10.0
    assert result.iloc[0]["inventory"] == 100.0


def test_inventory_change_first_day_is_nan():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["A"],
            "category": ["Cat1"],
            "inventory": [100.0],
            "units_sold": [10.0],
            "unit_cost": [5.0],
            "selling_price": [10.0],
            "supplier": ["Sup1"],
            "lead_time_days": [7.0],
        }
    )
    result = process_data(df)
    assert pd.isna(result.iloc[0]["inventory_change"])


def test_multiple_products_sorted_correctly():
    df = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-01", "2024-01-02", "2024-01-01"],
            "product": ["B", "B", "A", "A"],
            "category": ["Cat2", "Cat2", "Cat1", "Cat1"],
            "inventory": [50.0, 60.0, 100.0, 110.0],
            "units_sold": [5.0, 6.0, 10.0, 11.0],
            "unit_cost": [5.0, 5.0, 5.0, 5.0],
            "selling_price": [10.0, 10.0, 10.0, 10.0],
            "supplier": ["Sup1", "Sup1", "Sup1", "Sup1"],
            "lead_time_days": [7.0, 7.0, 7.0, 7.0],
        }
    )
    result = process_data(df)
    products = result["product"].tolist()
    assert products == ["A", "A", "B", "B"]
    dates = result["date"].tolist()
    assert dates == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")] * 2
