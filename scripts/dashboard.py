#!/usr/bin/env python3
"""
Dashboard - Real-time monitoring for Kalshi trading bot

Usage:
    python scripts/dashboard.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard.app import run_dashboard

if __name__ == "__main__":
    run_dashboard()
