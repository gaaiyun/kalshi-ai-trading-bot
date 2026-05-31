"""
Tests for the paper-trading CLI surface (scripts/paper_trade.py) and the
supporting paper module API it depends on.

These tests reproduce the import/attribute defects that previously made the
entire paper-trading CLI unrunnable, and lock in the behaviour of the
statistics / dashboard / settlement paths against a temporary signal store.
"""

import importlib
import os

import pytest


@pytest.fixture
def tmp_paper_db(tmp_path, monkeypatch):
    """Point the paper tracker at a throwaway database for each test."""
    db_file = tmp_path / "paper_trades.db"
    monkeypatch.setenv("PAPER_TRADING_DB", str(db_file))

    # The DB path is resolved at import time, so reload the module to pick up
    # the patched environment variable.
    import src.paper.tracker as tracker
    importlib.reload(tracker)
    yield tracker
    # Restore the module to its default state for other tests.
    monkeypatch.delenv("PAPER_TRADING_DB", raising=False)
    importlib.reload(tracker)


class TestPaperModuleApi:
    """The symbols that scripts/paper_trade.py imports must actually exist."""

    def test_paper_tracker_class_exists(self):
        from src.paper.tracker import PaperTracker

        tracker = PaperTracker()
        # The CLI calls these three async methods.
        assert hasattr(tracker, "scan_and_log")
        assert hasattr(tracker, "update_settled_markets")
        assert hasattr(tracker, "get_statistics")

    def test_generate_dashboard_exists(self):
        from src.paper.dashboard import generate_dashboard

        assert callable(generate_dashboard)

    def test_paper_trade_script_imports(self):
        """Importing the CLI module must not raise (regression for ImportError)."""
        import importlib.util
        from pathlib import Path

        script = Path(__file__).resolve().parent.parent / "scripts" / "paper_trade.py"
        spec = importlib.util.spec_from_file_location("paper_trade_cli", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "main")


class TestPaperTrackerStatistics:
    """get_statistics() must return the keys the CLI prints."""

    @pytest.mark.asyncio
    async def test_statistics_empty(self, tmp_paper_db):
        from src.paper.tracker import PaperTracker

        stats = await PaperTracker().get_statistics()
        for key in ("total_signals", "win_rate", "total_pnl", "avg_pnl"):
            assert key in stats

    @pytest.mark.asyncio
    async def test_statistics_after_settled_signal(self, tmp_paper_db):
        from src.paper.tracker import PaperTracker, log_signal, settle_signal

        sig_id = log_signal(
            market_id="MKT-1",
            market_title="Test market",
            side="YES",
            entry_price=0.40,
            confidence=0.8,
            reasoning="unit test",
            strategy="directional",
        )
        # YES wins -> pnl = 1 - 0.40 = 0.60
        settle_signal(sig_id, settlement_price=1.0)

        stats = await PaperTracker().get_statistics()
        assert stats["total_signals"] == 1
        assert stats["win_rate"] == 100.0
        assert abs(stats["total_pnl"] - 0.60) < 1e-6
        assert abs(stats["avg_pnl"] - 0.60) < 1e-6


class TestGenerateDashboard:
    """generate_dashboard() must write the documented HTML file."""

    def test_generate_dashboard_writes_file(self, tmp_paper_db, tmp_path):
        from src.paper.dashboard import generate_dashboard

        out = tmp_path / "paper_dashboard.html"
        path = generate_dashboard(str(out))
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            html = f.read()
        assert "Paper Trading Dashboard" in html
