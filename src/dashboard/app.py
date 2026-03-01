"""
Dashboard - Real-time monitoring for Kalshi trading bot
"""

import streamlit as st
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

from src.utils.database import DatabaseManager
from src.clients.kalshi_client import KalshiClient
from src.utils.logging_setup import get_trading_logger

logger = get_trading_logger("dashboard")


def run_dashboard():
    """Run the Streamlit dashboard."""
    st.set_page_config(
        page_title="Kalshi Trading Bot",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 Kalshi AI Trading Bot Dashboard")
    
    # Initialize clients
    db = DatabaseManager()
    kalshi = KalshiClient()
    
    # Sidebar
    st.sidebar.header("Settings")
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 5, 60, 10)
    
    # Main content
    col1, col2, col3 = st.columns(3)
    
    # Get data
    try:
        balance = asyncio.run(kalshi.get_balance())
        positions = asyncio.run(db.get_open_positions())
        stats = asyncio.run(db.get_statistics())
        
        # Display metrics
        with col1:
            st.metric("💰 Balance", f"${balance:.2f}")
        
        with col2:
            st.metric("📊 Open Positions", len(positions))
        
        with col3:
            total_pnl = stats.get('total_pnl', 0)
            st.metric("💵 Total P&L", f"${total_pnl:.2f}")
        
        # Positions table
        st.header("Open Positions")
        if positions:
            position_data = []
            for pos in positions:
                position_data.append({
                    "Market": pos.get('market_ticker', 'Unknown'),
                    "Side": pos.get('side', 'Unknown').upper(),
                    "Quantity": pos.get('quantity', 0),
                    "Entry Price": f"${pos.get('entry_price', 0):.2f}",
                    "Current Price": f"${pos.get('current_price', 0):.2f}",
                    "P&L": f"${pos.get('pnl', 0):.2f}",
                    "P&L %": f"{pos.get('pnl_pct', 0):.1f}%"
                })
            st.dataframe(position_data, use_container_width=True)
        else:
            st.info("No open positions")
        
        # Recent trades
        st.header("Recent Trades")
        recent_trades = asyncio.run(db.get_recent_trades(limit=10))
        if recent_trades:
            trade_data = []
            for trade in recent_trades:
                trade_data.append({
                    "Time": trade.get('timestamp', ''),
                    "Market": trade.get('market_ticker', 'Unknown'),
                    "Side": trade.get('side', 'Unknown').upper(),
                    "Quantity": trade.get('quantity', 0),
                    "Price": f"${trade.get('price', 0):.2f}",
                    "Confidence": f"{trade.get('confidence', 0):.2f}"
                })
            st.dataframe(trade_data, use_container_width=True)
        else:
            st.info("No recent trades")
        
        # Performance stats
        st.header("Performance Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
        
        with col2:
            st.metric("Total Trades", stats.get('total_trades', 0))
        
        with col3:
            st.metric("Avg P&L", f"${stats.get('avg_pnl', 0):.2f}")
        
        with col4:
            st.metric("Sharpe Ratio", f"{stats.get('sharpe_ratio', 0):.2f}")
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
    
    # Auto refresh
    if auto_refresh:
        st.rerun()
        asyncio.sleep(refresh_interval)


if __name__ == "__main__":
    run_dashboard()
