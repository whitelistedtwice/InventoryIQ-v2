import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from analysis import (
    OverallHealthResult,
    analyze_seasonality,
    calculate_category_risk,
    calculate_demand_statistics,
    calculate_financial_and_excess_metrics,
    calculate_inventory_planning,
    calculate_overall_health,
    calculate_product_risk,
    calculate_trend,
    detect_outliers,
)
from gemini import ExecutiveSummaryRequest, ProductContext, get_executive_summary, get_product_explanation
from gemini_config import is_gemini_configured
from recommendation import RecommendationResult, generate_recommendation
from scenario import run_scenario
from validation import validate_input

st.set_page_config(
    page_title="InventoryIQ V2",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_DATE_RANGE_DAYS = 90
MAX_PRODUCTS_FOR_AI = 10
PRIORITY_ACTION_COLORS = {
    "REORDER": "#dc2626",
    "HOLD": "#f59e0b",
    "REDUCE": "#ef4444",
    "MONITOR": "#3b82f6",
    "NO_ACTION": "#10b981",
    "UNAVAILABLE": "#6b7280",
}
PRIORITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "NONE": 4,
}


@st.cache_resource
def _load_sample_data() -> pd.DataFrame:
    sample_path = os.path.join(os.path.dirname(__file__), "test_data", "healthy_inventory.csv")
    if os.path.exists(sample_path):
        return pd.read_csv(sample_path)
    return pd.DataFrame()


@st.cache_resource
def _load_mock_data() -> pd.DataFrame:
    import random
    from datetime import datetime as dt

    random.seed(42)
    base_date = dt(2025, 1, 1)
    rows = []

    products = [
        {
            "product": "Widget A",
            "category": "Electronics",
            "inventory": 40,
            "units_sold_base": 25,
            "unit_cost": 10.0,
            "selling_price": 20.0,
            "supplier": "Supplier X",
            "lead_time_days": 14,
        },
        {
            "product": "Widget B",
            "category": "Electronics",
            "inventory": 500,
            "units_sold_base": 5,
            "unit_cost": 8.0,
            "selling_price": 15.0,
            "supplier": "Supplier Y",
            "lead_time_days": 7,
        },
        {
            "product": "Widget C",
            "category": "General",
            "inventory": 120,
            "units_sold_base": 10,
            "unit_cost": 5.0,
            "selling_price": 10.0,
            "supplier": "Supplier Z",
            "lead_time_days": 7,
        },
        {
            "product": "Widget D",
            "category": "General",
            "inventory": 200,
            "units_sold_base": 0,
            "unit_cost": 6.0,
            "selling_price": 12.0,
            "supplier": "Supplier X",
            "lead_time_days": 7,
        },
        {
            "product": "Widget E",
            "category": "General",
            "inventory": 80,
            "units_sold_base": 10,
            "unit_cost": 7.0,
            "selling_price": 14.0,
            "supplier": "Supplier Y",
            "lead_time_days": 10,
        },
    ]

    for i in range(15):
        date = base_date + timedelta(days=i)
        for p in products:
            if p["product"] == "Widget E":
                units_sold = max(0, int(random.gauss(p["units_sold_base"], 8)))
            else:
                units_sold = max(0, int(random.gauss(p["units_sold_base"], 2)))
            rows.append({
                "id": len(rows) + 1,
                "date": date.strftime("%Y-%m-%d"),
                "product": p["product"],
                "category": p["category"],
                "inventory": p["inventory"],
                "units_sold": units_sold,
                "unit_cost": p["unit_cost"],
                "selling_price": p["selling_price"],
                "supplier": p["supplier"],
                "lead_time_days": p["lead_time_days"],
            })

    return pd.DataFrame(rows)


def _safe_float(value: Optional[float]) -> Optional[float]:
    if value is None or (isinstance(value, float) and (value != value)):
        return None
    return float(value)


