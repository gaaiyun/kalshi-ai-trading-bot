"""
Tests for the BaseAgent JSON extraction and formatting utilities.

These tests run without any external API or model dependencies.
"""

import pytest
from src.agents.base_agent import BaseAgent


# ---------------------------------------------------------------------------
# Concrete stub for testing the abstract base class
# ---------------------------------------------------------------------------


class StubAgent(BaseAgent):
    """Minimal concrete implementation for testing."""

    AGENT_NAME = "stub"
    AGENT_ROLE = "test"
    SYSTEM_PROMPT = "You are a test agent."

    def _build_prompt(self, market_data: dict, context: dict) -> str:
        return f"Market: {market_data.get('title', 'Unknown')}"

    def _parse_result(self, raw_json: dict) -> dict:
        return {"value": raw_json.get("value", 0)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExtractJson:
    """Test BaseAgent._extract_json() with various input formats."""

    def setup_method(self):
        self.agent = StubAgent()

    def test_json_code_block(self):
        """Should extract JSON from a ```json ... ``` code block."""
        text = 'Here is the result:\n```json\n{"value": 42}\n```\nDone.'
        result = self.agent._extract_json(text)
        assert result == {"value": 42}

    def test_generic_code_block(self):
        """Should extract JSON from a plain ``` ... ``` code block."""
        text = 'Result:\n```\n{"value": 99}\n```'
        result = self.agent._extract_json(text)
        assert result == {"value": 99}

    def test_bare_json_object(self):
        """Should extract a bare JSON object from surrounding text."""
        text = 'The answer is {"value": 7} as you can see.'
        result = self.agent._extract_json(text)
        assert result == {"value": 7}

    def test_json_with_extra_whitespace(self):
        """Should handle JSON with leading/trailing whitespace."""
        text = '```json\n  {"value": 5}  \n```'
        result = self.agent._extract_json(text)
        assert result == {"value": 5}

    def test_no_json_returns_none(self):
        """Should return None when no JSON is found."""
        text = "This response contains no JSON at all."
        result = self.agent._extract_json(text)
        assert result is None

    def test_malformed_json_repaired(self):
        """Should attempt to repair slightly malformed JSON."""
        # Missing closing brace -- json_repair should handle this
        text = '{"value": 10'
        result = self.agent._extract_json(text)
        assert result is not None
        assert result["value"] == 10


class TestClamp:
    """Test BaseAgent.clamp() static method."""

    def test_within_range(self):
        assert BaseAgent.clamp(0.5) == 0.5

    def test_below_minimum(self):
        assert BaseAgent.clamp(-0.1) == 0.0

    def test_above_maximum(self):
        assert BaseAgent.clamp(1.5) == 1.0

    def test_custom_range(self):
        assert BaseAgent.clamp(5, lo=0, hi=10) == 5
        assert BaseAgent.clamp(-1, lo=0, hi=10) == 0
        assert BaseAgent.clamp(15, lo=0, hi=10) == 10

    def test_non_numeric_returns_lo(self):
        assert BaseAgent.clamp("abc") == 0.0


class TestFormatMarketSummary:
    """Test BaseAgent.format_market_summary() static method."""

    def test_basic_summary(self):
        market = {
            "title": "Will it rain?",
            "yes_price": 60,
            "no_price": 40,
            "volume": 5000,
            "days_to_expiry": 3,
            "rules": "Resolves YES if >1mm rain",
        }
        summary = BaseAgent.format_market_summary(market)
        assert "Will it rain?" in summary
        assert "60c" in summary
        assert "40c" in summary
        assert "5,000" in summary

    def test_summary_with_news(self):
        market = {
            "title": "Test",
            "yes_price": 50,
            "no_price": 50,
            "volume": 100,
            "days_to_expiry": 1,
            "rules": "",
            "news_summary": "Breaking news about the event.",
        }
        summary = BaseAgent.format_market_summary(market)
        assert "Breaking news" in summary

    def test_summary_with_missing_fields(self):
        """Should not raise even with minimal data."""
        market = {}
        summary = BaseAgent.format_market_summary(market)
        assert "Unknown Market" in summary


class TestStubAgentAnalyze:
    """Test the analyze() flow through the stub agent."""

    @pytest.mark.asyncio
    async def test_analyze_with_valid_response(self):
        """analyze() should parse a valid JSON response from get_completion."""

        async def mock_completion(prompt: str) -> str:
            return '```json\n{"value": 42}\n```'

        agent = StubAgent()
        result = await agent.analyze(
            market_data={"title": "Test"},
            context={},
            get_completion=mock_completion,
        )
        assert result["value"] == 42
        assert result["_agent"] == "stub"

    @pytest.mark.asyncio
    async def test_analyze_with_none_response(self):
        """analyze() should return an error dict when model returns None."""

        async def mock_completion(prompt: str) -> str:
            return None

        agent = StubAgent()
        result = await agent.analyze(
            market_data={"title": "Test"},
            context={},
            get_completion=mock_completion,
        )
        assert "error" in result
