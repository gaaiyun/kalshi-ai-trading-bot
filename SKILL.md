# Kalshi AI Trading Bot Skill

**Multi-agent AI trading system for Kalshi prediction markets with Grok-4 ensemble.**

## Overview

This skill provides an autonomous trading bot for [Kalshi](https://kalshi.com) prediction markets, featuring:

- **5-Model AI Ensemble**: Grok-4, Claude Sonnet 4, GPT-4o, Gemini 2.5 Flash, DeepSeek R1
- **Multi-Agent Decision System**: Forecaster, News Analyst, Bull/Bear Researchers, Risk Manager
- **Advanced Strategies**: Directional trading (50%), Market making (40%), Arbitrage detection (10%)
- **Portfolio Optimization**: Kelly Criterion sizing, risk parity allocation, dynamic rebalancing
- **Real-Time Monitoring**: Live dashboard, P&L tracking, performance analytics

## Quick Start

### Prerequisites

1. **Kalshi Account**: Sign up at [kalshi.com](https://kalshi.com) and get API credentials
2. **API Keys**:
   - xAI API key for Grok-4: [console.x.ai](https://console.x.ai/)
   - OpenRouter API key: [openrouter.ai](https://openrouter.ai/)
3. **Python 3.12+**: Required for async features

### Installation

```bash
# Navigate to skill directory
cd ~/.openclaw/workspace/skills/kalshi-trading

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.env` file in the skill directory:

```bash
# Kalshi API credentials
KALSHI_API_KEY=your_kalshi_api_key_id
# Place your kalshi_private_key file (no extension) in skill directory

# AI Model APIs
XAI_API_KEY=your_xai_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional fallback
```

### Usage

```bash
# Paper trading (no real money)
python scripts/trade.py --paper

# Live trading (real money - use with caution!)
python scripts/trade.py --live

# Launch monitoring dashboard
python scripts/dashboard.py

# Check portfolio status
python scripts/status.py

# Run health check
python scripts/health.py
```

## Architecture

### Multi-Agent Ensemble

| Agent | Model | Role | Weight |
|-------|-------|------|--------|
| Forecaster | Grok-4 | Lead probability prediction | 30% |
| News Analyst | Claude Sonnet 4 | News sentiment analysis | 20% |
| Bull Researcher | GPT-4o | Bullish case research | 20% |
| Bear Researcher | Gemini 2.5 Flash | Bearish case research | 15% |
| Risk Manager | DeepSeek R1 | Risk assessment | 15% |

### Trading Strategies

1. **Directional Trading (50% allocation)**
   - AI-predicted probability edges
   - Kelly Criterion position sizing
   - Dynamic exit strategies

2. **Market Making (40% allocation)**
   - Automated bid-ask spread capture
   - Liquidity provision
   - Spread profit optimization

3. **Arbitrage Detection (10% allocation)**
   - Cross-market opportunity scanning
   - Price discrepancy exploitation

### Risk Management

- **Position Limits**: Max 5% per position, 15 concurrent positions
- **Daily Loss Limit**: 15% maximum daily drawdown
- **Kelly Sizing**: Fractional Kelly (0.75x) for volatility control
- **Dynamic Exits**: Trailing stop-loss, take-profit, confidence decay
- **Cost Controls**: $50 daily AI API budget limit

## Features

### Portfolio Optimization

- Kelly Criterion position sizing with fractional multiplier
- Risk parity allocation across positions
- Automatic rebalancing every 6 hours
- Sector concentration limits (90% max)

### Dynamic Exit Strategies

- **Trailing Take-Profit**: 20% gain threshold
- **Stop-Loss**: 15% drawdown per position
- **Confidence Decay**: Exit when AI conviction drops
- **Time-Based**: 10-day maximum hold period
- **Volatility-Adjusted**: Dynamic thresholds

### Real-Time Dashboard

Monitor via Streamlit web interface:

- Portfolio value and balance
- Open positions with P&L
- AI decision logs and confidence scores
- Cost tracking and budget utilization
- Strategy-level performance breakdown

## Configuration

Edit `src/config/settings.py` for custom parameters:

```python
# Position sizing
max_position_size_pct = 5.0      # Max 5% per position
max_positions = 15               # Up to 15 concurrent
kelly_fraction = 0.75            # Fractional Kelly

# Market filtering
min_volume = 200                 # Minimum contract volume
max_time_to_expiry_days = 30     # Trade up to 30 days out
min_confidence_to_trade = 0.50   # Minimum AI confidence

# Risk management
max_daily_loss_pct = 15.0        # Daily loss limit
daily_ai_cost_limit = 50.0       # Max AI API spend (USD)
```

## Paper Trading

Test strategies without risking real money:

```bash
# Scan markets and log signals
python scripts/paper_trade.py

# Continuous scanning every 15 minutes
python scripts/paper_trade.py --loop --interval 900

# Check settled markets and update outcomes
python scripts/paper_trade.py --settle

# Generate HTML dashboard
python scripts/paper_trade.py --dashboard

# Print statistics
python scripts/paper_trade.py --stats
```

Dashboard output: `docs/paper_dashboard.html`

## Performance Tracking

All trades, decisions, and costs are logged to SQLite database (`trading_system.db`):

- Cumulative P&L and win rate
- Sharpe ratio and maximum drawdown
- AI confidence calibration curves
- Cost per trade and daily budget utilization
- Per-strategy performance breakdown

## Safety & Disclaimers

⚠️ **IMPORTANT WARNINGS**:

1. **Trading Risk**: Prediction markets involve substantial risk of loss. Only trade with capital you can afford to lose.
2. **Experimental Software**: This is research/educational software. Not financial advice.
3. **API Costs**: AI ensemble can incur significant API costs. Monitor your daily budget.
4. **Paper Trading First**: Always test in paper mode before live trading.
5. **No Guarantees**: Past performance does not guarantee future results.

## Troubleshooting

### Common Issues

**Database errors on startup**:
```bash
python -m src.utils.database
```

**Module import errors**:
```bash
# Use -m flag for module execution
python -m src.utils.database
```

**API authentication failures**:
- Verify `.env` file exists with correct keys
- Check `kalshi_private_key` file is in project root
- Ensure API keys are active and have sufficient credits

**High API costs**:
- Reduce `scan_interval_seconds` in settings
- Lower `max_trades_per_hour`
- Disable ensemble debate mode
- Use paper trading mode

## Development

### Project Structure

```
kalshi-trading/
├── scripts/           # Entry point scripts
│   ├── trade.py      # Main trading bot
│   ├── dashboard.py  # Monitoring dashboard
│   ├── status.py     # Portfolio status
│   └── health.py     # Health check
├── src/
│   ├── agents/       # Multi-agent ensemble
│   ├── clients/      # API clients (Kalshi, xAI, OpenRouter)
│   ├── config/       # Settings and parameters
│   ├── strategies/   # Trading strategies
│   └── utils/        # Database, logging, risk tools
├── requirements.txt  # Python dependencies
├── .env             # API credentials (create this)
└── SKILL.md         # This file
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ scripts/
isort src/ scripts/

# Type checking
mypy src/
```

## Resources

- **Kalshi API Docs**: [kalshi.com/docs](https://kalshi.com/docs)
- **xAI Console**: [console.x.ai](https://console.x.ai/)
- **OpenRouter**: [openrouter.ai](https://openrouter.ai/)
- **Original Project**: [github.com/kalshi-ai-trading-bot](https://github.com/yourusername/kalshi-ai-trading-bot)

## License

MIT License - See LICENSE file for details.

---

**Remember**: This is experimental software for educational purposes. Trading involves risk. Always start with paper trading and never risk more than you can afford to lose.