def _format_currency(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def _format_percent(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1%}"


def _format_delta(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return f"{value:+.1f}"


def _init_session_state() -> None:
    defaults = {
        "raw_df": pd.DataFrame(),
        "processed_df": pd.DataFrame(),
        "validation_result": None,
        "products": [],
        "selected_product": None,
        "scenario_assumptions": None,
        "scenario_result": None,
        "ai_brief": None,
        "ai_brief_error": None,
        "navigate_to": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _apply_filters(df: pd.DataFrame, date_range: Tuple[datetime, datetime], categories: List[str], product_search: str) -> pd.DataFrame:
    filtered = df.copy()
    if "date" in filtered.columns:
        filtered["date"] = pd.to_datetime(filtered["date"], errors="coerce")
        filtered = filtered.dropna(subset=["date"])
        if len(date_range) == 2:
            start, end = date_range
            filtered = filtered[(filtered["date"] >= pd.Timestamp(start)) & (filtered["date"] <= pd.Timestamp(end))]
    if categories and "category" in filtered.columns:
        filtered = filtered[filtered["category"].isin(categories)]
    if product_search and "product" in filtered.columns:
        search_lower = product_search.lower()
        filtered = filtered[filtered["product"].str.lower().str.contains(search_lower, na=False)]
    return filtered


def _build_product_result(row: pd.Series, demand_stats: Any, trend_result: Any, planning: Any, financial: Any, pattern: Any) -> Dict[str, Any]:
    risk = calculate_product_risk(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning,
        financial_result=financial,
        pattern_result=pattern,
        current_inventory=_safe_float(row.get("inventory")),
        unit_cost=_safe_float(row.get("unit_cost")) or 0.0,
        selling_price=_safe_float(row.get("selling_price")) or 0.0,
    )
    recommendation = generate_recommendation(
        demand_stats=demand_stats,
        trend_result=trend_result,
        planning_result=planning,
        financial_result=financial,
        pattern_result=pattern,
        risk_result=risk,
        current_inventory=_safe_float(row.get("inventory")),
        unit_cost=_safe_float(row.get("unit_cost")) or 0.0,
        lead_time_days=_safe_float(row.get("lead_time_days")),
    )
    return {
        "product": row.get("product"),
        "category": row.get("category"),
        "current_inventory": _safe_float(row.get("inventory")),
        "unit_cost": _safe_float(row.get("unit_cost")),
        "selling_price": _safe_float(row.get("selling_price")),
        "lead_time_days": _safe_float(row.get("lead_time_days")),
        "demand_stats": demand_stats,
        "trend_result": trend_result,
        "planning": planning,
        "financial": financial,
        "pattern": pattern,
        "risk": risk,
        "recommendation": recommendation,
    }


def _run_pipeline(df: pd.DataFrame) -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    if df.empty or "product" not in df.columns:
        return products
    for product_name, group in df.groupby("product"):
        last_row = group.iloc[-1]
        demand_series = group["units_sold"].fillna(0)
        demand_stats = calculate_demand_statistics(demand_series)
        trend_result = calculate_trend(demand_series)
        outlier_result = detect_outliers(demand_series)
        pattern_result = analyze_seasonality(demand_series)
        mean_demand = _safe_float(demand_stats.mean) or 0.0
        std_dev = _safe_float(demand_stats.std_dev) or 0.0
        current_inventory = _safe_float(last_row.get("inventory"))
        lead_time_days = _safe_float(last_row.get("lead_time_days"))
        unit_cost = _safe_float(last_row.get("unit_cost")) or 0.0
        selling_price = _safe_float(last_row.get("selling_price")) or 0.0
        planning = calculate_inventory_planning(
            mean_demand=mean_demand,
            std_dev=std_dev,
            current_inventory=current_inventory,
            lead_time_days=lead_time_days,
        )
        financial = calculate_financial_and_excess_metrics(
            mean_demand=mean_demand,
            std_dev=std_dev,
            current_inventory=current_inventory,
            unit_cost=unit_cost,
            selling_price=selling_price,
            lead_time_days=lead_time_days,
        )
        product = _build_product_result(last_row, demand_stats, trend_result, planning, financial, pattern_result)
        product["outlier_result"] = outlier_result
        outlier_dates = []
        if outlier_result.outlier_mask is not None:
            outlier_indices = outlier_result.outlier_mask[outlier_result.outlier_mask].index
            outlier_dates = pd.to_datetime(group.loc[outlier_indices, "date"]).dt.strftime("%Y-%m-%d").tolist()
        product["outlier_dates"] = outlier_dates
        product["inventory_history"] = list(zip(
            pd.to_datetime(group["date"]).dt.strftime("%Y-%m-%d").tolist(),
            group["inventory"].fillna(0).tolist(),
        ))
        product["demand_history"] = list(zip(
            pd.to_datetime(group["date"]).dt.strftime("%Y-%m-%d").tolist(),
            demand_series.tolist(),
        ))
        products.append(product)
    return products


def _render_kpi_card(title: str, value: str, subtitle: str = "", delta: Optional[str] = None) -> None:
    st.metric(label=title, value=value, delta=delta, help=subtitle)


def _render_inventory_health(products: List[Dict[str, Any]]) -> None:
    st.subheader("Inventory Health")
    if not products:
        st.info("No product data available for the current filters.")
        return
    category_results = calculate_category_risk(
        [
            {
                "category": p["category"],
                "risk_score": _safe_float(p["risk"].risk_score),
                "risk_level": p["risk"].risk_level,
                "inventory_value": _safe_float(p["financial"].inventory_value),
                "capital_tied_up": _safe_float(p["financial"].capital_tied_up),
                "shortage_units": max(0.0, _safe_float(p["planning"].lead_time_demand) - _safe_float(p["current_inventory"])) if _safe_float(p["planning"].lead_time_demand) is not None and _safe_float(p["current_inventory"]) is not None else None,
                "selling_price": _safe_float(p["selling_price"]),
                "excess_inventory_value": _safe_float(p["financial"].excess_inventory_value),
                "cv": _safe_float(p["demand_stats"].cv),
            }
            for p in products
            if p["risk"].risk_score is not None
        ]
    )
    overall = calculate_overall_health(category_results, [
        {
            "risk_score": _safe_float(p["risk"].risk_score),
            "risk_level": p["risk"].risk_level,
            "revenue_at_risk": _safe_float(p["financial"].revenue_at_risk),
            "profit_at_risk": _safe_float(p["financial"].profit_at_risk),
        }
        for p in products
    ])
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        health_status = overall.overall_health_status or "N/A"
        st.metric("Overall Health", health_status, help="Aggregated inventory health status")
    with col2:
        products_at_risk = overall.products_at_risk
        total = overall.total_products
        st.metric("Products at Risk", f"{products_at_risk} / {total}")
    with col3:
        stockout = overall.total_stockout_exposure
        st.metric("Estimated Stockout Exposure", _format_currency(stockout))
    with col4:
        excess = overall.total_excess_inventory_value
        st.metric("Estimated Excess Inventory", _format_currency(excess))
    col5, col6 = st.columns(2)
    with col5:
        capital = overall.total_capital_tied_up
        st.metric("Capital Tied Up", _format_currency(capital))
    with col6:
        revenue = overall.total_revenue_at_risk
        profit = overall.total_profit_at_risk
        st.metric("Estimated Revenue / Profit Risk", f"{_format_currency(revenue)} / {_format_currency(profit)}")


def _render_top_priorities(products: List[Dict[str, Any]]) -> None:
    st.subheader("Top Priorities")
    if not products:
        st.info("No recommendations available.")
        return
    prioritized = []
    for p in products:
        rec = p["recommendation"]
        if rec.action == "UNAVAILABLE":
            continue
        prioritized.append({
            "product": p["product"],
            "category": p["category"],
            "action": rec.action,
            "priority": rec.priority,
            "reasons": rec.reasons,
            "evidence": rec.evidence,
            "reorder_quantity": rec.reorder_quantity,
            "risk_score": _safe_float(p["risk"].risk_score),
            "risk_level": p["risk"].risk_level,
        })
    prioritized.sort(key=lambda x: (PRIORITY_ORDER.get(x["priority"], 99), -(x["risk_score"] or 0)))
    if not prioritized:
        st.info("All products are healthy or data is insufficient for recommendations.")
        return
    for idx, item in enumerate(prioritized[:10], 1):
        action_color = PRIORITY_ACTION_COLORS.get(item["action"], "#6b7280")
        with st.container():
            col_header, col_body, col_meta = st.columns([1, 3, 2])
            with col_header:
                st.markdown(f"<span style='color:{action_color}; font-weight:bold; font-size:1.1rem;'>{item['action']}</span>", unsafe_allow_html=True)
                st.caption(f"#{idx} {item['priority']}")
                if item["risk_level"]:
                    risk_color = "#dc2626" if item["risk_level"] == "HIGH" else "#f59e0b" if item["risk_level"] == "MEDIUM" else "#10b981"
                    st.markdown(f"<span style='color:{risk_color}; font-size:0.85rem;'>{item['risk_level']}</span>", unsafe_allow_html=True)
            with col_body:
                st.markdown(f"**{item['product']}** ({item['category'] or 'N/A'})")
                for reason in item["reasons"][:4]:
                    st.caption(f"• {reason}")
            with col_meta:
                if item["reorder_quantity"] is not None:
                    st.metric("Est. Reorder Qty", f"{item['reorder_quantity']:.1f}", help="Estimated reorder quantity from backend planning")
                stockout_prob = item.get("evidence", {}).get("stockout_probability")
                if stockout_prob is not None:
                    st.caption(f"Stockout prob: {_format_percent(stockout_prob)}")
                excess_units = item.get("evidence", {}).get("excess_units")
                if excess_units is not None and excess_units > 0:
                    st.caption(f"Excess units: {excess_units:.1f}")
            st.divider()


def _render_ai_brief(products: List[Dict[str, Any]]) -> None:
    st.subheader("AI Business Brief")
    if not products:
        st.info("Upload data to generate an AI business brief.")
        return
    if not is_gemini_configured():
        st.warning("Gemini API key is not configured. AI brief is unavailable. Configure `GEMINI_API_KEY` to enable this section.")
        return
    if st.session_state.ai_brief is None and st.session_state.ai_brief_error is None:
        category_results = calculate_category_risk([
            {
                "category": p["category"],
                "risk_score": _safe_float(p["risk"].risk_score),
                "risk_level": p["risk"].risk_level,
                "inventory_value": _safe_float(p["financial"].inventory_value),
                "capital_tied_up": _safe_float(p["financial"].capital_tied_up),
                "shortage_units": max(0.0, _safe_float(p["planning"].lead_time_demand) - _safe_float(p["current_inventory"])) if _safe_float(p["planning"].lead_time_demand) is not None and _safe_float(p["current_inventory"]) is not None else None,
                "selling_price": _safe_float(p["selling_price"]),
                "excess_inventory_value": _safe_float(p["financial"].excess_inventory_value),
                "cv": _safe_float(p["demand_stats"].cv),
            }
            for p in products
            if p["risk"].risk_score is not None
        ])
        overall = calculate_overall_health(category_results, [
            {
                "risk_score": _safe_float(p["risk"].risk_score),
                "risk_level": p["risk"].risk_level,
                "revenue_at_risk": _safe_float(p["financial"].revenue_at_risk),
                "profit_at_risk": _safe_float(p["financial"].profit_at_risk),
            }
            for p in products
        ])
        top_products = sorted(products, key=lambda x: _safe_float(x["risk"].risk_score) or 0, reverse=True)[:MAX_PRODUCTS_FOR_AI]
        product_contexts = []
        for p in top_products:
            product_contexts.append(
                ProductContext(
                    product=p["product"],
                    category=p["category"],
                    mean_demand=_safe_float(p["demand_stats"].mean),
                    cv=_safe_float(p["demand_stats"].cv),
                    trend=p["trend_result"].trend,
                    trend_strength=_safe_float(p["trend_result"].trend_strength),
                    current_inventory=_safe_float(p["current_inventory"]),
                    days_remaining=_safe_float(p["planning"].days_remaining),
                    lead_time_days=_safe_float(p.get("lead_time_days")),
                    safety_stock=_safe_float(p["planning"].safety_stock),
                    reorder_point=_safe_float(p["planning"].reorder_point),
                    reorder_quantity=_safe_float(p["planning"].reorder_quantity),
                    stockout_probability=_safe_float(p["planning"].stockout_probability),
                    excess_units=_safe_float(p["financial"].excess_units),
                    excess_inventory_value=_safe_float(p["financial"].excess_inventory_value),
                    revenue_at_risk=_safe_float(p["financial"].revenue_at_risk),
                    profit_at_risk=_safe_float(p["financial"].profit_at_risk),
                    risk_score=_safe_float(p["risk"].risk_score),
                    risk_level=p["risk"].risk_level,
                    recommendation_action=p["recommendation"].action,
                    recommendation_priority=p["recommendation"].priority,
                    recommendation_reasons=p["recommendation"].reasons,
                    recommendation_evidence=p["recommendation"].evidence,
                )
            )
        request = ExecutiveSummaryRequest(
            overall_health_status=overall.overall_health_status,
            overall_risk_score=_safe_float(overall.overall_risk_score),
            total_products=overall.total_products,
            products_at_risk=overall.products_at_risk,
            high_risk_categories=overall.high_risk_categories,
            total_categories=overall.total_categories,
            total_stockout_exposure=_safe_float(overall.total_stockout_exposure),
            total_excess_inventory_value=_safe_float(overall.total_excess_inventory_value),
            total_capital_tied_up=_safe_float(overall.total_capital_tied_up),
            total_revenue_at_risk=_safe_float(overall.total_revenue_at_risk),
            total_profit_at_risk=_safe_float(overall.total_profit_at_risk),
            category_risk_levels=[cr.risk_level for cr in category_results.values() if cr.risk_level],
            products=product_contexts,
        )
        try:
            response = get_executive_summary(request)
            if isinstance(response, dict):
                st.session_state.ai_brief = response.get("text", "")
            else:
                st.session_state.ai_brief = getattr(response, "text", "")
        except Exception as exc:
            st.session_state.ai_brief_error = str(exc)
    if st.session_state.ai_brief_error:
        st.error(f"AI brief failed: {st.session_state.ai_brief_error}")
    elif st.session_state.ai_brief:
        st.success(st.session_state.ai_brief)
    else:
        with st.spinner("Generating AI business brief..."):
            st.empty()


def _render_product_explorer(products: List[Dict[str, Any]]) -> None:
    st.subheader("Product Explorer")
    if not products:
        st.info("No products to display.")
        return

    rows = []
    for p in products:
        risk_score = _safe_float(p["risk"].risk_score)
        risk_level = p["risk"].risk_level or "N/A"
        action = p["recommendation"].action or "N/A"
        main_issue = "Healthy"
        if action == "REORDER":
            main_issue = "Stockout risk"
        elif action == "REDUCE":
            main_issue = "Excess inventory"
        elif action == "HOLD":
            main_issue = "Low demand"
        elif action == "MONITOR":
            main_issue = "Volatility / trend"
        stockout_prob = _safe_float(p["planning"].stockout_probability)
        excess_units = _safe_float(p["financial"].excess_units)
        excess_ratio = None
        if excess_units is not None and _safe_float(p["financial"].target_stock) is not None and _safe_float(p["financial"].target_stock) > 0:
            excess_ratio = excess_units / _safe_float(p["financial"].target_stock)
        rows.append({
            "Product": p["product"],
            "Category": p["category"] or "N/A",
            "Risk Score": risk_score if risk_score is not None else 0,
            "Risk Level": risk_level,
            "Action": action,
            "Main Issue": main_issue,
            "Stockout Prob": stockout_prob,
            "Excess Units": excess_units,
            "Excess Ratio": excess_ratio,
        })
    explorer_df = pd.DataFrame(rows)

    with st.form("product_explorer_filters"):
        col_search, col_sort = st.columns([2, 1])
        with col_search:
            search = st.text_input("Search products", value="", placeholder="Type to search...")
        with col_sort:
            sort_by = st.selectbox(
                "Sort by",
                ["Risk Score", "Product", "Priority"],
                index=0,
            )
        col_risk, col_category, col_stockout, col_excess = st.columns(4)
        with col_risk:
            risk_filter = st.multiselect(
                "Risk Level",
                ["LOW", "MEDIUM", "HIGH"],
                default=[],
                help="Filter by risk level.",
            )
        with col_category:
            category_filter = st.multiselect(
                "Category",
                sorted(explorer_df["Category"].unique().tolist()),
                default=[],
                help="Filter by category.",
            )
        with col_stockout:
            stockout_filter = st.multiselect(
                "Stockout Risk",
                ["Stockout risk", "No stockout risk"],
                default=[],
                help="Filter by stockout exposure.",
            )
        with col_excess:
            excess_filter = st.multiselect(
                "Excess Inventory",
                ["Excess inventory", "No excess inventory"],
                default=[],
                help="Filter by excess inventory status.",
            )
        apply_filters = st.form_submit_button("Apply Filters", use_container_width=True)

    filtered_df = explorer_df.copy()
    if search:
        search_lower = search.lower()
        filtered_df = filtered_df[filtered_df["Product"].str.lower().str.contains(search_lower, na=False)]
    if risk_filter:
        filtered_df = filtered_df[filtered_df["Risk Level"].isin(risk_filter)]
    if category_filter:
        filtered_df = filtered_df[filtered_df["Category"].isin(category_filter)]
    if "Stockout risk" in stockout_filter and "No stockout risk" not in stockout_filter:
        filtered_df = filtered_df[filtered_df["Main Issue"] == "Stockout risk"]
    elif "No stockout risk" in stockout_filter and "Stockout risk" not in stockout_filter:
        filtered_df = filtered_df[filtered_df["Main Issue"] != "Stockout risk"]
    if "Excess inventory" in excess_filter and "No excess inventory" not in excess_filter:
        filtered_df = filtered_df[filtered_df["Main Issue"] == "Excess inventory"]
    elif "No excess inventory" in excess_filter and "Excess inventory" not in excess_filter:
        filtered_df = filtered_df[filtered_df["Main Issue"] != "Excess inventory"]

    if sort_by == "Risk Score":
        filtered_df = filtered_df.sort_values("Risk Score", ascending=False)
    elif sort_by == "Product":
        filtered_df = filtered_df.sort_values("Product")
    elif sort_by == "Priority":
        priority_map = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "NONE": 4}
        filtered_df = filtered_df.copy()
        filtered_df["_priority_sort"] = filtered_df["Action"].map(priority_map).fillna(99)
        filtered_df = filtered_df.sort_values(["_priority_sort", "Risk Score"], ascending=[True, False]).drop(columns=["_priority_sort"])

    display_df = filtered_df[["Product", "Category", "Risk Score", "Risk Level", "Action", "Main Issue"]].reset_index(drop=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    product_names = filtered_df["Product"].tolist()
    if product_names:
        selected = st.selectbox("Select a product to view details", product_names, index=0 if product_names else None)
        if selected and st.button("View Product Deep Dive", type="primary"):
            st.session_state.selected_product = selected
            st.session_state.navigate_to = "Product Deep Dive"
            st.rerun()
    else:
        st.info("No products match the current filters.")


def _render_category_analysis(products: List[Dict[str, Any]]) -> None:
    st.subheader("Category Analysis")
    if not products:
        st.info("No category data available.")
        return

    category_products = [
        {
            "category": p["category"],
            "risk_score": _safe_float(p["risk"].risk_score),
            "risk_level": p["risk"].risk_level,
            "inventory_value": _safe_float(p["financial"].inventory_value),
            "capital_tied_up": _safe_float(p["financial"].capital_tied_up),
            "shortage_units": max(0.0, _safe_float(p["planning"].lead_time_demand) - _safe_float(p["current_inventory"])) if _safe_float(p["planning"].lead_time_demand) is not None and _safe_float(p["current_inventory"]) is not None else None,
            "selling_price": _safe_float(p["selling_price"]),
            "excess_inventory_value": _safe_float(p["financial"].excess_inventory_value),
            "cv": _safe_float(p["demand_stats"].cv),
        }
        for p in products
        if p["risk"].risk_score is not None
    ]

    category_results = calculate_category_risk(category_products)

    if not category_results:
        st.info("No valid category data available.")
        return

    rows = []
    for category, result in category_results.items():
        risk_score = _safe_float(result.risk_score)
        avg_risk = _safe_float(result.average_product_risk_score)
        risk_level = result.risk_level or "N/A"
        risk_color = "#6b7280"
        if risk_level == "HIGH":
            risk_color = "#dc2626"
        elif risk_level == "MEDIUM":
            risk_color = "#f59e0b"
        elif risk_level == "LOW":
            risk_color = "#10b981"

        rows.append({
            "Category": category,
            "Products": result.product_count,
            "High-Risk Products": result.high_risk_product_count,
            "Avg Product Risk": f"{avg_risk:.1f}" if avg_risk is not None else "N/A",
            "Category Risk": f"{risk_score:.1f}" if risk_score is not None else "N/A",
            "Risk Level": risk_level,
            "Inventory Value": _format_currency(result.category_inventory_value),
            "Capital Tied Up": _format_currency(result.category_capital_tied_up),
            "Stockout Exposure": _format_currency(result.category_stockout_exposure),
            "Excess Inventory": _format_currency(result.category_excess_inventory_value),
            "Demand Volatility": f"{result.category_demand_volatility:.2f}" if result.category_demand_volatility is not None else "N/A",
        })

        if result.warnings:
            for warning in result.warnings[:2]:
                st.caption(f"{category}: {warning}")

    results_df = pd.DataFrame(rows)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Category Comparison Table**")
        display_cols = ["Category", "Products", "High-Risk Products", "Category Risk", "Risk Level", "Demand Volatility"]
        st.dataframe(results_df[display_cols], use_container_width=True, hide_index=True)
    with col2:
        st.markdown("**Financial Metrics by Category**")
        financial_cols = ["Category", "Inventory Value", "Capital Tied Up", "Stockout Exposure", "Excess Inventory"]
        st.dataframe(results_df[financial_cols], use_container_width=True, hide_index=True)

    st.markdown("**Category Risk Comparison**")
    if not results_df.empty and "Category Risk" in results_df.columns:
        chart_data = results_df[["Category", "Category Risk", "High-Risk Products"]].copy()
        chart_data["Category Risk"] = pd.to_numeric(chart_data["Category Risk"], errors="coerce")
        chart_data = chart_data.dropna(subset=["Category Risk"])
        if not chart_data.empty:
            st.bar_chart(chart_data.set_index("Category")["Category Risk"])


def _render_product_deep_dive(products: List[Dict[str, Any]]) -> None:
    st.subheader("Product Deep Dive")
    if not products:
        st.info("No products available.")
        return
    product_names = [p["product"] for p in products]
    default_index = 0
    if st.session_state.selected_product in product_names:
        default_index = product_names.index(st.session_state.selected_product)
        st.session_state.selected_product = None
        st.session_state.navigate_to = None
    selected = st.selectbox("Select a product", product_names, index=default_index if product_names else None)
    if not selected:
        return
    product = next((p for p in products if p["product"] == selected), None)
    if not product:
        return

    risk_score = _safe_float(product["risk"].risk_score)
    risk_level = product["risk"].risk_level or "N/A"
    rec = product["recommendation"]

    # Header
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Product", selected)
        st.caption(f"Category: {product['category'] or 'N/A'}")
    with col2:
        st.metric("Risk Score", f"{risk_score:.1f}" if risk_score is not None else "N/A")
        st.metric("Risk Level", risk_level)
    with col3:
        action_color = PRIORITY_ACTION_COLORS.get(rec.action, "#6b7280")
        st.markdown(f"<span style='color:{action_color}; font-weight:bold; font-size:1.2rem;'>{rec.action}</span>", unsafe_allow_html=True)
        st.caption(f"Priority: {rec.priority}")

    st.divider()

    # Demand
    st.markdown("### Demand")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("**Observed**")
        mean = _safe_float(product["demand_stats"].mean)
        median = _safe_float(product["demand_stats"].median)
        min_d = _safe_float(product["demand_stats"].min)
        max_d = _safe_float(product["demand_stats"].max)
        zero_days = product["demand_stats"].zero_demand_days
        st.metric("Mean Demand", f"{mean:.2f}" if mean is not None else "N/A")
        st.metric("Median Demand", f"{median:.2f}" if median is not None else "N/A")
        st.metric("Min / Max", f"{min_d:.0f} / {max_d:.0f}" if min_d is not None and max_d is not None else "N/A")
        st.caption(f"Zero-demand days: {zero_days if zero_days is not None else 'N/A'}")
    with col2:
        st.caption("**Variability**")
        cv = _safe_float(product["demand_stats"].cv)
        std = _safe_float(product["demand_stats"].std_dev)
        variance = _safe_float(product["demand_stats"].variance)
        st.metric("CV", f"{cv:.2f}" if cv is not None else "N/A")
        st.metric("Std Dev", f"{std:.2f}" if std is not None else "N/A")
        st.metric("Variance", f"{variance:.2f}" if variance is not None else "N/A")
    with col3:
        st.caption("**Trend**")
        trend = product["trend_result"].trend or "N/A"
        strength = _safe_float(product["trend_result"].trend_strength)
        significant = product["trend_result"].trend_significant
        st.metric("Trend", trend.title() if isinstance(trend, str) else str(trend))
        st.metric("Strength", f"{strength:.3f}" if strength is not None else "N/A")
        st.caption(f"Significant: {'Yes' if significant else 'No' if significant is not None else 'N/A'}")

    pattern_label = getattr(product.get("pattern"), "monthly_pattern_label", None)
    if pattern_label:
        st.caption(f"Pattern: {pattern_label}")

    outlier_result = product.get("outlier_result")
    if outlier_result is not None:
        if outlier_result.outlier_mask is not None:
            outlier_count = int(outlier_result.outlier_mask.sum())
            st.caption(f"Outliers: {outlier_count} (method: {outlier_result.method})")
        elif outlier_result.warnings:
            for warning in outlier_result.warnings[:2]:
                st.caption(f"Outlier note: {warning}")

    demand_history = product.get("demand_history", [])
    if demand_history:
        demand_df = pd.DataFrame(demand_history, columns=["date", "units_sold"])
        demand_df["date"] = pd.to_datetime(demand_df["date"])
        st.markdown("**Demand History**")
        st.line_chart(demand_df.set_index("date")["units_sold"])

    st.divider()

    # Inventory
    st.markdown("### Inventory")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("**Current**")
        current_inv = _safe_float(product["current_inventory"])
        st.metric("Current Inventory", f"{current_inv:.0f}" if current_inv is not None else "N/A")
    with col2:
        st.caption("**Planning Estimates**")
        safety_stock = _safe_float(product["planning"].safety_stock)
        reorder_point = _safe_float(product["planning"].reorder_point)
        days_remaining = _safe_float(product["planning"].days_remaining)
        st.metric("Safety Stock", f"{safety_stock:.1f}" if safety_stock is not None else "N/A")
        st.metric("Reorder Point (ROP)", f"{reorder_point:.1f}" if reorder_point is not None else "N/A")
        st.metric("Days Remaining", f"{days_remaining:.1f}" if days_remaining is not None else "N/A")
    with col3:
        st.caption("**Stockout Risk**")
        stockout_prob = _safe_float(product["planning"].stockout_probability)
        st.metric("Stockout Probability", _format_percent(stockout_prob))

    inventory_history = product.get("inventory_history", [])
    if inventory_history:
        inv_df = pd.DataFrame(inventory_history, columns=["date", "inventory"])
        inv_df["date"] = pd.to_datetime(inv_df["date"])
        st.markdown("**Inventory History**")
        st.line_chart(inv_df.set_index("date")["inventory"])

    st.divider()

    # Financial
    st.markdown("### Financial Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("**Inventory Value**")
        inv_value = _safe_float(product["financial"].inventory_value)
        capital = _safe_float(product["financial"].capital_tied_up)
        unit_cost = _safe_float(product["unit_cost"])
        st.metric("Inventory Value", _format_currency(inv_value))
        st.metric("Capital Tied Up", _format_currency(capital))
        st.metric("Unit Cost", _format_currency(unit_cost))
    with col2:
        st.caption("**Excess**")
        excess_units = _safe_float(product["financial"].excess_units)
        excess_value = _safe_float(product["financial"].excess_inventory_value)
        st.metric("Excess Units", f"{excess_units:.1f}" if excess_units is not None else "N/A")
        st.metric("Excess Value", _format_currency(excess_value))
    with col3:
        st.caption("**Revenue / Profit Exposure**")
        revenue = _safe_float(product["financial"].revenue_at_risk)
        profit = _safe_float(product["financial"].profit_at_risk)
        gross_margin = _safe_float(product["financial"].gross_margin)
        st.metric("Revenue at Risk", _format_currency(revenue))
        st.metric("Profit at Risk", _format_currency(profit))
        st.metric("Gross Margin", _format_percent(gross_margin))

    st.divider()

    # Recommendation
    st.markdown("### Recommendation")
    action_color = PRIORITY_ACTION_COLORS.get(rec.action, "#6b7280")
    st.markdown(f"<span style='color:{action_color}; font-weight:bold; font-size:1.1rem;'>{rec.action}</span> — <b>{rec.priority}</b>", unsafe_allow_html=True)
    if rec.reasons:
        st.markdown("**Reasons:**")
        for reason in rec.reasons[:8]:
            st.caption(f"• {reason}")
    if rec.evidence:
        st.markdown("**Evidence:**")
        for key, value in rec.evidence.items():
            st.caption(f"• {key}: {value}")

    st.divider()

    # Gemini button (UI element only)
    if st.button("Ask Gemini for explanation", key=f"gemini_{selected}"):
        if not is_gemini_configured():
            st.warning("Gemini API key is not configured.")
        else:
            context = ProductContext(
                product=product["product"],
                category=product["category"],
                mean_demand=_safe_float(product["demand_stats"].mean),
                cv=_safe_float(product["demand_stats"].cv),
                trend=product["trend_result"].trend,
                trend_strength=_safe_float(product["trend_result"].trend_strength),
                current_inventory=_safe_float(product["current_inventory"]),
                days_remaining=_safe_float(product["planning"].days_remaining),
                lead_time_days=_safe_float(product.get("lead_time_days")),
                safety_stock=_safe_float(product["planning"].safety_stock),
                reorder_point=_safe_float(product["planning"].reorder_point),
                reorder_quantity=_safe_float(product["planning"].reorder_quantity),
                stockout_probability=_safe_float(product["planning"].stockout_probability),
                excess_units=_safe_float(product["financial"].excess_units),
                excess_inventory_value=_safe_float(product["financial"].excess_inventory_value),
                revenue_at_risk=_safe_float(product["financial"].revenue_at_risk),
                profit_at_risk=_safe_float(product["financial"].profit_at_risk),
                risk_score=_safe_float(product["risk"].risk_score),
                risk_level=product["risk"].risk_level,
                recommendation_action=rec.action,
                recommendation_priority=rec.priority,
                recommendation_reasons=rec.reasons,
                recommendation_evidence=rec.evidence,
            )
            try:
                explanation = get_product_explanation(context)
                if isinstance(explanation, dict):
                    st.info(explanation.get("text", ""))
                else:
                    st.info(getattr(explanation, "text", ""))
            except Exception as exc:
                st.error(f"Gemini explanation failed: {exc}")


def _render_historical_analysis(products: List[Dict[str, Any]], filtered_df: pd.DataFrame) -> None:
    st.subheader("Historical Analysis")
    if not products:
        st.info("No historical data available.")
        return

    categories = sorted(set(p.get("category") or "Uncategorized" for p in products))
    selected_categories = st.multiselect("Filter by category", categories, default=categories)
    if selected_categories:
        products = [p for p in products if (p.get("category") or "Uncategorized") in selected_categories]

    if not products:
        st.info("No products match the selected categories.")
        return

    product_names = [p["product"] for p in products]
    default_products = product_names[:min(5, len(product_names))]
    selected_products = st.multiselect("Select products", product_names, default=default_products)
    if not selected_products:
        st.info("Select at least one product to view historical data.")
        return

    selected_set = set(selected_products)
    for product in products:
        if product["product"] not in selected_set:
            continue

        st.markdown(f"**{product['product']}** ({product.get('category') or 'N/A'})")

        demand_history = product.get("demand_history", [])
        if demand_history:
            demand_df = pd.DataFrame(demand_history, columns=["date", "units_sold"])
            demand_df["date"] = pd.to_datetime(demand_df["date"])
            demand_df = demand_df.sort_values("date").drop_duplicates(subset=["date"])
            st.markdown("**Daily Sales**")
            st.line_chart(demand_df.set_index("date")["units_sold"])

            outlier_dates = product.get("outlier_dates", [])
            if outlier_dates:
                spike_df = demand_df[demand_df["date"].isin(pd.to_datetime(outlier_dates))]
                if not spike_df.empty:
                    st.caption("Demand spikes:")
                    for _, row in spike_df.iterrows():
                        st.caption(f"• {row['date'].strftime('%Y-%m-%d')}: {row['units_sold']:.0f} units")

        inventory_history = product.get("inventory_history", [])
        if inventory_history:
            inv_df = pd.DataFrame(inventory_history, columns=["date", "inventory"])
            inv_df["date"] = pd.to_datetime(inv_df["date"])
            inv_df = inv_df.sort_values("date").drop_duplicates(subset=["date"])
            st.markdown("**Inventory Level**")
            st.line_chart(inv_df.set_index("date")["inventory"])

            stockouts = inv_df[inv_df["inventory"] == 0]
            if not stockouts.empty:
                st.caption("Stockout events:")
                for _, row in stockouts.iterrows():
                    st.caption(f"• {row['date'].strftime('%Y-%m-%d')}: out of stock")

            inv_df["prev_inventory"] = inv_df["inventory"].shift(1)
            replenishments = inv_df[inv_df["inventory"] > inv_df["prev_inventory"].fillna(0) * 1.2]
            if not replenishments.empty:
                st.caption("Replenishment events:")
                for _, row in replenishments.iterrows():
                    st.caption(f"• {row['date'].strftime('%Y-%m-%d')}: inventory increased to {row['inventory']:.0f}")

            safety_stock = _safe_float(product["planning"].safety_stock)
            if safety_stock is not None:
                breaches = inv_df[inv_df["inventory"] < safety_stock]
                if not breaches.empty:
                    st.caption(f"Safety-stock-breach events (below safety stock {safety_stock:.1f}):")
                    for _, row in breaches.iterrows():
                        st.caption(f"• {row['date'].strftime('%Y-%m-%d')}: inventory {row['inventory']:.0f}")

        st.divider()


def _render_what_if_scenarios(products: List[Dict[str, Any]]) -> None:
    st.subheader("What-If Scenarios")
    if not products:
        st.info("No baseline data available for scenarios.")
        return
    product_names = [p["product"] for p in products]
    selected = st.selectbox("Select a product", product_names, index=0 if product_names else None, key="scenario_product")
    if not selected:
        return
    product = next((p for p in products if p["product"] == selected), None)
    if not product:
        return
    col1, col2 = st.columns(2)
    with col1:
        demand_change = st.slider("Demand Change (%)", min_value=-50, max_value=100, value=0, step=1)
    with col2:
        lead_time_change = st.slider("Lead Time Change (days)", min_value=-5, max_value=14, value=0, step=1)
    if st.button("Run Scenario"):
        mean_demand = _safe_float(product["demand_stats"].mean) or 0.0
        std_dev = _safe_float(product["demand_stats"].std_dev) or 0.0
        current_inventory = _safe_float(product["current_inventory"])
        lead_time_days = _safe_float(product.get("lead_time_days"))
        unit_cost = _safe_float(product["unit_cost"]) or 0.0
        selling_price = _safe_float(product["selling_price"]) or 0.0
        try:
            scenario = run_scenario(
                mean_demand=mean_demand,
                std_dev=std_dev,
                current_inventory=current_inventory,
                unit_cost=unit_cost,
                selling_price=selling_price,
                lead_time_days=lead_time_days,
                mean_demand_change_pct=demand_change / 100,
                lead_time_days_change=float(lead_time_change),
            )
            st.session_state.scenario_result = scenario
        except Exception as exc:
            st.error(f"Scenario failed: {exc}")
    scenario = st.session_state.get("scenario_result")
    if scenario is not None:
        baseline = scenario.baseline
        scen = scenario.scenario
        deltas = scenario.deltas

        st.markdown("**Baseline vs Scenario**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("*Baseline*")
            st.metric("Risk Score", f"{_safe_float(baseline.risk.risk_score):.1f}" if _safe_float(baseline.risk.risk_score) is not None else "N/A")
            st.metric("Risk Level", baseline.risk.risk_level or "N/A")
            st.metric("Recommendation", baseline.recommendation.action or "N/A")
            st.caption(f"Priority: {baseline.recommendation.priority}")
        with col2:
            st.markdown("*Scenario*")
            st.metric("Risk Score", f"{_safe_float(scen.risk.risk_score):.1f}" if _safe_float(scen.risk.risk_score) is not None else "N/A")
            st.metric("Risk Level", scen.risk.risk_level or "N/A")
            st.metric("Recommendation", scen.recommendation.action or "N/A")
            st.caption(f"Priority: {scen.recommendation.priority}")

        st.markdown("**Impact Summary**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("**Planning**")
            st.metric("Safety Stock", f"{_safe_float(scen.planning.safety_stock):.1f}" if _safe_float(scen.planning.safety_stock) is not None else "N/A", delta=_format_delta(deltas.safety_stock))
            st.metric("Reorder Point", f"{_safe_float(scen.planning.reorder_point):.1f}" if _safe_float(scen.planning.reorder_point) is not None else "N/A", delta=_format_delta(deltas.reorder_point))
            st.metric("Days Remaining", f"{_safe_float(scen.planning.days_remaining):.1f}" if _safe_float(scen.planning.days_remaining) is not None else "N/A", delta=_format_delta(deltas.days_remaining))
        with col2:
            st.caption("**Financial**")
            st.metric("Excess Units", f"{_safe_float(scen.financial.excess_units):.1f}" if _safe_float(scen.financial.excess_units) is not None else "N/A", delta=_format_delta(deltas.excess_units))
            st.metric("Excess Value", _format_currency(_safe_float(scen.financial.excess_inventory_value)), delta=_format_delta(deltas.excess_inventory_value))
            st.metric("Revenue at Risk", _format_currency(_safe_float(scen.financial.revenue_at_risk)), delta=_format_delta(deltas.revenue_at_risk))
        with col3:
            st.caption("**Stockout / Profit**")
            st.metric("Stockout Probability", _format_percent(_safe_float(scen.planning.stockout_probability)), delta=_format_delta(deltas.stockout_probability))
            st.metric("Profit at Risk", _format_currency(_safe_float(scen.financial.profit_at_risk)), delta=_format_delta(deltas.profit_at_risk))
            st.metric("Risk Score", f"{_safe_float(scen.risk.risk_score):.1f}" if _safe_float(scen.risk.risk_score) is not None else "N/A", delta=_format_delta(deltas.risk_score))

        st.markdown("**Causal Chain**")
        st.caption(f"Demand change: {demand_change:+d}% → scenario mean demand = {_safe_float(scen.planning.lead_time_demand):.1f if _safe_float(scen.planning.lead_time_demand) is not None else 'N/A'} units")
        st.caption(f"Lead time change: {lead_time_change:+d} days → scenario lead time = {_safe_float(product.get('lead_time_days')) + lead_time_change if _safe_float(product.get('lead_time_days')) is not None else 'N/A'} days")
        if deltas.risk_score is not None:
            direction = "increases" if deltas.risk_score > 0 else "decreases" if deltas.risk_score < 0 else "unchanged"
            st.caption(f"Risk score {direction} by {abs(deltas.risk_score):.1f} points under this scenario.")

        if st.button("Reset Scenario"):
            st.session_state.scenario_result = None
            st.rerun()


def _render_sidebar(df: pd.DataFrame) -> Tuple[Tuple[datetime, datetime], List[str], str]:
    st.sidebar.header("Global Controls")
    min_date = datetime.today() - timedelta(days=DEFAULT_DATE_RANGE_DAYS)
    max_date = datetime.today()
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not dates.empty:
            min_date = dates.min().to_pydatetime()
            max_date = dates.max().to_pydatetime()
    date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if len(date_range) != 2:
        date_range = (min_date, max_date)
    categories = []
    if "category" in df.columns:
        all_categories = sorted(df["category"].dropna().unique().tolist())
        categories = st.sidebar.multiselect("Category", all_categories, default=all_categories)
    product_search = st.sidebar.text_input("Search products", value="", placeholder="Type to search...")
    return date_range, categories, product_search


def main() -> None:
    _init_session_state()
    st.title("InventoryIQ V2")
    st.caption("Inventory decision-support dashboard")

    with st.sidebar:
        st.header("Data Input")
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        data_source = st.radio(
            "Data source",
            ["Sample data", "Mock demo data"],
            index=0,
            help="Use sample data or mock demo data to explore all product states.",
        )

    raw_df = pd.DataFrame()
    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
        except Exception as exc:
            st.error(f"Failed to read CSV: {exc}")
            st.stop()
    elif data_source == "Sample data":
        raw_df = _load_sample_data()
    else:
        raw_df = _load_mock_data()

    if raw_df.empty:
        st.info("Upload a CSV file or enable sample data to begin.")
        st.stop()

    validation = validate_input(raw_df)
    if not validation.is_valid:
        st.error("Data validation failed:")
        for err in validation.errors:
            st.write(f"- {err}")
        st.stop()

    processed_df = validation.df.copy()
    date_range, categories, product_search = _render_sidebar(processed_df)
    filtered_df = _apply_filters(processed_df, date_range, categories, product_search)
    if filtered_df.empty:
        st.warning("No data matches the current filters.")
        st.stop()

    products = _run_pipeline(filtered_df)
    st.session_state.products = products

    section = st.session_state.get("navigate_to")
    if section not in [
        "Inventory Health",
        "Top Priorities",
        "AI Business Brief",
        "Product Explorer",
        "Category Analysis",
        "Product Deep Dive",
        "Historical Analysis",
        "What-If Scenarios",
    ]:
        section = st.sidebar.radio(
            "Navigate",
            [
                "Inventory Health",
                "Top Priorities",
                "AI Business Brief",
                "Product Explorer",
                "Category Analysis",
                "Product Deep Dive",
                "Historical Analysis",
                "What-If Scenarios",
            ],
            index=0,
        )
    else:
        st.session_state.navigate_to = None

    if section == "Inventory Health":
        _render_inventory_health(products)
    elif section == "Top Priorities":
        _render_top_priorities(products)
    elif section == "AI Business Brief":
        _render_ai_brief(products)
    elif section == "Product Explorer":
        _render_product_explorer(products)
    elif section == "Category Analysis":
        _render_category_analysis(products)
    elif section == "Product Deep Dive":
        _render_product_deep_dive(products)
    elif section == "Historical Analysis":
        _render_historical_analysis(products, filtered_df)
    elif section == "What-If Scenarios":
        _render_what_if_scenarios(products)


if __name__ == "__main__":
    main()
