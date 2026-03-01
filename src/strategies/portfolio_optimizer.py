"""
Portfolio Optimizer - Simplified Kelly Criterion position sizing
"""

from typing import Dict, Optional
from src.utils.logging_setup import get_trading_logger
from src.config.settings import settings

logger = get_trading_logger("portfolio")


class PortfolioOptimizer:
    """
    Simplified portfolio optimizer using Kelly Criterion.
    
    Kelly Criterion formula:
    f* = (bp - q) / b
    
    Where:
    - f* = fraction of bankroll to bet
    - b = odds received (payout ratio)
    - p = probability of winning
    - q = probability of losing (1 - p)
    """
    
    def __init__(self):
        self.kelly_fraction = settings.trading.kelly_fraction
        self.max_position_pct = settings.trading.max_position_size_pct / 100
    
    def calculate_kelly_size(
        self,
        probability: float,
        current_price: float,
        balance: float
    ) -> float:
        """
        Calculate position size using Kelly Criterion.
        
        Args:
            probability: AI predicted probability (0-1)
            current_price: Current market price (0-1)
            balance: Available balance
        
        Returns:
            Position size in dollars
        """
        # Validate inputs
        if probability <= 0 or probability >= 1:
            return 0.0
        
        if current_price <= 0 or current_price >= 1:
            return 0.0
        
        # Calculate edge
        edge = probability - current_price
        
        # No edge, no trade
        if edge <= 0:
            return 0.0
        
        # Calculate Kelly fraction
        # For binary markets: f* = edge / (1 - current_price)
        kelly_f = edge / (1 - current_price)
        
        # Apply fractional Kelly
        kelly_f *= self.kelly_fraction
        
        # Cap at max position size
        kelly_f = min(kelly_f, self.max_position_pct)
        
        # Convert to dollar amount
        position_size = balance * kelly_f
        
        logger.debug(
            f"Kelly sizing: prob={probability:.2f}, price={current_price:.2f}, "
            f"edge={edge:.2f}, kelly_f={kelly_f:.2f}, size=${position_size:.2f}"
        )
        
        return position_size
    
    def calculate_risk_parity_weights(
        self,
        positions: list
    ) -> Dict[str, float]:
        """
        Calculate risk parity weights for portfolio rebalancing.
        
        Args:
            positions: List of position dicts
        
        Returns:
            Dict mapping position_id to target weight
        """
        if not positions:
            return {}
        
        # Simple equal weighting for now
        # TODO: Implement true risk parity based on volatility
        equal_weight = 1.0 / len(positions)
        
        return {
            pos.get('id'): equal_weight
            for pos in positions
        }
