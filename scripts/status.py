#!/usr/bin/env python3
"""
Status - Check portfolio status and positions

Usage:
    python scripts/status.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.database import DatabaseManager
from src.clients.kalshi_client import KalshiClient
from src.utils.logging_setup import setup_logging, get_trading_logger

logger = get_trading_logger("status")


async def show_status():
    """Display current portfolio status."""
    try:
        # Initialize clients
        db = DatabaseManager()
        kalshi = KalshiClient()
        
        # Get balance (Kalshi returns cents inside a dict)
        balance_resp = await kalshi.get_balance()
        balance = balance_resp.get("balance", 0) / 100.0 if isinstance(balance_resp, dict) else float(balance_resp)
        logger.info(f"Balance: ${balance:.2f}")
        
        # Get open positions
        positions = await db.get_open_positions()
        
        if not positions:
            logger.info("No open positions")
            return
        
        logger.info(f"Open Positions ({len(positions)}):")
        
        total_invested = 0
        total_value = 0
        
        for pos in positions:
            market_ticker = pos.get('market_ticker', 'Unknown')
            side = pos.get('side', 'Unknown')
            quantity = pos.get('quantity', 0)
            entry_price = pos.get('entry_price', 0)
            current_price = pos.get('current_price', entry_price)
            
            invested = quantity * entry_price
            value = quantity * current_price
            pnl = value - invested
            pnl_pct = (pnl / invested * 100) if invested > 0 else 0
            
            total_invested += invested
            total_value += value
            
            logger.info(
                f"  {market_ticker} | {side} | "
                f"Qty: {quantity} | Entry: ${entry_price:.2f} | "
                f"Current: ${current_price:.2f} | "
                f"P&L: ${pnl:.2f} ({pnl_pct:+.1f}%)"
            )
        
        total_pnl = total_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        logger.info(f"\nPortfolio Summary:")
        logger.info(f"  Total Invested: ${total_invested:.2f}")
        logger.info(f"  Current Value: ${total_value:.2f}")
        logger.info(f"  Total P&L: ${total_pnl:.2f} ({total_pnl_pct:+.1f}%)")
        
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(show_status())
