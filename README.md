# Kalshi AI Trading Bot - OpenClaw Skill

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-orange.svg)](https://openclaw.com)

**Multi-agent AI trading system for Kalshi prediction markets with Grok-4 ensemble.**

## 🚀 Features

- **5-Model AI Ensemble**: Grok-4, Claude Sonnet 4, GPT-4o, Gemini 2.5 Flash, DeepSeek R1
- **Multi-Agent Decision System**: Specialized agents for forecasting, news analysis, bull/bear research, and risk management
- **Advanced Trading Strategies**: Directional trading (50%), Market making (40%), Arbitrage detection (10%)
- **Portfolio Optimization**: Kelly Criterion sizing, risk parity allocation, dynamic rebalancing
- **Real-Time Monitoring**: Live dashboard with P&L tracking and performance analytics
- **Paper Trading Mode**: Test strategies without risking real money
- **Cost Controls**: Daily AI API budget limits and cost tracking

## 📋 Prerequisites

1. **Kalshi Account**: [Sign up](https://kalshi.com) and obtain API credentials
2. **API Keys**:
   - xAI API key for Grok-4: [console.x.ai](https://console.x.ai/)
   - OpenRouter API key: [openrouter.ai](https://openrouter.ai/)
3. **Python 3.12+**: Required for async features

## 🔧 Installation

```bash
# Navigate to skill directory
cd ~/.openclaw/workspace/skills/kalshi-trading

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m src.utils.database
```

## ⚙️ Configuration

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

Download your Kalshi private key from [Kalshi Settings → API](https://kalshi.com/account/settings) and save as `kalshi_private_key` (no file extension) in the skill directory.

## 🎯 Usage

### Basic Commands

```bash
# Paper trading (recommended for testing)
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

### Paper Trading Workflow

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

## 🏗️ Architecture

### Multi-Agent Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    Kalshi AI Trading Bot                    │
├─────────────────────────────────────────────────────────────┤
│  INGEST          DECIDE (Multi-Agent)         EXECUTE       │
│                                                              │
│  Kalshi API  →  ┌──────────────────────┐                   │
│  WebSocket   →  │ Grok-4 (30%)         │                   │
│  News Feeds  →  │ Claude Sonnet 4 (20%)│  →  Order Router │
│  Market Data →  │ GPT-4o (20%)         │  →  Kelly Sizing │
│                 │ Gemini 2.5 (15%)     │  →  Risk Parity  │
│                 │ DeepSeek R1 (15%)    │                   │
│                 └──────────────────────┘                   │
│                   Debate & Consensus                        │
└─────────────────────────────────────────────────────────────┘
```

### Agent Roles

| Agent | Model | Role | Weight |
|-------|-------|------|--------|
| **Forecaster** | Grok-4 | Lead probability prediction | 30% |
| **News Analyst** | Claude Sonnet 4 | News sentiment analysis | 20% |
| **Bull Researcher** | GPT-4o | Bullish case research | 20% |
| **Bear Researcher** | Gemini 2.5 Flash | Bearish case research | 15% |
| **Risk Manager** | DeepSeek R1 | Risk assessment | 15% |

### Trading Strategies

1. **Directional Trading (50% allocation)**
   - AI-predicted probability edges
   - Kelly Criterion position sizing
   - Dynamic exit strategies (trailing stop-loss, take-profit, confidence decay)

2. **Market Making (40% allocation)**
   - Automated bid-ask spread capture
   - Liquidity provision
   - Spread profit optimization

3. **Arbitrage Detection (10% allocation)**
   - Cross-market opportunity scanning
   - Price discrepancy exploitation

## 🛡️ Risk Management

- **Position Limits**: Max 5% per position, 15 concurrent positions
- **Daily Loss Limit**: 15% maximum daily drawdown
- **Kelly Sizing**: Fractional Kelly (0.75x) for volatility control
- **Dynamic Exits**: Trailing stop-loss (15%), take-profit (20%), confidence decay
- **Cost Controls**: $50 daily AI API budget limit
- **Sector Concentration**: 90% maximum per sector

## 📊 Performance Tracking

All trades, decisions, and costs are logged to SQLite database (`trading_system.db`):

- Cumulative P&L and win rate
- Sharpe ratio and maximum drawdown
- AI confidence calibration curves
- Cost per trade and daily budget utilization
- Per-strategy performance breakdown

## 🎨 Dashboard

Real-time Streamlit web interface showing:

- Portfolio value and balance
- Open positions with entry prices and P&L
- AI decision logs and confidence scores
- Cost monitoring and budget utilization
- Strategy-level performance breakdown

## ⚠️ Safety & Disclaimers

**IMPORTANT WARNINGS**:

1. **Trading Risk**: Prediction markets involve substantial risk of loss. Only trade with capital you can afford to lose.
2. **Experimental Software**: This is research/educational software. Not financial advice.
3. **API Costs**: AI ensemble can incur significant API costs. Monitor your daily budget.
4. **Paper Trading First**: Always test in paper mode before live trading.
5. **No Guarantees**: Past performance does not guarantee future results.

## 🔧 Troubleshooting

### Database Errors

```bash
python -m src.utils.database
```

### Module Import Errors

Always use `-m` flag for module execution:
```bash
python -m src.utils.database
```

### API Authentication Failures

- Verify `.env` file exists with correct keys
- Check `kalshi_private_key` file is in project root
- Ensure API keys are active and have sufficient credits

### High API Costs

- Reduce `scan_interval_seconds` in settings
- Lower `max_trades_per_hour`
- Disable ensemble debate mode
- Use paper trading mode

## 📁 Project Structure

```
kalshi-trading/
├── scripts/              # Entry point scripts
│   ├── trade.py         # Main trading bot
│   ├── dashboard.py     # Monitoring dashboard
│   ├── status.py        # Portfolio status
│   ├── health.py        # Health check
│   └── paper_trade.py   # Paper trading
├── src/
│   ├── agents/          # Multi-agent ensemble
│   ├── clients/         # API clients (Kalshi, xAI, OpenRouter)
│   ├── config/          # Settings and parameters
│   ├── strategies/      # Trading strategies
│   ├── jobs/            # Core pipeline (ingest, decide, execute, track)
│   └── utils/           # Database, logging, risk tools
├── requirements.txt     # Python dependencies
├── .env                # API credentials (create this)
├── SKILL.md            # Skill documentation
└── README.md           # This file
```

## 🧪 Development

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

## 📚 Resources

- **Kalshi API Docs**: [kalshi.com/docs](https://kalshi.com/docs)
- **xAI Console**: [console.x.ai](https://console.x.ai/)
- **OpenRouter**: [openrouter.ai](https://openrouter.ai/)
- **Original Project**: [github.com/kalshi-ai-trading-bot](https://github.com/gaaiyun/kalshi-ai-trading-bot)

## 📄 License

MIT License - See LICENSE file for details.

## 🙏 Acknowledgments

Based on the original [Kalshi AI Trading Bot](https://github.com/gaaiyun/kalshi-ai-trading-bot) project. Adapted for OpenClaw skill framework.

---

**Remember**: This is experimental software for educational purposes. Trading involves risk. Always start with paper trading and never risk more than you can afford to lose.
