"""
Enhanced evaluation system with cost monitoring and trading performance analysis.
"""

import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.utils.database import DatabaseManager
from src.config.settings import settings
from src.utils.logging_setup import get_trading_logger

async def analyze_ai_costs(db_manager: DatabaseManager) -> Dict:
    """Analyze AI spending patterns and provide cost optimization recommendations."""
    logger = get_trading_logger("cost_analysis")
    
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    async with aiosqlite.connect(db_manager.db_path) as db:
        # Daily cost summary
        daily_costs = {}
        for date in [today, yesterday]:
            cursor = await db.execute("""
                SELECT total_ai_cost, analysis_count, decision_count 
                FROM daily_cost_tracking WHERE date = ?
            """, (date,))
            row = await cursor.fetchone()
            daily_costs[date] = {
                'cost': row[0] if row else 0.0,
                'analyses': row[1] if row else 0,
                'decisions': row[2] if row else 0
            }
        
        # Weekly cost trend
        cursor = await db.execute("""
            SELECT SUM(total_ai_cost), SUM(analysis_count), SUM(decision_count)
            FROM daily_cost_tracking WHERE date >= ?
        """, (week_ago,))
        weekly_stats = await cursor.fetchone()
        
        # Most expensive markets by analysis cost
        cursor = await db.execute("""
            SELECT market_id, COUNT(*) as analysis_count, SUM(cost_usd) as total_cost,
                   AVG(cost_usd) as avg_cost, analysis_type
            FROM market_analyses 
            WHERE DATE(analysis_timestamp) >= ?
            GROUP BY market_id
            ORDER BY total_cost DESC
            LIMIT 10
        """, (week_ago,))
        expensive_markets = await cursor.fetchall()
        
        # Analysis type breakdown
        cursor = await db.execute("""
            SELECT analysis_type, COUNT(*) as count, SUM(cost_usd) as total_cost
            FROM market_analyses 
            WHERE DATE(analysis_timestamp) >= ?
            GROUP BY analysis_type
        """, (week_ago,))
        analysis_breakdown = await cursor.fetchall()
    
    # Calculate cost efficiency metrics
    today_cost = daily_costs[today]['cost']
    today_decisions = daily_costs[today]['decisions']
    cost_per_decision = today_cost / max(1, today_decisions)
    
    weekly_cost = weekly_stats[0] if weekly_stats and weekly_stats[0] else 0.0
    weekly_analyses = weekly_stats[1] if weekly_stats and weekly_stats[1] else 0
    weekly_decisions = weekly_stats[2] if weekly_stats and weekly_stats[2] else 0
    
    # Generate recommendations
    recommendations = []
    
    if today_cost > settings.trading.daily_ai_budget * 0.8:
        recommendations.append(f"⚠️  Near daily budget limit: ${today_cost:.3f} / ${settings.trading.daily_ai_budget}")
    
    if cost_per_decision > settings.trading.max_ai_cost_per_decision:
        recommendations.append(f"💰 High cost per decision: ${cost_per_decision:.3f}")
    
    if weekly_cost > settings.trading.daily_ai_budget * 5:  # More than 5 days of budget in a week
        recommendations.append("📈 Weekly spending trending high - consider tighter controls")
    
    if weekly_analyses > weekly_decisions * 3:  # Too many analyses relative to decisions
        recommendations.append("🔄 High analysis-to-decision ratio - improve filtering")
    
    # Log comprehensive cost report
    logger.info(
        "AI Cost Analysis Report",
        today_cost=today_cost,
        yesterday_cost=daily_costs[yesterday]['cost'],
        weekly_cost=weekly_cost,
        cost_per_decision=cost_per_decision,
        weekly_analyses=weekly_analyses,
        weekly_decisions=weekly_decisions,
        budget_utilization=today_cost / settings.trading.daily_ai_budget,
        recommendations=recommendations
    )
    
    return {
        'daily_costs': daily_costs,
        'weekly_cost': weekly_cost,
        'cost_per_decision': cost_per_decision,
        'expensive_markets': expensive_markets,
        'analysis_breakdown': analysis_breakdown,
        'recommendations': recommendations
    }

