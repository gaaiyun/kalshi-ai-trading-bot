"""
Kalshi Trading Bot - Simplified multi-agent trading system
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from src.clients.kalshi_client import KalshiClient
from src.clients.model_router import ModelRouter
from src.agents.ensemble import EnsembleRunner
from src.strategies.portfolio_optimizer import PortfolioOptimizer
from src.utils.database import DatabaseManager
from src.utils.logging_setup import get_trading_logger
from src.config.settings import settings

logger = get_trading_logger("trading_bot")


class KalshiTradingBot:
    """
    Simplified Kalshi trading bot with multi-agent AI ensemble.
    
    Features:
    - 5-model AI ensemble (Grok-4, Claude, GPT-4o, Gemini, DeepSeek)
    - Portfolio optimization with Kelly Criterion
    - Risk management and position limits
    - Paper trading and live trading modes
    """
    
    def __init__(self, live_mode: bool = False):
        self.live_mode = live_mode
        self.logger = get_trading_logger("bot")
        
        # Initialize clients
        self.kalshi = KalshiClient()
        self.model_router = ModelRouter()
        self.ensemble = EnsembleRunner()
        self.portfolio = PortfolioOptimizer()
        self.db = DatabaseManager()
        
        # State tracking
        self.balance = 0.0
        self.daily_cost = 0.0
        self.daily_loss = 0.0
        self.last_reset = datetime.now()
        
        self.logger.info(
            f"Bot initialized - Mode: {'LIVE' if live_mode else 'PAPER'}"
        )
    
    async def run(self):
        """Main trading loop."""
        await self.db.initialize()
        
        self.logger.info("🚀 Starting trading bot...")
        
        while True:
            try:
                # Reset daily counters if needed
                await self._check_daily_reset()
                
                # Check if we can trade
                if not await self._can_trade():
                    await asyncio.sleep(60)
                    continue
                
                # Get balance
                self.balance = await self.kalshi.get_balance()
                
                # Scan markets
                markets = await self._scan_markets()
                
                if not markets:
                    self.logger.info("No markets found, waiting...")
                    await asyncio.sleep(settings.trading.scan_interval_seconds)
                    continue
                
                # Analyze each market
                for market in markets:
                    try:
                        await self._analyze_and_trade(market)
                    except Exception as e:
                        self.logger.error(f"Error analyzing market: {e}")
                        continue
                
                # Check and update positions
                await self._update_positions()
                
                # Wait before next scan
                await asyncio.sleep(settings.trading.scan_interval_seconds)
                
            except KeyboardInterrupt:
                self.logger.info("Bot stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Bot error: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _check_daily_reset(self):
        """Reset daily counters at midnight."""
        now = datetime.now()
        if now.date() > self.last_reset.date():
            self.daily_cost = 0.0
            self.daily_loss = 0.0
            self.last_reset = now
            self.logger.info("Daily counters reset")
    
    async def _can_trade(self) -> bool:
        """Check if we can trade based on limits."""
        # Check daily cost limit
        if self.daily_cost >= settings.trading.daily_ai_budget:
            self.logger.warning(
                f"Daily AI budget limit reached: ${self.daily_cost:.2f}"
            )
            return False
        
        # Check daily loss limit
        if self.daily_loss >= settings.trading.max_daily_loss_pct:
            self.logger.warning(
                f"Daily loss limit reached: {self.daily_loss:.1f}%"
            )
            return False
        
        # Check balance
        if self.balance < settings.trading.min_balance:
            self.logger.warning(
                f"Balance too low: ${self.balance:.2f}"
            )
            return False
        
        return True
    
    async def _scan_markets(self) -> List[Dict]:
        """Scan for tradeable markets."""
        try:
            markets = await self.kalshi.get_markets()
            
            # Filter markets
            filtered = []
            for market in markets:
                if self._is_tradeable(market):
                    filtered.append(market)
            
            self.logger.info(f"Found {len(filtered)} tradeable markets")
            return filtered
            
        except Exception as e:
            self.logger.error(f"Error scanning markets: {e}")
            return []
    
    def _is_tradeable(self, market: Dict) -> bool:
        """Check if market meets trading criteria."""
        # Check volume
        volume = market.get('volume', 0)
        if volume < settings.trading.min_volume:
            return False
        
        # Check expiry
        expiry = market.get('expiry_date')
        if expiry:
            days_to_expiry = (expiry - datetime.now()).days
            if days_to_expiry > settings.trading.max_time_to_expiry_days:
                return False
        
        return True
    
    async def _analyze_and_trade(self, market: Dict):
        """Analyze market with AI ensemble and execute trade if signal found."""
        market_ticker = market.get('ticker', 'Unknown')
        
        self.logger.info(f"Analyzing {market_ticker}...")
        
        # Get AI ensemble decision
        result = await self.ensemble.run_ensemble(
            market_data=market,
            get_completions=self.model_router.get_completions()
        )
        
        # Track cost
        cost = result.get('total_cost', 0)
        self.daily_cost += cost
        
        # Check confidence
        confidence = result.get('confidence', 0)
        if confidence < settings.trading.min_confidence_to_trade:
            self.logger.info(
                f"{market_ticker}: Low confidence {confidence:.2f}, skipping"
            )
            return
        
        # Get probability
        probability = result.get('probability', 0.5)
        
        # Calculate position size using Kelly Criterion
        position_size = self.portfolio.calculate_kelly_size(
            probability=probability,
            current_price=market.get('last_price', 0.5),
            balance=self.balance
        )
        
        if position_size <= 0:
            self.logger.info(f"{market_ticker}: No edge, skipping")
            return
        
        # Check position limits
        if not await self._check_position_limits(position_size):
            self.logger.info(f"{market_ticker}: Position limits reached")
            return
        
        # Execute trade
        await self._execute_trade(
            market=market,
            side='yes' if probability > 0.5 else 'no',
            quantity=position_size,
            confidence=confidence,
            ai_result=result
        )
    
    async def _check_position_limits(self, new_position_size: float) -> bool:
        """Check if new position would exceed limits."""
        # Get current positions
        positions = await self.db.get_open_positions()
        
        # Check max positions
        if len(positions) >= settings.trading.max_positions:
            return False
        
        # Check max position size
        max_size = self.balance * (settings.trading.max_position_size_pct / 100)
        if new_position_size > max_size:
            return False
        
        return True
    
    async def _execute_trade(
        self,
        market: Dict,
        side: str,
        quantity: float,
        confidence: float,
        ai_result: Dict
    ):
        """Execute trade order."""
        market_ticker = market.get('ticker', 'Unknown')
        
        self.logger.info(
            f"🎯 Trading signal: {market_ticker} | "
            f"Side: {side.upper()} | Qty: {quantity:.0f} | "
            f"Confidence: {confidence:.2f}"
        )
        
        if not self.live_mode:
            self.logger.info("📝 Paper trade - not executing")
            # Log to database for paper trading
            await self.db.log_paper_trade(
                market_ticker=market_ticker,
                side=side,
                quantity=quantity,
                price=market.get('last_price', 0.5),
                confidence=confidence,
                ai_result=ai_result
            )
            return
        
        try:
            # Execute real trade
            order = await self.kalshi.place_order(
                market_ticker=market_ticker,
                side=side,
                quantity=int(quantity),
                order_type='market'
            )
            
            self.logger.info(f"✅ Order executed: {order.get('order_id')}")
            
            # Log to database
            await self.db.log_trade(
                market_ticker=market_ticker,
                side=side,
                quantity=quantity,
                price=order.get('fill_price', market.get('last_price', 0.5)),
                confidence=confidence,
                ai_result=ai_result,
                order_id=order.get('order_id')
            )
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
    
    async def _update_positions(self):
        """Update open positions and check exit conditions."""
        positions = await self.db.get_open_positions()
        
        for position in positions:
            try:
                await self._check_exit_conditions(position)
            except Exception as e:
                self.logger.error(f"Error updating position: {e}")
    
    async def _check_exit_conditions(self, position: Dict):
        """Check if position should be closed."""
        market_ticker = position.get('market_ticker')
        entry_price = position.get('entry_price', 0)
        quantity = position.get('quantity', 0)
        
        # Get current price
        market = await self.kalshi.get_market(market_ticker)
        current_price = market.get('last_price', entry_price)
        
        # Calculate P&L
        pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        
        # Check stop-loss
        if pnl_pct <= -settings.trading.stop_loss_pct:
            self.logger.info(
                f"🛑 Stop-loss triggered for {market_ticker}: {pnl_pct:.1f}%"
            )
            await self._close_position(position, current_price, "stop_loss")
            return
        
        # Check take-profit
        if pnl_pct >= settings.trading.take_profit_pct:
            self.logger.info(
                f"💰 Take-profit triggered for {market_ticker}: {pnl_pct:.1f}%"
            )
            await self._close_position(position, current_price, "take_profit")
            return
        
        # Check time-based exit
        entry_time = position.get('entry_time')
        if entry_time:
            days_held = (datetime.now() - entry_time).days
            if days_held >= settings.trading.max_hold_days:
                self.logger.info(
                    f"⏰ Time-based exit for {market_ticker}: {days_held} days"
                )
                await self._close_position(position, current_price, "time_exit")
    
    async def _close_position(
        self,
        position: Dict,
        current_price: float,
        reason: str
    ):
        """Close an open position."""
        market_ticker = position.get('market_ticker')
        quantity = position.get('quantity', 0)
        side = position.get('side', 'yes')
        
        # Determine close side (opposite of entry)
        close_side = 'no' if side == 'yes' else 'yes'
        
        if not self.live_mode:
            self.logger.info(f"📝 Paper trade close - not executing")
            await self.db.close_position(
                position_id=position.get('id'),
                exit_price=current_price,
                exit_reason=reason
            )
            return
        
        try:
            # Execute close order
            order = await self.kalshi.place_order(
                market_ticker=market_ticker,
                side=close_side,
                quantity=int(quantity),
                order_type='market'
            )
            
            self.logger.info(f"✅ Position closed: {market_ticker}")
            
            # Update database
            await self.db.close_position(
                position_id=position.get('id'),
                exit_price=order.get('fill_price', current_price),
                exit_reason=reason,
                order_id=order.get('order_id')
            )
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
