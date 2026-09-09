"""Data cleaning, date handling, aggregation and derived variables."""

from __future__ import annotations

import pandas as pd

REQUIRED_DERIVED_COLUMNS = [
    "daily_revenue",
    "daily_profit",
    "inventory_value",
    "inventory_change",
    "sales_velocity",
    "profit_margin",
]


def process_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.sort_values(["product", "date"]).reset_index(drop=True)

    aggregated = (
        df.groupby(["product", "date"], as_index=False)
        .agg(
            {
                "category": "last",
                "inventory": "last",
                "units_sold": "sum",
                "unit_cost": "last",
                "selling_price": "last",
                "supplier": "last",
                "lead_time_days": "last",
            }
        )
        .sort_values(["product", "date"])
        .reset_index(drop=True)
    )

    aggregated["daily_revenue"] = aggregated["units_sold"] * aggregated["selling_price"]
    aggregated["daily_profit"] = aggregated["units_sold"] * (
        aggregated["selling_price"] - aggregated["unit_cost"]
    )
    aggregated["inventory_value"] = aggregated["inventory"] * aggregated["unit_cost"]

    aggregated["opening_inventory"] = aggregated.groupby("product")["inventory"].shift(1)
    aggregated["inventory_change"] = (
        aggregated["inventory"] - aggregated["opening_inventory"]
    )

    aggregated["sales_velocity"] = aggregated["units_sold"]

    aggregated["profit_margin"] = 0.0
    revenue_mask = aggregated["daily_revenue"] > 0
    aggregated.loc[revenue_mask, "profit_margin"] = (
        aggregated.loc[revenue_mask, "daily_profit"]
        / aggregated.loc[revenue_mask, "daily_revenue"]
    )

    return aggregated
