"""
Tests for the EdgeFilter module.

These tests validate the edge-based filtering logic used across all
trading strategies. They run without any external API dependencies.
"""

import pytest
from src.utils.edge_filter import (
    EdgeFilter,
    EdgeFilterResult,
    calculate_edge,
    passes_edge_filter,
    get_minimum_edge_for_confidence,
)


class TestEdgeFilterCalculate:
    """Test EdgeFilter.calculate_edge()"""

    def test_yes_side_when_ai_higher(self):
        """When AI probability > market probability, side should be YES."""
        result = EdgeFilter.calculate_edge(ai_probability=0.70, market_probability=0.55)
        assert result.side == "YES"
        assert result.edge_magnitude > 0

    def test_no_side_when_ai_lower(self):
        """When AI probability < market probability, side should be NO."""
        result = EdgeFilter.calculate_edge(ai_probability=0.35, market_probability=0.55)
        assert result.side == "NO"
        assert result.edge_magnitude < 0

    def test_edge_percentage_is_absolute(self):
        """edge_percentage should always be non-negative."""
        result = EdgeFilter.calculate_edge(ai_probability=0.30, market_probability=0.55)
        assert result.edge_percentage >= 0

    def test_high_confidence_low_edge_passes(self):
        """High confidence with sufficient edge should pass."""
        result = EdgeFilter.calculate_edge(
            ai_probability=0.70, market_probability=0.58, confidence=0.85
        )
        assert result.passes_filter is True

    def test_low_confidence_rejected(self):
        """Below minimum confidence should always fail."""
        result = EdgeFilter.calculate_edge(
            ai_probability=0.80, market_probability=0.50, confidence=0.40
        )
        assert result.passes_filter is False
        assert "Confidence" in result.reason

    def test_small_edge_rejected(self):
        """Edge too small for the confidence level should fail."""
        result = EdgeFilter.calculate_edge(
            ai_probability=0.52, market_probability=0.50, confidence=0.55
        )
        assert result.passes_filter is False

    def test_input_clamping(self):
        """Extreme inputs should be clamped to valid range."""
        result = EdgeFilter.calculate_edge(
            ai_probability=0.0, market_probability=1.0, confidence=0.80
        )
        # Should not raise; values clamped internally
        assert 0.0 <= result.edge_percentage <= 1.0

    def test_confidence_adjusted_edge(self):
        """confidence_adjusted_edge = edge_percentage * confidence."""
        result = EdgeFilter.calculate_edge(
            ai_probability=0.70, market_probability=0.50, confidence=0.80
        )
        expected = result.edge_percentage * 0.80
        assert abs(result.confidence_adjusted_edge - expected) < 1e-9


class TestEdgeFilterThresholds:
    """Test that confidence-based thresholds are applied correctly."""

    def test_high_confidence_threshold(self):
        """High confidence (>=0.8) should use HIGH_CONFIDENCE_EDGE."""
        threshold = get_minimum_edge_for_confidence(0.85)
        assert threshold == EdgeFilter.HIGH_CONFIDENCE_EDGE

    def test_medium_confidence_threshold(self):
        """Medium confidence (>=0.6) should use MEDIUM_CONFIDENCE_EDGE."""
        threshold = get_minimum_edge_for_confidence(0.65)
        assert threshold == EdgeFilter.MEDIUM_CONFIDENCE_EDGE

    def test_low_confidence_threshold(self):
        """Low confidence (<0.6) should use LOW_CONFIDENCE_EDGE."""
        threshold = get_minimum_edge_for_confidence(0.50)
        assert threshold == EdgeFilter.LOW_CONFIDENCE_EDGE


class TestFilterOpportunities:
    """Test EdgeFilter.filter_opportunities()"""

    def test_filters_out_weak_opportunities(self):
        """Opportunities below edge threshold should be removed."""
        opportunities = [
            {"predicted_probability": 0.70, "market_probability": 0.55, "confidence": 0.80},
            {"predicted_probability": 0.52, "market_probability": 0.50, "confidence": 0.55},
        ]
        filtered = EdgeFilter.filter_opportunities(opportunities)
        assert len(filtered) == 1
        assert filtered[0]["predicted_probability"] == 0.70

    def test_disable_filter_returns_all(self):
        """With require_edge_filter=False, all opportunities pass."""
        opportunities = [
            {"predicted_probability": 0.51, "market_probability": 0.50, "confidence": 0.55},
        ]
        filtered = EdgeFilter.filter_opportunities(opportunities, require_edge_filter=False)
        assert len(filtered) == 1

    def test_empty_list_returns_empty(self):
        """Empty input should return empty output."""
        assert EdgeFilter.filter_opportunities([]) == []


class TestShouldTradeMarket:
    """Test EdgeFilter.should_trade_market()"""

    def test_trade_approved_when_conditions_met(self):
        """Should approve trade when edge and confidence are sufficient."""
        should_trade, reason, edge_result = EdgeFilter.should_trade_market(
            ai_probability=0.75,
            market_probability=0.55,
            confidence=0.85,
        )
        assert should_trade is True
        assert "TRADE APPROVED" in reason

    def test_trade_rejected_low_edge(self):
        """Should reject when edge is too small."""
        should_trade, reason, edge_result = EdgeFilter.should_trade_market(
            ai_probability=0.52,
            market_probability=0.50,
            confidence=0.85,
        )
        assert should_trade is False

    def test_trade_rejected_low_volume(self):
        """Should reject when volume is below minimum."""
        should_trade, reason, edge_result = EdgeFilter.should_trade_market(
            ai_probability=0.75,
            market_probability=0.55,
            confidence=0.85,
            additional_filters={"volume": 100, "min_volume": 1000},
        )
        assert should_trade is False
        assert "Volume" in reason


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_calculate_edge_convenience(self):
        """calculate_edge() should delegate to EdgeFilter.calculate_edge()."""
        result = calculate_edge(0.70, 0.50, 0.80)
        assert isinstance(result, EdgeFilterResult)

    def test_passes_edge_filter_true(self):
        """passes_edge_filter() returns True for good edge."""
        assert passes_edge_filter(0.75, 0.55, 0.85) is True

    def test_passes_edge_filter_false(self):
        """passes_edge_filter() returns False for poor edge."""
        assert passes_edge_filter(0.52, 0.50, 0.55) is False
