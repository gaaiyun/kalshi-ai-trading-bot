#!/usr/bin/env python3
"""
Health Check - Verify all connections and configuration

Usage:
    python scripts/health.py
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_setup import setup_logging, get_trading_logger
from src.clients.kalshi_client import KalshiClient
from src.clients.xai_client import XAIClient
from src.clients.openrouter_client import OpenRouterClient
from src.utils.database import DatabaseManager

logger = get_trading_logger("health")


async def check_health():
    """Run health checks on all components."""
    logger.info("Running health checks...")
    
    all_ok = True
    
    # Check environment variables
    logger.info("\nChecking environment variables...")
    required_vars = ["KALSHI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"]
    for var in required_vars:
        if os.getenv(var):
            logger.info(f"  {var} is set")
        else:
            logger.error(f"  {var} is missing")
            all_ok = False
    
    # Check Kalshi private key file
    key_file = Path("kalshi_private_key")
    if key_file.exists():
        logger.info(f"  kalshi_private_key file found")
    else:
        logger.error(f"  kalshi_private_key file not found")
        all_ok = False
    
    # Check database
    logger.info("\nChecking database...")
    try:
        db = DatabaseManager()
        await db.initialize()
        logger.info("  Database initialized successfully")
    except Exception as e:
        logger.error(f"  Database error: {e}")
        all_ok = False
    
    # Check Kalshi API
    logger.info("\nChecking Kalshi API...")
    try:
        kalshi = KalshiClient()
        balance_resp = await kalshi.get_balance()
        balance = balance_resp.get("balance", 0) / 100.0 if isinstance(balance_resp, dict) else float(balance_resp)
        logger.info(f"  Kalshi API connected - Balance: ${balance:.2f}")
    except Exception as e:
        logger.error(f"  Kalshi API error: {e}")
        all_ok = False
    
    # Check xAI API
    logger.info("\nChecking xAI API (Grok-4)...")
    try:
        xai = XAIClient()
        response = await xai.get_completion(
            prompt="Say 'OK' if you can read this.",
            max_tokens=10
        )
        if response:
            logger.info(f"  xAI API connected")
        else:
            logger.error(f"  xAI API returned empty response")
            all_ok = False
    except Exception as e:
        logger.error(f"  xAI API error: {e}")
        all_ok = False
    
    # Check OpenRouter API
    logger.info("\nChecking OpenRouter API...")
    try:
        openrouter = OpenRouterClient()
        response = await openrouter.get_completion(
            model="anthropic/claude-sonnet-4",
            prompt="Say 'OK' if you can read this.",
            max_tokens=10
        )
        if response:
            logger.info(f"  OpenRouter API connected")
        else:
            logger.error(f"  OpenRouter API returned empty response")
            all_ok = False
    except Exception as e:
        logger.error(f"  OpenRouter API error: {e}")
        all_ok = False
    
    # Summary
    logger.info("\n" + "="*50)
    if all_ok:
        logger.info("All health checks passed!")
    else:
        logger.error("Some health checks failed. Please fix the issues above.")
    logger.info("="*50)
    
    return all_ok


if __name__ == "__main__":
    setup_logging()
    result = asyncio.run(check_health())
    sys.exit(0 if result else 1)
