"""
Tests for Phase 3 — Query Orchestrator & Workflows.
Covers intent routing, deterministic structured data tool, and abstention behavior.
"""
import pytest
from app.services.orchestration.router import (
    classify_intent,
    ROUTE_RETRIEVE,
    ROUTE_SQL,
    ROUTE_SUMMARIZE,
    ROUTE_WORKFLOW,
    ROUTE_UNSUPPORTED,
)
from app.services.orchestration.data_tool import _markdown_to_df


class TestIntentClassifier:
    def test_unsupported_routing(self):
        decision = classify_intent("Can you please book a flight to New York for me?")
        assert decision.route == ROUTE_UNSUPPORTED
        assert decision.confidence >= 0.9

    def test_summarization_routing(self):
        decision = classify_intent("Provide a brief executive summary of this quarterly report")
        assert decision.route == ROUTE_SUMMARIZE
        assert decision.confidence >= 0.8

    def test_structured_data_sql_routing(self):
        decision = classify_intent("What is the total revenue and average margin breakdown per year?")
        assert decision.route == ROUTE_SQL
        assert decision.confidence >= 0.8

    def test_multi_step_routing(self):
        decision = classify_intent("First summarize section 4 and then compare it with the previous year")
        assert decision.route == ROUTE_WORKFLOW

    def test_default_retrieval_routing(self):
        decision = classify_intent("What is the mandatory data retention period under SOC2?")
        assert decision.route == ROUTE_RETRIEVE


class TestStructuredDataTool:
    def test_markdown_table_parsing(self):
        md = """
        | Region | Revenue | Margin_Pct |
        |---|---|---|
        | NA | 48.6 | 24.2 |
        | EMEA | 31.2 | 19.8 |
        """
        df = _markdown_to_df(md)
        assert df is not None
        assert len(df) == 2
        assert "Revenue" in df.columns or "revenue" in [c.lower() for c in df.columns]

    def test_invalid_markdown_returns_none(self):
        assert _markdown_to_df("Just some regular text without table bars") is None
