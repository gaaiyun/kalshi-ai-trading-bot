"""
Paper Trading Signal Tracker

Logs hypothetical trades to SQLite and checks outcomes when markets settle.
No real money is ever risked.
"""

import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


DB_PATH = os.environ.get(
    "PAPER_TRADING_DB",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "paper_trades.db"),
)


@dataclass
class Signal:
    """A single paper-trading signal."""
    id: Optional[int]
    timestamp: str          # ISO-8601
    market_id: str
    market_title: str
    side: str               # YES / NO
    entry_price: float      # 0-1 scale (e.g. 0.85 = 85¢)
    confidence: float       # model confidence 0-1
    reasoning: str
    strategy: str           # e.g. directional, market_making
    # Outcome fields (filled after settlement)
    outcome: Optional[str]  # win / loss / pending
    settlement_price: Optional[float]
    pnl: Optional[float]    # per-contract P&L in dollars
    settled_at: Optional[str]


def _ensure_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            market_id       TEXT NOT NULL,
            market_title    TEXT NOT NULL,
            side            TEXT NOT NULL DEFAULT 'NO',
            entry_price     REAL NOT NULL,
            confidence      REAL,
            reasoning       TEXT,
            strategy        TEXT,
            outcome         TEXT DEFAULT 'pending',
            settlement_price REAL,
            pnl             REAL,
            settled_at      TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_market
        ON signals(market_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_outcome
        ON signals(outcome)
    """)
    conn.commit()


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_db(conn)
    return conn


def log_signal(
    market_id: str,
    market_title: str,
    side: str,
    entry_price: float,
    confidence: float,
    reasoning: str,
    strategy: str = "directional",
) -> int:
    """Record a new paper-trading signal. Returns the signal id."""
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO signals
           (timestamp, market_id, market_title, side, entry_price, confidence, reasoning, strategy)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            market_id,
            market_title,
            side,
            entry_price,
            confidence,
            reasoning,
            strategy,
        ),
    )
    conn.commit()
    signal_id = cur.lastrowid
    conn.close()
    return signal_id


def settle_signal(signal_id: int, settlement_price: float):
    """
    Mark a signal as settled.
    For NO side: profit = entry_price - settlement_price  (you bought NO at entry_price)
    Actually on Kalshi: buying NO at price p means you pay p, and receive $1 if NO wins.
    So PnL = (1 - entry_price) if NO wins, else -entry_price.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,)).fetchone()
    if not row:
        conn.close()
        return

    side = row["side"]
    entry = row["entry_price"]

    if side == "NO":
        # settlement_price is the YES settlement (1.0 if YES wins, 0.0 if NO wins)
        if settlement_price <= 0.5:
            # NO wins
            pnl = 1.0 - entry
            outcome = "win"
        else:
            # YES wins → NO loses
            pnl = -entry
            outcome = "loss"
    else:
        # YES side
        if settlement_price >= 0.5:
            pnl = 1.0 - entry
            outcome = "win"
        else:
            pnl = -entry
            outcome = "loss"

    conn.execute(
        """UPDATE signals
           SET outcome = ?, settlement_price = ?, pnl = ?, settled_at = ?
           WHERE id = ?""",
        (outcome, settlement_price, round(pnl, 4), datetime.now(timezone.utc).isoformat(), signal_id),
    )
    conn.commit()
    conn.close()


def get_pending_signals() -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM signals WHERE outcome = 'pending' ORDER BY timestamp").fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result


def get_all_signals() -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM signals ORDER BY timestamp DESC").fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result


