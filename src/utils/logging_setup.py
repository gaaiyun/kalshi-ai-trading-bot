"""
Logging setup for the Kalshi trading system.
Provides structured logging with file rotation and multiple output targets.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

import structlog
from structlog import configure, get_logger

from src.config.settings import settings


def setup_logging(log_level: str = "INFO") -> None:
    """
    Set up structured logging for the trading system.
    Creates a new log file for each run with timestamp.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    from datetime import datetime
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"trading_system_{timestamp}.log"
    
    # Create a "latest.log" symlink/copy for easy access
    latest_log = logs_dir / "latest.log"

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Configure structlog for human-readable output
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True, exception_formatter=structlog.dev.rich_traceback),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=[
            logging.FileHandler(log_file),
            logging.FileHandler(latest_log, mode='w'),
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Log startup message
    logger = get_trading_logger("logging")
    logger.info(
        "Logging system initialized",
        log_file=str(log_file),
        latest_log=str(latest_log),
        log_level=log_level,
        console_enabled=True,
        file_enabled=True
    )


def get_trading_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance for the trading system.
    
    Args:
        name: Logger name (typically module name)
    
    Returns:
        Configured logger instance
    """
    return get_logger(f"trading_system.{name}")


class TradingLoggerMixin:
    """
    Mixin class to add logging capability to trading system classes.
    """
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.logger = get_trading_logger(cls.__name__.lower())
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class."""
        if not hasattr(self, '_logger'):
            self._logger = get_trading_logger(self.__class__.__name__.lower())
        return self._logger


def log_trade_execution(
    action: str,
    market_id: str,
    amount: float,
    price: Optional[float] = None,
    confidence: Optional[float] = None,
    reason: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log trade execution with structured data.
    
    Args:
        action: Trade action (BUY, SELL, CANCEL)
        market_id: Kalshi market identifier
        amount: Trade amount
        price: Trade price (if applicable)
        confidence: AI confidence level
        reason: Reason for trade
        **kwargs: Additional context
    """
    logger = get_trading_logger("trade_execution")
    logger.info(
        "Trade executed",
        action=action,
        market_id=market_id,
        amount=amount,
        price=price,
        confidence=confidence,
        reason=reason,
        **kwargs
    )


def log_market_analysis(
    market_id: str,
    analysis_result: dict,
    processing_time: float,
    cost: float,
    **kwargs
) -> None:
    """
    Log market analysis results.
    
    Args:
        market_id: Kalshi market identifier
        analysis_result: AI analysis result
        processing_time: Time taken for analysis
        cost: Cost of analysis
        **kwargs: Additional context
    """
    logger = get_trading_logger("market_analysis")
    logger.info(
        "Market analysis completed",
        market_id=market_id,
        analysis_result=analysis_result,
        processing_time_seconds=processing_time,
        cost_usd=cost,
        **kwargs
    )


def log_error_with_context(
    error: Exception,
    context: dict,
    logger_name: str = "error"
) -> None:
    """
    Log error with additional context.
    
    Args:
        error: Exception that occurred
        context: Additional context information
        logger_name: Logger name to use
    """
    logger = get_trading_logger(logger_name)
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        **context,
        exc_info=True
    ) 