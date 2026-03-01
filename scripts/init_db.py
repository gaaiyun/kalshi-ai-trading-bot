"""
Simplified database manager for testing without API keys
"""

import sqlite3
import asyncio
from pathlib import Path


async def initialize_database():
    """Initialize the trading database with required tables."""
    db_path = Path("trading_system.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create positions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_ticker TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL,
            entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            exit_time TIMESTAMP,
            exit_price REAL,
            exit_reason TEXT,
            pnl REAL,
            pnl_pct REAL,
            status TEXT DEFAULT 'open',
            confidence REAL,
            order_id TEXT
        )
    """)
    
    # Create trades table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_ticker TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confidence REAL,
            order_id TEXT,
            ai_result TEXT
        )
    """)
    
    # Create paper_trades table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_ticker TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            entry_price REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confidence REAL,
            ai_result TEXT,
            settled BOOLEAN DEFAULT 0,
            outcome TEXT,
            pnl REAL
        )
    """)
    
    # Create statistics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE DEFAULT CURRENT_DATE,
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            total_pnl REAL DEFAULT 0,
            daily_cost REAL DEFAULT 0,
            sharpe_ratio REAL
        )
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized: {db_path}")


if __name__ == "__main__":
    asyncio.run(initialize_database())