def get_stats() -> Dict[str, Any]:
    """Compute summary statistics over all settled signals."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM signals WHERE outcome != 'pending'").fetchall()
    settled = [dict(r) for r in rows]
    pending = conn.execute("SELECT COUNT(*) FROM signals WHERE outcome = 'pending'").fetchone()[0]
    conn.close()

    if not settled:
        return {
            "total_signals": pending,
            "settled": 0,
            "pending": pending,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_return": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
        }

    wins = sum(1 for s in settled if s["outcome"] == "win")
    losses = sum(1 for s in settled if s["outcome"] == "loss")
    pnls = [s["pnl"] for s in settled if s["pnl"] is not None]
    total_pnl = sum(pnls)

    return {
        "total_signals": len(settled) + pending,
        "settled": len(settled),
        "pending": pending,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(settled) * 100, 1) if settled else 0.0,
        "total_pnl": round(total_pnl, 2),
        "avg_return": round(total_pnl / len(settled), 4) if settled else 0.0,
        "best_trade": round(max(pnls), 4) if pnls else 0.0,
        "worst_trade": round(min(pnls), 4) if pnls else 0.0,
    }


class PaperTracker:
    """
    Async-friendly facade over the paper-trading signal store.

    `scripts/paper_trade.py` drives this class. The methods that touch the
    signal database (statistics, settlement bookkeeping) work with no
    credentials. Methods that need live market data (`scan_and_log`,
    `update_settled_markets`) use a real Kalshi client when one is available
    and raise a clear error otherwise instead of inventing data.
    """

    def __init__(self, kalshi_client=None):
        self._kalshi = kalshi_client

    def _get_kalshi(self):
        """Lazily build a KalshiClient; surfaces a clear error if it can't."""
        if self._kalshi is not None:
            return self._kalshi
        # Imported lazily so the stats/dashboard paths never require the
        # Kalshi client (and its private-key file) to be available.
        from src.clients.kalshi_client import KalshiClient

        self._kalshi = KalshiClient()
        return self._kalshi

    async def get_statistics(self) -> Dict[str, Any]:
        """Return summary statistics in the shape the CLI expects."""
        stats = get_stats()
        # The CLI prints avg_pnl; expose it as an alias of avg_return.
        stats["avg_pnl"] = stats.get("avg_return", 0.0)
        return stats

    async def scan_and_log(self) -> int:
        """
        Fetch live open markets from Kalshi and record paper-trading signals.

        Requires Kalshi API credentials and an AI client to score markets.
        Without an AI scorer wired in we deliberately log nothing rather than
        fabricate signals; the caller is told why.

        Returns the number of signals logged.
        """
        kalshi = self._get_kalshi()
        markets_resp = await kalshi.get_markets(limit=100, status="open")
        markets = markets_resp.get("markets", []) if isinstance(markets_resp, dict) else []

        scored = await self._score_markets(markets)
        logged = 0
        for market_id, market_title, side, entry_price, confidence, reasoning in scored:
            log_signal(
                market_id=market_id,
                market_title=market_title,
                side=side,
                entry_price=entry_price,
                confidence=confidence,
                reasoning=reasoning,
                strategy="directional",
            )
            logged += 1
        return logged

    async def _score_markets(self, markets):
        """
        Hook for turning live markets into signals.

        The probability model (AI ensemble) is not wired into the paper
        tracker, so by default this returns no signals and explains that an
        AI scorer is required. Subclasses or callers can override this to
        plug in their own scoring without changing the rest of the pipeline.
        """
        raise RuntimeError(
            "No AI scorer is configured for paper scanning. "
            "Fetched %d live markets but cannot generate signals without a "
            "probability model. Use --stats/--dashboard/--settle to work with "
            "previously logged signals." % len(markets)
        )

    async def update_settled_markets(self) -> int:
        """
        Settle any pending signals whose markets have resolved on Kalshi.

        Returns the number of signals that were newly settled.
        """
        pending = get_pending_signals()
        if not pending:
            return 0

        kalshi = self._get_kalshi()
        settled_count = 0
        for sig in pending:
            market_id = sig["market_id"]
            try:
                resp = await kalshi.get_market(market_id)
            except Exception:
                continue
            market = resp.get("market", {}) if isinstance(resp, dict) else {}
            if market.get("status") != "settled":
                continue
            # Kalshi reports the settled result as "yes" or "no".
            result = market.get("result")
            if result == "yes":
                settlement_price = 1.0
            elif result == "no":
                settlement_price = 0.0
            else:
                continue
            settle_signal(sig["id"], settlement_price)
            settled_count += 1
        return settled_count
