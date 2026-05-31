#!/usr/bin/env python3
"""
Kalshi AI Trading Bot - Main Entry Point

Simplified trading bot for Kalshi prediction markets with multi-agent AI ensemble.

Usage:
    python scripts/trade.py --paper    # Paper trading (no real money)
    python scripts/trade.py --live     # Live trading (real money)
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.trading_bot import KalshiTradingBot
from src.utils.logging_setup import setup_logging, get_trading_logger

logger = get_trading_logger("main")


async def main():
    """Main entry point for the trading bot."""
    parser = argparse.ArgumentParser(description="Kalshi AI Trading Bot")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live trading (real money). Default is paper trading."
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Enable paper trading (no real money). This is the default."
    )
    args = parser.parse_args()

    # Default to paper trading if neither flag is specified
    live_mode = args.live and not args.paper

    if live_mode:
        logger.warning("LIVE TRADING MODE ENABLED - REAL MONEY AT RISK")
        response = input("Are you sure you want to trade with real money? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Live trading cancelled by user")
            return
    else:
        logger.info("Paper trading mode - no real money at risk")

    # Initialize and run the bot
    bot = KalshiTradingBot(live_mode=live_mode)
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
