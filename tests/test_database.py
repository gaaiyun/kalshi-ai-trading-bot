"""
Tests for the DatabaseManager.

Validates table creation, migrations, and core CRUD operations.
Uses an in-memory SQLite database so no external services are needed.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from src.utils.database import (
    DatabaseManager,
    Market,
    Position,
    TradeLog,
    LLMQuery,
)


@pytest.fixture
def tmp_db_path(tmp_path):
    """Return a temporary database path."""
    return str(tmp_path / "test_trading.db")


@pytest_asyncio.fixture
async def db(tmp_db_path):
    """Create and initialize a DatabaseManager with a temp database."""
    manager = DatabaseManager(db_path=tmp_db_path)
    await manager.initialize()
    yield manager


class TestTableCreation:
    """Verify all tables are created on initialize."""

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, tmp_db_path):
        """initialize() should create the expected tables without error."""
        manager = DatabaseManager(db_path=tmp_db_path)
        await manager.initialize()
        # If we get here without exception, tables were created
        assert os.path.exists(tmp_db_path)


class TestMarketOperations:
    """Test market-related database operations."""

    @pytest.mark.asyncio
    async def test_upsert_markets(self, db):
        """Upserting markets should insert them into the database."""
        markets = [
            Market(
                market_id="TEST-001",
                title="Test Market",
                yes_price=55.0,
                no_price=45.0,
                volume=1000,
                expiration_ts=int((datetime.now() + timedelta(days=7)).timestamp()),
                category="politics",
                status="active",
                last_updated=datetime.now(),
            )
        ]
        await db.upsert_markets(markets)

        # Verify by fetching eligible markets
        result = await db.get_eligible_markets(volume_min=100, max_days_to_expiry=30)
        assert len(result) == 1
        assert result[0].market_id == "TEST-001"

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, db):
        """Upserting the same market_id should update, not duplicate."""
        now = datetime.now()
        expiry_ts = int((now + timedelta(days=7)).timestamp())

        markets_v1 = [
            Market(
                market_id="TEST-002", title="V1", yes_price=50.0, no_price=50.0,
                volume=500, expiration_ts=expiry_ts, category="sports",
                status="active", last_updated=now,
            )
        ]
        await db.upsert_markets(markets_v1)

        markets_v2 = [
            Market(
                market_id="TEST-002", title="V2", yes_price=60.0, no_price=40.0,
                volume=800, expiration_ts=expiry_ts, category="sports",
                status="active", last_updated=now,
            )
        ]
        await db.upsert_markets(markets_v2)

        result = await db.get_eligible_markets(volume_min=100, max_days_to_expiry=30)
        assert len(result) == 1
        assert result[0].title == "V2"
        assert result[0].yes_price == 60.0


class TestPositionOperations:
    """Test position-related database operations."""

    @pytest.mark.asyncio
    async def test_add_position(self, db):
        """Adding a position should return an ID and persist the data."""
        position = Position(
            market_id="MKT-001",
            side="YES",
            entry_price=55.0,
            quantity=10,
            timestamp=datetime.now(),
            rationale="Test trade",
            confidence=0.75,
        )
        pos_id = await db.add_position(position)
        assert pos_id is not None

        open_positions = await db.get_open_positions()
        assert len(open_positions) == 1
        assert open_positions[0].market_id == "MKT-001"

    @pytest.mark.asyncio
    async def test_duplicate_position_rejected(self, db):
        """Adding a duplicate market+side position should return None."""
        position = Position(
            market_id="MKT-002", side="YES", entry_price=50.0,
            quantity=5, timestamp=datetime.now(),
        )
        first_id = await db.add_position(position)
        assert first_id is not None

        second_id = await db.add_position(position)
        assert second_id is None

    @pytest.mark.asyncio
    async def test_update_position_status(self, db):
        """Updating position status should change it in the database."""
        position = Position(
            market_id="MKT-003", side="YES", entry_price=50.0,
            quantity=5, timestamp=datetime.now(),
        )
        pos_id = await db.add_position(position)

        await db.update_position_status(pos_id, "closed")

        # The position should no longer appear in open positions
        open_positions = await db.get_open_positions()
        assert len(open_positions) == 0


class TestTradeLogOperations:
    """Test trade log operations."""

    @pytest.mark.asyncio
    async def test_add_trade_log(self, db):
        """Adding a trade log should persist it."""
        log = TradeLog(
            market_id="MKT-001",
            side="YES",
            entry_price=50.0,
            exit_price=60.0,
            quantity=10,
            pnl=100.0,
            entry_timestamp=datetime.now() - timedelta(hours=1),
            exit_timestamp=datetime.now(),
            rationale="Test exit",
            strategy="directional_trading",
        )
        await db.add_trade_log(log)

        all_logs = await db.get_all_trade_logs()
        assert len(all_logs) == 1
        assert all_logs[0].pnl == 100.0


class TestLLMQueryLogging:
    """Test LLM query logging."""

    @pytest.mark.asyncio
    async def test_log_and_retrieve_llm_query(self, db):
        """Logging an LLM query should make it retrievable."""
        query = LLMQuery(
            timestamp=datetime.now(),
            strategy="forecaster",
            query_type="market_analysis",
            market_id="MKT-001",
            prompt="Analyze this market",
            response='{"probability": 0.7}',
            tokens_used=500,
            cost_usd=0.005,
            confidence_extracted=0.7,
            decision_extracted="BUY",
        )
        await db.log_llm_query(query)

        queries = await db.get_llm_queries(strategy="forecaster", hours_back=1)
        assert len(queries) == 1
        assert queries[0].strategy == "forecaster"


class TestDashboardReads:
    """Methods consumed by the Streamlit dashboard must exist and aggregate."""

    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, db):
        stats = await db.get_statistics()
        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0.0
        assert stats["total_pnl"] == 0.0

    @pytest.mark.asyncio
    async def test_get_statistics_and_recent_trades(self, db):
        await db.add_trade_log(
            TradeLog(
                market_id="MKT-W", side="YES", entry_price=40.0, exit_price=60.0,
                quantity=10, pnl=200.0,
                entry_timestamp=datetime.now() - timedelta(hours=2),
                exit_timestamp=datetime.now() - timedelta(hours=1),
                rationale="winner", strategy="directional_trading",
            )
        )
        await db.add_trade_log(
            TradeLog(
                market_id="MKT-L", side="NO", entry_price=55.0, exit_price=45.0,
                quantity=5, pnl=-50.0,
                entry_timestamp=datetime.now() - timedelta(hours=2),
                exit_timestamp=datetime.now(),
                rationale="loser", strategy="directional_trading",
            )
        )

        stats = await db.get_statistics()
        assert stats["total_trades"] == 2
        assert stats["winning_trades"] == 1
        assert stats["win_rate"] == 50.0
        assert abs(stats["total_pnl"] - 150.0) < 1e-9

        recent = await db.get_recent_trades(limit=10)
        assert len(recent) == 2
        # Most recent (MKT-L) should come first.
        assert recent[0]["market_ticker"] == "MKT-L"
        assert all("price" in t for t in recent)


class TestCostTracking:
    """Test daily cost tracking."""

    @pytest.mark.asyncio
    async def test_record_and_get_daily_cost(self, db):
        """Recording market analyses should accumulate daily cost."""
        await db.record_market_analysis(
            market_id="MKT-001",
            decision_action="BUY",
            confidence=0.75,
            cost_usd=0.05,
        )
        await db.record_market_analysis(
            market_id="MKT-002",
            decision_action="SKIP",
            confidence=0.40,
            cost_usd=0.03,
        )

        daily_cost = await db.get_daily_ai_cost()
        assert abs(daily_cost - 0.08) < 1e-9

    @pytest.mark.asyncio
    async def test_was_recently_analyzed(self, db):
        """was_recently_analyzed should return True after analysis."""
        assert await db.was_recently_analyzed("MKT-NEW") is False

        await db.record_market_analysis(
            market_id="MKT-NEW",
            decision_action="BUY",
            confidence=0.75,
            cost_usd=0.05,
        )

        assert await db.was_recently_analyzed("MKT-NEW", hours=1) is True
