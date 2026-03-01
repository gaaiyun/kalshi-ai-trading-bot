"""
Performance Dashboard Integration

Integrates the automated performance analyzer with the beast mode dashboard,
providing real-time health monitoring and actionable insights directly in the UI.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import os
import aiosqlite

from src.jobs.automated_performance_analyzer import run_performance_analysis, Priority
from src.jobs.performance_scheduler import get_scheduler_status, ScheduleConfig
from src.utils.database import DatabaseManager
from src.utils.logging_setup import get_trading_logger


@dataclass
class DashboardMetrics:
    """Key metrics for dashboard display."""
    health_score: float
    critical_issues: int
    warnings: int
    available_cash: float
    capital_utilization: float
    active_positions: int
    win_rate: float
    total_pnl: float
    last_analysis: Optional[str]
    trending: str  # "up", "down", "stable"


@dataclass
class CriticalAlert:
    """Critical alert for dashboard display."""
    priority: str
    title: str
    message: str
    action_required: str
    target_date: str
    category: str


class PerformanceDashboardIntegration:
    """
    Integration layer between performance analyzer and dashboard.
    
    Provides real-time health metrics, alerts, and recommendations
    formatted for dashboard consumption.
    """
    
    def __init__(self):
        self.logger = get_trading_logger("dashboard_integration")
        self.db = None
        self._last_metrics: Optional[DashboardMetrics] = None
        self._last_alerts: List[CriticalAlert] = []
        
    async def initialize(self):
        """Initialize database connection."""
        self.db = DatabaseManager()
        await self.db.initialize()
        self.logger.info("Dashboard integration initialized")
    
    async def get_current_metrics(self) -> DashboardMetrics:
        """Get current system metrics for dashboard display."""
        try:
            # Get latest analysis from database
            async with aiosqlite.connect(self.db.db_path) as database:
                cursor = await database.execute("""
                    SELECT * FROM analysis_reports 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                latest_report = await cursor.fetchone()
            
            if latest_report:
                # Load the full report file
                report_file = latest_report[6]  # report_file column
                if report_file and os.path.exists(report_file):
                    with open(report_file, 'r') as f:
                        full_report = json.load(f)
                    
                    metrics = self._extract_dashboard_metrics(full_report)
                else:
                    # Fallback to database values
                    metrics = DashboardMetrics(
                        health_score=latest_report[2],  # health_score
                        critical_issues=latest_report[3],  # critical_issues
                        warnings=latest_report[4],  # warnings
                        available_cash=0.0,  # Will be fetched separately
                        capital_utilization=0.0,
                        active_positions=0,
                        win_rate=0.0,
                        total_pnl=0.0,
                        last_analysis=latest_report[1],  # timestamp
                        trending="stable"
                    )
            else:
                # No analysis available - create basic metrics
                metrics = DashboardMetrics(
                    health_score=50.0,
                    critical_issues=0,
                    warnings=0,
                    available_cash=0.0,
                    capital_utilization=0.0,
                    active_positions=0,
                    win_rate=0.0,
                    total_pnl=0.0,
                    last_analysis=None,
                    trending="stable"
                )
            
            # Calculate trending based on previous metrics
            if self._last_metrics:
                if metrics.health_score > self._last_metrics.health_score + 5:
                    metrics.trending = "up"
                elif metrics.health_score < self._last_metrics.health_score - 5:
                    metrics.trending = "down"
                else:
                    metrics.trending = "stable"
            
            self._last_metrics = metrics
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get current metrics: {e}")
            return DashboardMetrics(
                health_score=0.0,
                critical_issues=1,
                warnings=0,
                available_cash=0.0,
                capital_utilization=0.0,
                active_positions=0,
                win_rate=0.0,
                total_pnl=0.0,
                last_analysis=None,
                trending="down"
            )
    
    def _extract_dashboard_metrics(self, report: Dict[str, Any]) -> DashboardMetrics:
        """Extract dashboard metrics from full analysis report."""
        summary = report.get('summary', {})
        performance = report.get('performance_metrics', {})
        
        return DashboardMetrics(
            health_score=summary.get('overall_health_score', 0.0),
            critical_issues=summary.get('total_critical_issues', 0),
            warnings=summary.get('total_warnings', 0),
            available_cash=performance.get('available_cash', 0.0),
            capital_utilization=performance.get('capital_utilization', 0.0),
            active_positions=performance.get('active_positions', 0),
            win_rate=performance.get('overall_win_rate', 0.0),
            total_pnl=performance.get('total_pnl', 0.0),
            last_analysis=report.get('timestamp'),
            trending="stable"  # Will be calculated later
        )
    
    async def get_critical_alerts(self) -> List[CriticalAlert]:
        """Get critical alerts for dashboard display."""
        try:
            # Get latest analysis from database
            async with aiosqlite.connect(self.db.db_path) as database:
                cursor = await database.execute("""
                    SELECT report_file FROM analysis_reports 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                result = await cursor.fetchone()
            
            if not result or not result[0]:
                return []
            
            report_file = result[0]
            if not os.path.exists(report_file):
                return []
            
            with open(report_file, 'r') as f:
                report = json.load(f)
            
            alerts = []
            action_items = report.get('action_items', [])
            
            for item in action_items:
                # Only show critical and high priority items
                if item['priority'] in ['CRITICAL', 'HIGH']:
                    alert = CriticalAlert(
                        priority=item['priority'],
                        title=item['action'],
                        message=item['rationale'],
                        action_required=item['implementation_steps'][0] if item['implementation_steps'] else "Review required",
                        target_date=item['target_date'],
                        category=item['category']
                    )
                    alerts.append(alert)
            
            self._last_alerts = alerts
            return alerts
            
        except Exception as e:
            self.logger.error(f"Failed to get critical alerts: {e}")
            return []
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get complete dashboard summary."""
        metrics = await self.get_current_metrics()
        alerts = await self.get_critical_alerts()
        scheduler_status = get_scheduler_status()
        
        # Determine overall system status
        if metrics.critical_issues > 0:
            system_status = "CRITICAL"
            status_color = "red"
        elif metrics.warnings > 0:
            system_status = "WARNING" 
            status_color = "yellow"
        elif metrics.health_score >= 80:
            system_status = "HEALTHY"
            status_color = "green"
        else:
            system_status = "DEGRADED"
            status_color = "orange"
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system_status': system_status,
            'status_color': status_color,
            'metrics': asdict(metrics),
            'alerts': [asdict(alert) for alert in alerts],
            'scheduler': {
                'running': scheduler_status['running'],
                'last_analysis': scheduler_status.get('last_analysis'),
                'next_analysis': self._calculate_next_analysis_time()
            },
            'quick_actions': self._generate_quick_actions(metrics, alerts),
            'performance_summary': {
                'health_score_trend': self._get_health_trend(),
                'key_improvements': self._get_key_improvements(alerts),
                'risk_level': self._calculate_risk_level(metrics)
            }
        }
    
    def _calculate_next_analysis_time(self) -> str:
        """Calculate next scheduled analysis time."""
        # Assuming daily analysis at 9 AM
        now = datetime.now()
        next_analysis = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if next_analysis <= now:
            next_analysis += timedelta(days=1)
        return next_analysis.isoformat()
    
    def _generate_quick_actions(self, metrics: DashboardMetrics, alerts: List[CriticalAlert]) -> List[Dict[str, str]]:
        """Generate quick action buttons for dashboard."""
        actions = []
        
        # Always include refresh analysis
        actions.append({
            'title': 'Run Analysis Now',
            'action': 'run_analysis',
            'icon': 'refresh',
            'color': 'blue'
        })
        
        # Critical cash action
        if metrics.available_cash < 50:
            actions.append({
                'title': 'Emergency Cash Build',
                'action': 'build_cash',
                'icon': 'dollar-sign',
                'color': 'red'
            })
        
        # Position management
        if metrics.active_positions > 12:
            actions.append({
                'title': 'Reduce Positions',
                'action': 'reduce_positions',
                'icon': 'trending-down',
                'color': 'orange'
            })
        
        # Capital utilization
        if metrics.capital_utilization > 80:
            actions.append({
                'title': 'Lower Utilization',
                'action': 'reduce_utilization',
                'icon': 'shield',
                'color': 'yellow'
            })
        
        return actions
    
    def _get_health_trend(self) -> str:
        """Get health score trend description."""
        if not self._last_metrics:
            return "No trend data available"
        
        current_score = self._last_metrics.health_score
        
        if current_score >= 80:
            return "System health is excellent"
        elif current_score >= 60:
            return "System health is good"
        elif current_score >= 40:
            return "System health needs attention"
        else:
            return "System health is critical"
    
    def _get_key_improvements(self, alerts: List[CriticalAlert]) -> List[str]:
        """Get key improvement recommendations."""
        improvements = []
        
        for alert in alerts[:3]:  # Top 3 alerts
            if alert.priority == 'CRITICAL':
                improvements.append(f"🚨 {alert.title}")
            else:
                improvements.append(f"⚠️ {alert.title}")
        
        if not improvements:
            improvements.append("✅ No critical issues detected")
        
        return improvements
    
    def _calculate_risk_level(self, metrics: DashboardMetrics) -> str:
        """Calculate overall risk level."""
        if metrics.critical_issues > 0:
            return "HIGH"
        elif metrics.warnings > 0 or metrics.capital_utilization > 80:
            return "MEDIUM"
        elif metrics.capital_utilization > 60:
            return "LOW"
        else:
            return "MINIMAL"
    
    async def trigger_emergency_analysis(self) -> Dict[str, Any]:
        """Trigger emergency analysis and return results."""
        self.logger.info("🚨 Triggering emergency performance analysis")
        
        try:
            report = await run_performance_analysis()
            
            # Extract critical information for immediate action
            emergency_summary = {
                'timestamp': datetime.now().isoformat(),
                'health_score': report['summary']['overall_health_score'],
                'critical_issues': report['summary']['total_critical_issues'],
                'urgent_actions': [],
                'immediate_steps': []
            }
            
            # Extract urgent actions
            for action in report['action_items']:
                if action['priority'] == 'CRITICAL':
                    emergency_summary['urgent_actions'].append({
                        'action': action['action'],
                        'rationale': action['rationale'],
                        'target_date': action['target_date'],
                        'steps': action['implementation_steps'][:2]  # First 2 steps
                    })
            
            # Generate immediate steps
            if report['summary']['total_critical_issues'] > 0:
                emergency_summary['immediate_steps'] = [
                    "Stop all automated trading",
                    "Review cash reserves immediately", 
                    "Consider closing high-risk positions",
                    "Manual oversight required"
                ]
            
            self.logger.info(
                "🚨 Emergency analysis completed",
                health_score=emergency_summary['health_score'],
                critical_issues=emergency_summary['critical_issues']
            )
            
            return emergency_summary
            
        except Exception as e:
            self.logger.error(f"❌ Emergency analysis failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'health_score': 0.0,
                'critical_issues': 1,
                'urgent_actions': [],
                'immediate_steps': ["Manual intervention required due to analysis failure"]
            }


