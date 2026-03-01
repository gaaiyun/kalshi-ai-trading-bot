#!/usr/bin/env python3
"""
Paper Trading - Test strategies without risking real money

Usage:
    python scripts/paper_trade.py                    # Single scan
    python scripts/paper_trade.py --loop             # Continuous scanning
    python scripts/paper_trade.py --settle           # Update settled markets
    python scripts/paper_trade.py --dashboard        # Generate HTML dashboard
    python scripts/paper_trade.py --stats            # Print statistics
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.paper.tracker import PaperTracker
from src.paper.dashboard import generate_dashboard
from src.utils.logging_setup import setup_logging, get_trading_logger

logger = get_trading_logger("paper_trade")


async def main():
    """Main entry point for paper trading."""
    parser = argparse.ArgumentParser(description="Kalshi Paper Trading")
    parser.add_argument("--loop", action="store_true", help="Continuous scanning")
    parser.add_argument("--interval", type=int, default=900, help="Scan interval in seconds (default: 900)")
    parser.add_argument("--settle", action="store_true", help="Check and update settled markets")
    parser.add_argument("--dashboard", action="store_true", help="Generate HTML dashboard")
    parser.add_argument("--stats", action="store_true", help="Print statistics")
    args = parser.parse_args()

    tracker = PaperTracker()

    try:
        if args.settle:
            logger.info("📊 Checking settled markets...")
            await tracker.update_settled_markets()
            logger.info("✅ Settled markets updated")
        
        elif args.dashboard:
            logger.info("📈 Generating dashboard...")
            generate_dashboard()
            logger.info("✅ Dashboard generated: docs/paper_dashboard.html")
        
        elif args.stats:
            logger.info("📊 Paper Trading Statistics:")
            stats = await tracker.get_statistics()
            logger.info(f"  Total Signals: {stats['total_signals']}")
            logger.info(f"  Win Rate: {stats['win_rate']:.1f}%")
            logger.info(f"  Total P&L: ${stats['total_pnl']:.2f}")
            logger.info(f"  Avg P&L per Trade: ${stats['avg_pnl']:.2f}")
        
        elif args.loop:
            logger.info(f"🔄 Starting continuous scanning (interval: {args.interval}s)")
            while True:
                await tracker.scan_and_log()
                logger.info(f"⏳ Waiting {args.interval} seconds...")
                await asyncio.sleep(args.interval)
        
        else:
            logger.info("📝 Scanning markets for signals...")
            await tracker.scan_and_log()
            logger.info("✅ Scan complete")

    except KeyboardInterrupt:
        logger.info("Paper trading stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