async def analyze_trading_performance(db_manager: DatabaseManager) -> Dict:
    """Analyze trading performance and position management effectiveness."""
    logger = get_trading_logger("trading_performance")
    
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    async with aiosqlite.connect(db_manager.db_path) as db:
        # Overall P&L
        cursor = await db.execute("""
            SELECT COUNT(*) as total_trades, SUM(pnl) as total_pnl,
                   AVG(pnl) as avg_pnl, SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades
            FROM trade_logs WHERE DATE(exit_timestamp) >= ?
        """, (week_ago,))
        perf_stats = await cursor.fetchone()
        
        # Exit reason analysis
        cursor = await db.execute("""
            SELECT 
                CASE 
                    WHEN rationale LIKE '%market_resolution%' THEN 'market_resolution'
                    WHEN rationale LIKE '%stop_loss%' THEN 'stop_loss'
                    WHEN rationale LIKE '%take_profit%' THEN 'take_profit'
                    WHEN rationale LIKE '%time_based%' THEN 'time_based'
                    ELSE 'other'
                END as exit_reason,
                COUNT(*) as count,
                AVG(pnl) as avg_pnl
            FROM trade_logs 
            WHERE DATE(exit_timestamp) >= ?
            GROUP BY exit_reason
        """, (week_ago,))
        exit_reasons = await cursor.fetchall()
        
        # Current open positions analysis
        cursor = await db.execute("""
            SELECT COUNT(*) as open_positions,
                   AVG((julianday('now') - julianday(timestamp)) * 24) as avg_hours_held
            FROM positions WHERE status = 'open'
        """)
        position_stats = await cursor.fetchone()
    
    total_trades = perf_stats[0] if perf_stats and perf_stats[0] is not None else 0
    total_pnl = perf_stats[1] if perf_stats and perf_stats[1] is not None else 0.0
    winning_trades = perf_stats[3] if perf_stats and perf_stats[3] is not None else 0
    win_rate = (winning_trades / max(1, total_trades)) if total_trades > 0 else 0.0
    
    avg_pnl = perf_stats[2] if perf_stats and perf_stats[2] is not None else 0.0
    open_positions = position_stats[0] if position_stats and position_stats[0] is not None else 0
    avg_hours_held = position_stats[1] if position_stats and position_stats[1] is not None else 0.0
    
    logger.info(
        "Trading Performance Report",
        total_trades=total_trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        avg_pnl=avg_pnl,
        open_positions=open_positions,
        avg_hours_held=avg_hours_held
    )
    
    return {
        'total_trades': total_trades,
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'exit_reasons': exit_reasons,
        'position_stats': position_stats
    }

async def run_evaluation():
    """
    Enhanced evaluation job that analyzes both costs and trading performance.
    """
    logger = get_trading_logger("evaluation")
    logger.info("Starting enhanced evaluation job.")
    
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        # Analyze AI costs and efficiency
        cost_analysis = await analyze_ai_costs(db_manager)
        
        # Analyze trading performance
        performance_analysis = await analyze_trading_performance(db_manager)
        
        # Generate overall system health summary
        daily_cost = cost_analysis['daily_costs'][datetime.now().strftime('%Y-%m-%d')]['cost']
        budget_utilization = daily_cost / settings.trading.daily_ai_budget
        
        health_status = "🟢 HEALTHY"
        if budget_utilization > 0.9:
            health_status = "🔴 OVER BUDGET"
        elif budget_utilization > 0.7:
            health_status = "🟡 HIGH USAGE"
        
        logger.info(
            "System Health Summary",
            status=health_status,
            daily_budget_used=f"{budget_utilization:.1%}",
            total_recommendations=len(cost_analysis['recommendations']),
            open_positions=performance_analysis.get('position_stats', [0])[0] if performance_analysis.get('position_stats') else 0
        )
        
        # If costs are high, suggest immediate actions
        if budget_utilization > 0.8:
            logger.warning(
                "HIGH COST ALERT: Consider immediate actions",
                suggestions=[
                    "Increase analysis_cooldown_hours",
                    "Raise min_volume_for_ai_analysis threshold", 
                    "Enable skip_news_for_low_volume",
                    "Reduce max_analyses_per_market_per_day"
                ]
            )
    
    except Exception as e:
        logger.error("Error in evaluation job", error=str(e), exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