# Global instance for dashboard integration
_dashboard_integration: Optional[PerformanceDashboardIntegration] = None


async def get_dashboard_integration() -> PerformanceDashboardIntegration:
    """Get or create dashboard integration instance."""
    global _dashboard_integration
    
    if _dashboard_integration is None:
        _dashboard_integration = PerformanceDashboardIntegration()
        await _dashboard_integration.initialize()
    
    return _dashboard_integration


# Dashboard API endpoints (to be called from beast mode dashboard)
async def dashboard_get_metrics() -> Dict[str, Any]:
    """API endpoint: Get current system metrics."""
    integration = await get_dashboard_integration()
    return asdict(await integration.get_current_metrics())


async def dashboard_get_alerts() -> List[Dict[str, Any]]:
    """API endpoint: Get critical alerts."""
    integration = await get_dashboard_integration()
    alerts = await integration.get_critical_alerts()
    return [asdict(alert) for alert in alerts]


async def dashboard_get_summary() -> Dict[str, Any]:
    """API endpoint: Get complete dashboard summary."""
    integration = await get_dashboard_integration()
    return await integration.get_dashboard_summary()


async def dashboard_trigger_analysis() -> Dict[str, Any]:
    """API endpoint: Trigger emergency analysis."""
    integration = await get_dashboard_integration()
    return await integration.trigger_emergency_analysis()


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Dashboard Integration")
    parser.add_argument("--metrics", action="store_true", help="Show current metrics")
    parser.add_argument("--alerts", action="store_true", help="Show critical alerts")
    parser.add_argument("--summary", action="store_true", help="Show dashboard summary")
    parser.add_argument("--emergency", action="store_true", help="Trigger emergency analysis")
    args = parser.parse_args()
    
    async def main():
        if args.metrics:
            metrics = await dashboard_get_metrics()
            print("📊 CURRENT METRICS:")
            print(json.dumps(metrics, indent=2, default=str))
        
        elif args.alerts:
            alerts = await dashboard_get_alerts()
            print("🚨 CRITICAL ALERTS:")
            print(json.dumps(alerts, indent=2, default=str))
        
        elif args.summary:
            summary = await dashboard_get_summary()
            print("📋 DASHBOARD SUMMARY:")
            print(json.dumps(summary, indent=2, default=str))
        
        elif args.emergency:
            result = await dashboard_trigger_analysis()
            print("🚨 EMERGENCY ANALYSIS:")
            print(json.dumps(result, indent=2, default=str))
        
        else:
            parser.print_help()
    
    asyncio.run(main()) 