import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from analysis import (
    OverallHealthResult,
    calculate_category_risk,
    calculate_demand_statistics,
    calculate_financial_and_excess_metrics,
    calculate_inventory_planning,
    calculate_overall_health,
    calculate_product_risk,
    calculate_trend,
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
        pattern = type("PatternResult", (), {"weekday_factors": None, "monthly_factors": None, "monthly_pattern_label": None})()
        products.append(_build_product_result(last_row, demand_stats, trend_result, planning, financial, pattern))
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
        st.metric("Stockout Exposure", _format_currency(stockout))
    with col4:
        excess = overall.total_excess_inventory_value
        st.metric("Excess Inventory", _format_currency(excess))
    col5, col6 = st.columns(2)
    with col5:
        capital = overall.total_capital_tied_up
        st.metric("Capital Tied Up", _format_currency(capital))
    with col6:
        revenue = overall.total_revenue_at_risk
        profit = overall.total_profit_at_risk
        st.metric("Revenue / Profit Risk", f"{_format_currency(revenue)} / {_format_currency(profit)}")


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
            "action": rec.action,
            "priority": rec.priority,
            "reasons": rec.reasons,
            "reorder_quantity": rec.reorder_quantity,
            "risk_score": _safe_float(p["risk"].risk_score),
            "risk_level": p["risk"].risk_level,
        })
    prioritized.sort(key=lambda x: (PRIORITY_ORDER.get(x["priority"], 99), -(x["risk_score"] or 0)))
    for idx, item in enumerate(prioritized[:10], 1):
        action_color = PRIORITY_ACTION_COLORS.get(item["action"], "#6b7280")
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                st.markdown(f"<span style='color:{action_color}; font-weight:bold; font-size:1.1rem;'>{item['action']}</span>", unsafe_allow_html=True)
                st.caption(f"#{idx} {item['priority']}")
            with col2:
                st.markdown(f"**{item['product']}**")
                for reason in item["reasons"][:3]:
                    st.caption(reason)
            with col3:
                if item["reorder_quantity"] is not None:
                    st.metric("Reorder Qty", f"{item['reorder_quantity']:.1f}")
                if item["risk_level"]:
                    st.caption(f"Risk: {item['risk_level']}")
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
        rows.append({
            "Product": p["product"],
            "Category": p["category"] or "N/A",
            "Risk Score": risk_score if risk_score is not None else 0,
            "Risk Level": risk_level,
            "Action": action,
            "Main Issue": main_issue,
        })
    explorer_df = pd.DataFrame(rows)
    st.dataframe(explorer_df, use_container_width=True, hide_index=True)


