"""Gemini AI integration for InventoryIQ V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from google import genai
from google.genai import types as genai_types

from gemini_config import get_gemini_api_key, is_gemini_configured


DEFAULT_MODEL = "gemini-2.0-flash"


@dataclass
class ProductContext:
    product: str
    category: str
    mean_demand: Optional[float] = None
    cv: Optional[float] = None
    trend: Optional[str] = None
    trend_strength: Optional[float] = None
    current_inventory: Optional[float] = None
    days_remaining: Optional[float] = None
    lead_time_days: Optional[float] = None
    safety_stock: Optional[float] = None
    reorder_point: Optional[float] = None
    reorder_quantity: Optional[float] = None
    stockout_probability: Optional[float] = None
    excess_units: Optional[float] = None
    excess_inventory_value: Optional[float] = None
    revenue_at_risk: Optional[float] = None
    profit_at_risk: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    recommendation_action: Optional[str] = None
    recommendation_priority: Optional[str] = None
    recommendation_reasons: List[str] = field(default_factory=list)
    recommendation_evidence: dict = field(default_factory=dict)


@dataclass
class ExecutiveSummaryRequest:
    overall_health_status: Optional[str] = None
    overall_risk_score: Optional[float] = None
    total_products: int = 0
    products_at_risk: int = 0
    high_risk_categories: int = 0
    total_categories: int = 0
    total_stockout_exposure: Optional[float] = None
    total_excess_inventory_value: Optional[float] = None
    total_capital_tied_up: Optional[float] = None
    total_revenue_at_risk: Optional[float] = None
    total_profit_at_risk: Optional[float] = None
    category_risk_levels: List[str] = field(default_factory=list)
    products: List[ProductContext] = field(default_factory=list)


@dataclass
class GeminiResponse:
    text: str
    model: str
    finish_reason: Optional[str] = None


@dataclass
class GeminiFailure:
    error_type: str
    message: str
    details: Optional[str] = None


def _get_client() -> genai.Client:
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


def _call_gemini(prompt: str, *, model: str = DEFAULT_MODEL) -> GeminiResponse:
    client = _get_client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=512,
        ),
    )
    text = ""
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        text = "".join(part.text or "" for part in response.candidates[0].content.parts if part.text)
    return GeminiResponse(
        text=text.strip(),
        model=model,
        finish_reason=response.candidates[0].finish_reason if response.candidates else None,
    )


def _build_executive_prompt(request: ExecutiveSummaryRequest) -> str:
    lines = [
        "You are an inventory business analyst assistant.",
        "Do not calculate or modify any numbers.",
        "Use only the verified context provided below.",
        "Provide a concise business summary in 3-5 bullets.",
        "",
        "Verified context:",
        f"- Overall health status: {request.overall_health_status or 'N/A'}",
        f"- Overall risk score: {request.overall_risk_score if request.overall_risk_score is not None else 'N/A'}",
        f"- Total products: {request.total_products}",
        f"- Products at risk (MEDIUM/HIGH): {request.products_at_risk}",
        f"- Total categories: {request.total_categories}",
        f"- High-risk categories: {request.high_risk_categories}",
        f"- Total stockout exposure: {request.total_stockout_exposure if request.total_stockout_exposure is not None else 'N/A'}",
        f"- Total excess inventory value: {request.total_excess_inventory_value if request.total_excess_inventory_value is not None else 'N/A'}",
        f"- Total capital tied up: {request.total_capital_tied_up if request.total_capital_tied_up is not None else 'N/A'}",
        f"- Total revenue at risk: {request.total_revenue_at_risk if request.total_revenue_at_risk is not None else 'N/A'}",
        f"- Total profit at risk: {request.total_profit_at_risk if request.total_profit_at_risk is not None else 'N/A'}",
        f"- Category risk levels: {', '.join(request.category_risk_levels) if request.category_risk_levels else 'N/A'}",
    ]

    if request.products:
        lines.append("- Top products needing attention:")
        for product in request.products[:10]:
            action = product.recommendation_action or "N/A"
            priority = product.recommendation_priority or "N/A"
            lines.append(
                f"  - {product.product or 'Unknown'} | {product.category or 'N/A'} | "
                f"risk={product.risk_level or 'N/A'} | action={action} | priority={priority}"
            )
    lines.append("")
    lines.append("Provide only the summary bullets. Do not invent metrics or override the deterministic assessment.")
    return "\n".join(lines)


def _build_product_prompt(context: ProductContext) -> str:
    lines = [
        "You are an inventory business analyst assistant.",
        "Do not calculate or modify any numbers.",
        "Use only the verified context provided below.",
        "Explain the product's situation, why it is risky or healthy, and what the recommendation means.",
        "Keep it concise and focused on business attention points.",
        "",
        "Verified product context:",
        f"- Product: {context.product or 'N/A'}",
        f"- Category: {context.category or 'N/A'}",
        f"- Mean demand: {context.mean_demand if context.mean_demand is not None else 'N/A'}",
        f"- Coefficient of variation: {context.cv if context.cv is not None else 'N/A'}",
        f"- Demand trend: {context.trend or 'N/A'}",
        f"- Trend strength: {context.trend_strength if context.trend_strength is not None else 'N/A'}",
        f"- Current inventory: {context.current_inventory if context.current_inventory is not None else 'N/A'}",
        f"- Days remaining: {context.days_remaining if context.days_remaining is not None else 'N/A'}",
        f"- Lead time: {context.lead_time_days if context.lead_time_days is not None else 'N/A'}",
        f"- Safety stock: {context.safety_stock if context.safety_stock is not None else 'N/A'}",
        f"- Reorder point: {context.reorder_point if context.reorder_point is not None else 'N/A'}",
        f"- Reorder quantity: {context.reorder_quantity if context.reorder_quantity is not None else 'N/A'}",
        f"- Stockout probability: {context.stockout_probability if context.stockout_probability is not None else 'N/A'}",
        f"- Excess units: {context.excess_units if context.excess_units is not None else 'N/A'}",
        f"- Excess inventory value: {context.excess_inventory_value if context.excess_inventory_value is not None else 'N/A'}",
        f"- Revenue at risk: {context.revenue_at_risk if context.revenue_at_risk is not None else 'N/A'}",
        f"- Profit at risk: {context.profit_at_risk if context.profit_at_risk is not None else 'N/A'}",
        f"- Risk score: {context.risk_score if context.risk_score is not None else 'N/A'}",
        f"- Risk level: {context.risk_level or 'N/A'}",
        f"- Recommendation: {context.recommendation_action or 'N/A'} (priority: {context.recommendation_priority or 'N/A'})",
        f"- Recommendation reasons: {'; '.join(context.recommendation_reasons) if context.recommendation_reasons else 'N/A'}",
    ]
    lines.append("")
    lines.append("Explain what is happening, why, and what the business should pay attention to. Do not invent facts.")
    return "\n".join(lines)


def get_executive_summary(
    request: ExecutiveSummaryRequest,
    *,
    model: str = DEFAULT_MODEL,
) -> GeminiResponse | GeminiFailure:
    if not is_gemini_configured():
        return GeminiFailure(
            error_type="missing_api_key",
            message="Gemini API key is not configured.",
        )
    try:
        prompt = _build_executive_prompt(request)
        return _call_gemini(prompt, model=model)
    except ValueError as exc:
        return GeminiFailure(error_type="configuration_error", message=str(exc))
    except Exception as exc:  # noqa: BLE001
        return GeminiFailure(
            error_type="gemini_api_error",
            message="Gemini request failed.",
            details=str(exc),
        )


def get_product_explanation(
    context: ProductContext,
    *,
    model: str = DEFAULT_MODEL,
) -> GeminiResponse | GeminiFailure:
    if not is_gemini_configured():
        return GeminiFailure(
            error_type="missing_api_key",
            message="Gemini API key is not configured.",
        )
    try:
        prompt = _build_product_prompt(context)
        return _call_gemini(prompt, model=model)
    except ValueError as exc:
        return GeminiFailure(error_type="configuration_error", message=str(exc))
    except Exception as exc:  # noqa: BLE001
        return GeminiFailure(
            error_type="gemini_api_error",
            message="Gemini request failed.",
            details=str(exc),
        )
