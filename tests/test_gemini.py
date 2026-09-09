from __future__ import annotations

import os
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from google import genai
from google.genai import types as genai_types

from gemini import (
    DEFAULT_MODEL,
    ExecutiveSummaryRequest,
    GeminiFailure,
    GeminiResponse,
    ProductContext,
    get_executive_summary,
    get_product_explanation,
)


def _mock_genai_client(*, text: str = "Mocked Gemini response"):
    mock_client = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    mock_part.text = text
    mock_candidate.content.parts = [mock_part]
    mock_candidate.finish_reason = "STOP"
    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


def test_executive_summary_request_contains_no_raw_csv():
    request = ExecutiveSummaryRequest(
        overall_health_status="ATTENTION",
        overall_risk_score=55.0,
        total_products=10,
        products_at_risk=3,
        high_risk_categories=1,
        total_categories=2,
        total_stockout_exposure=500.0,
        total_excess_inventory_value=200.0,
        total_capital_tied_up=1000.0,
        total_revenue_at_risk=300.0,
        total_profit_at_risk=150.0,
        category_risk_levels=["MEDIUM", "HIGH"],
    )
    assert "csv" not in str(request).lower()
    assert "dataset" not in str(request).lower()


def test_product_context_contains_no_raw_csv():
    context = ProductContext(
        product="Widget A",
        category="General",
        mean_demand=10.0,
        cv=0.3,
        trend="INCREASING",
        current_inventory=40.0,
        days_remaining=4.0,
        stockout_probability=0.8,
        risk_level="HIGH",
        recommendation_action="REORDER",
        recommendation_priority="HIGH",
        recommendation_reasons=["Demand is increasing and coverage is below lead time."],
        recommendation_evidence={"stockout_probability": 0.8},
    )
    assert "csv" not in str(context).lower()
    assert "dataset" not in str(context).lower()


def test_executive_summary_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with patch("gemini.is_gemini_configured", return_value=False):
        result = get_executive_summary(ExecutiveSummaryRequest())
    assert isinstance(result, GeminiFailure)
    assert result.error_type == "missing_api_key"
    assert "Gemini API key is not configured" in result.message


def test_product_explanation_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with patch("gemini.is_gemini_configured", return_value=False):
        result = get_product_explanation(ProductContext(product="Widget A", category="General"))
    assert isinstance(result, GeminiFailure)
    assert result.error_type == "missing_api_key"


@patch("gemini.is_gemini_configured", return_value=True)
@patch("gemini._get_client")
def test_executive_summary_success(mock_get_client, _mock_configured):
    mock_client = _mock_genai_client(text="Business is stable but watch high-risk categories.")
    mock_get_client.return_value = mock_client

    request = ExecutiveSummaryRequest(
        overall_health_status="ATTENTION",
        overall_risk_score=55.0,
        total_products=10,
        products_at_risk=3,
        high_risk_categories=1,
        total_categories=2,
        category_risk_levels=["MEDIUM", "HIGH"],
    )
    result = get_executive_summary(request, model=DEFAULT_MODEL)
    assert isinstance(result, GeminiResponse)
    assert result.text.strip()
    assert result.model == DEFAULT_MODEL
    assert mock_client.models.generate_content.called


@patch("gemini.is_gemini_configured", return_value=True)
@patch("gemini._get_client")
def test_product_explanation_success(mock_get_client, _mock_configured):
    mock_client = _mock_genai_client(text="Product is at risk due to increasing demand and low coverage.")
    mock_get_client.return_value = mock_client

    context = ProductContext(
        product="Widget A",
        category="General",
        mean_demand=10.0,
        cv=0.3,
        trend="INCREASING",
        current_inventory=40.0,
        days_remaining=4.0,
        lead_time_days=7.0,
        stockout_probability=0.8,
        risk_level="HIGH",
        recommendation_action="REORDER",
        recommendation_priority="HIGH",
        recommendation_reasons=["Demand is increasing and coverage is below lead time."],
        recommendation_evidence={"stockout_probability": 0.8},
    )
    result = get_product_explanation(context, model=DEFAULT_MODEL)
    assert isinstance(result, GeminiResponse)
    assert result.text.strip()
    assert result.model == DEFAULT_MODEL
    assert mock_client.models.generate_content.called


@patch("gemini.is_gemini_configured", return_value=True)
@patch("gemini._get_client")
def test_gemini_api_failure_returns_failure(mock_get_client, _mock_configured):
    mock_get_client.side_effect = RuntimeError("API error")
    result = get_executive_summary(ExecutiveSummaryRequest())
    assert isinstance(result, GeminiFailure)
    assert result.error_type == "gemini_api_error"
    assert "Gemini request failed" in result.message


@patch("gemini.is_gemini_configured", return_value=True)
@patch("gemini._get_client")
def test_gemini_empty_response_returns_empty_text(mock_get_client, _mock_configured):
    mock_client = _mock_genai_client(text="")
    mock_get_client.return_value = mock_client

    result = get_executive_summary(ExecutiveSummaryRequest())
    assert isinstance(result, GeminiResponse)
    assert result.text == ""


@patch("gemini.is_gemini_configured", return_value=True)
@patch("gemini._get_client")
def test_gemini_model_name_is_configurable(mock_get_client, _mock_configured):
    mock_client = _mock_genai_client()
    mock_get_client.return_value = mock_client

    get_executive_summary(ExecutiveSummaryRequest(), model="custom-model")
    assert mock_client.models.generate_content.call_args[1]["model"] == "custom-model"


def test_default_model_is_known():
    assert DEFAULT_MODEL == "gemini-2.0-flash"


def test_gemini_response_attributes():
    response = GeminiResponse(text="Hello", model="gemini-2.0-flash", finish_reason="STOP")
    assert response.text == "Hello"
    assert response.model == "gemini-2.0-flash"
    assert response.finish_reason == "STOP"


def test_gemini_failure_attributes():
    failure = GeminiFailure(error_type="missing_api_key", message="No key", details="detail")
    assert failure.error_type == "missing_api_key"
    assert failure.message == "No key"
    assert failure.details == "detail"


def test_product_context_defaults():
    context = ProductContext(product="Widget A", category="General")
    assert context.mean_demand is None
    assert context.recommendation_reasons == []
    assert context.recommendation_evidence == {}


def test_executive_summary_request_defaults():
    request = ExecutiveSummaryRequest()
    assert request.overall_health_status is None
    assert request.total_products == 0
    assert request.products == []