def _render_category_analysis(products: List[Dict[str, Any]]) -> None:
    st.subheader("Category Analysis")
    if not products:
        st.info("No category data available.")
        return
    category_map: Dict[str, List[Dict[str, Any]]] = {}
    for p in products:
        cat = p["category"] or "Uncategorized"
        category_map.setdefault(cat, []).append(p)
    rows = []
    for category, items in category_map.items():
        risk_scores = [_safe_float(i["risk"].risk_score) for i in items if _safe_float(i["risk"].risk_score) is not None]
        avg_risk = float(sum(risk_scores) / len(risk_scores)) if risk_scores else None
        stockout_exposure = sum(_safe_float(i["financial"].revenue_at_risk) or 0 for i in items)
        excess_value = sum(_safe_float(i["financial"].excess_inventory_value) or 0 for i in items)
        inventory_value = sum(_safe_float(i["financial"].inventory_value) or 0 for i in items)
        risk_level = "LOW"
        if avg_risk is not None:
            if avg_risk >= 70:
                risk_level = "HIGH"
            elif avg_risk >= 40:
                risk_level = "MEDIUM"
        rows.append({
            "Category": category,
            "Products": len(items),
            "Avg Risk": f"{avg_risk:.1f}" if avg_risk is not None else "N/A",
            "Risk Level": risk_level,
            "Stockout Exposure": _format_currency(stockout_exposure),
            "Excess Inventory": _format_currency(excess_value),
            "Inventory Value": _format_currency(inventory_value),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_product_deep_dive(products: List[Dict[str, Any]]) -> None:
    st.subheader("Product Deep Dive")
    if not products:
        st.info("No products available.")
        return
    product_names = [p["product"] for p in products]
    selected = st.selectbox("Select a product", product_names, index=0 if product_names else None)
    if not selected:
        return
    product = next((p for p in products if p["product"] == selected), None)
    if not product:
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Mean Demand", f"{_safe_float(product['demand_stats'].mean):.2f}" if _safe_float(product['demand_stats'].mean) is not None else "N/A")
        st.metric("CV", f"{_safe_float(product['demand_stats'].cv):.2f}" if _safe_float(product['demand_stats'].cv) is not None else "N/A")
    with col2:
        st.metric("Days Remaining", f"{_safe_float(product['planning'].days_remaining):.1f}" if _safe_float(product['planning'].days_remaining) is not None else "N/A")
        st.metric("Stockout Probability", _format_percent(_safe_float(product['planning'].stockout_probability)))
    with col3:
        st.metric("Risk Score", f"{_safe_float(product['risk'].risk_score):.1f}" if _safe_float(product['risk'].risk_score) is not None else "N/A")
        st.metric("Risk Level", product["risk"].risk_level or "N/A")
    st.markdown("**Recommendation**")
    rec = product["recommendation"]
    st.markdown(f"**{rec.action}** — {rec.priority}")
    for reason in rec.reasons[:5]:
        st.caption(reason)
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


def _render_historical_analysis(df: pd.DataFrame) -> None:
    st.subheader("Historical Analysis")
    if df.empty:
        st.info("No historical data available.")
        return
    if "date" not in df.columns or "units_sold" not in df.columns:
        st.info("Historical view requires date and units_sold columns.")
        return
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date"]).sort_values("date")
    if chart_df.empty:
        st.info("No valid date data available.")
        return
    product_names = sorted(chart_df["product"].dropna().unique()) if "product" in chart_df.columns else []
    selected_products = st.multiselect("Select products", product_names, default=product_names[:5] if len(product_names) > 5 else product_names)
    if not selected_products:
        st.info("Select at least one product to view historical data.")
        return
    filtered = chart_df[chart_df["product"].isin(selected_products)]
    daily_sales = filtered.groupby(["date", "product"])["units_sold"].sum().reset_index()
    st.markdown("**Daily Sales Over Time**")
    st.line_chart(daily_sales.pivot(index="date", columns="product", values="units_sold"))
    if "inventory" in filtered.columns:
        daily_inventory = filtered.groupby(["date", "product"])["inventory"].last().reset_index()
        st.markdown("**Inventory Over Time**")
        st.line_chart(daily_inventory.pivot(index="date", columns="product", values="inventory"))


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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Baseline Risk Score", f"{_safe_float(baseline.risk.risk_score):.1f}" if _safe_float(baseline.risk.risk_score) is not None else "N/A")
        with col2:
            st.metric("Scenario Risk Score", f"{_safe_float(scen.risk.risk_score):.1f}" if _safe_float(scen.risk.risk_score) is not None else "N/A")
        with col3:
            delta = _safe_float(deltas.risk_score)
            st.metric("Risk Delta", f"{delta:+.1f}" if delta is not None else "N/A")
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
        use_sample = st.checkbox("Use sample data", value=True)

    raw_df = pd.DataFrame()
    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
        except Exception as exc:
            st.error(f"Failed to read CSV: {exc}")
            st.stop()
    elif use_sample:
        raw_df = _load_sample_data()

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
        _render_historical_analysis(filtered_df)
    elif section == "What-If Scenarios":
        _render_what_if_scenarios(products)


if __name__ == "__main__":
    main()
