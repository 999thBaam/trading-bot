# Intelligent Adaptive Crypto Trading Bot — Design Spec

## Overview
A Python-based crypto trading bot that detects market conditions and switches between strategies automatically. Runs locally, trades on Binance, sends alerts via Telegram. Designed for passive income with ₹1000 starting capital and as a portfolio showcase piece.

## Goals
- **Passive income**: Steady small returns with strong risk management
- **Portfolio piece**: Demonstrates algorithmic trading, multi-strategy design, real-time market analysis
- **Semi-autonomous**: Bot trades on its own, sends Telegram alerts, requires approval for big decisions

## Architecture

```
┌─────────────────────────────────────────────┐
│              Trading Bot Core               │
├──────────┬──────────┬──────────┬────────────┤
│  Market   │ Strategy │  Risk    │  Trade     │
│  Analyzer │ Engine   │ Manager  │  Executor  │
├──────────┴──────────┴──────────┴────────────┤
│              Binance API Layer              │
├─────────────────────────────────────────────┤
│         Telegram Alert System               │
├─────────────────────────────────────────────┤
│         Trade Logger / Analytics            │
└─────────────────────────────────────────────┘
```

### Core Modules

1. **Market Analyzer** — Fetches price data, detects market regime (trending/sideways/volatile) using ATR, ADX, and Bollinger Band width
2. **Strategy Engine** — Holds multiple strategies, picks the right one based on market regime
3. **Risk Manager** — Controls position sizing, stop-losses, max daily loss limit. Never risks more than 3% per trade
4. **Trade Executor** — Places buy/sell orders on Binance, handles order lifecycle
5. **Telegram Alerts** — Sends trade notifications, daily P&L summaries, and big-decision alerts requiring user approval
6. **Trade Logger** — Records every trade in SQLite, tracks win rate, profit, and per-strategy performance

## Tech Stack
- Python 3.9+
- `python-binance` — Binance API
- `python-telegram-bot` — Telegram alerts
- `pandas` + `ta` — Technical indicators
- SQLite — Trade history
- Local execution (macOS)

## Market Regime Detection

| Condition | Regime |
|---|---|
| ADX > 25 | Trending |
| ADX < 20 + tight Bollinger Bands | Sideways/ranging |
| ATR spike + wide Bollinger Bands | High volatility |

## Strategies

### 1. Trend Follower (trending markets)
- EMA 9/21 crossover for entry signals
- MACD histogram confirmation
- Trailing stop-loss that locks in profits
- Exit on EMA cross back or trailing stop hit

### 2. Mean Reversion (sideways markets)
- RSI < 30 → buy, RSI > 70 → sell
- Bollinger Band touch confirmation (lower band = buy)
- Take-profit at middle Bollinger Band (mean)
- Tight stop-loss below recent low

### 3. Volatility Pause (volatile/uncertain markets)
- Reduces position size by 50% or sits out entirely
- Only takes very high-confidence signals (multiple indicators agree)
- Widens stop-losses to avoid noise stop-outs
- Alerts user: "Market is choppy, sitting tight"

## Coin Selection
- Monitors top 5-10 liquid coins: BTC, ETH, SOL, BNB, XRP, etc.
- Scores each coin on volume, trend strength, volatility
- Picks best 1-2 coins to trade at any time
- With ₹1000 capital, holds only 1 position at a time

## Risk Management

| Rule | Value |
|---|---|
| Max risk per trade | 3% (₹30) |
| Max daily loss | 5% (₹50) |
| Max drawdown | 15% (₹150) — bot pauses, alerts user |
| Stop-losses | Always required, no trade without one |
| Leverage | None — spot trading only |
| Fee filter | Skips trades where fees > 1% of position |

## Telegram Alerts

### Auto-sent (no approval needed)
- Trade executed (entry price, coin, strategy, stop-loss)
- Trade closed (P&L, exit reason)
- Daily summary (P&L, win rate, trades taken)

### Requires user approval
- First trade on a new coin
- Any trade after a 3-loss streak
- Resuming after daily/drawdown limit hit

## Trade Logger & Analytics
- SQLite database for all trades
- Per-strategy win rate tracking — bot weights towards better-performing strategies over time
- Weekly performance report via Telegram
- CSV export for manual analysis

## Project Structure

```
trading-bot/
├── config.py          # API keys, risk params, coin list
├── main.py            # Bot loop — runs every 5 minutes
├── market_analyzer.py # Regime detection
├── strategies/
│   ├── trend.py       # Trend follower
│   ├── mean_revert.py # Mean reversion
│   └── volatility.py  # Volatility handler
├── risk_manager.py    # Position sizing, stop-loss, limits
├── trade_executor.py  # Binance order placement
├── telegram_bot.py    # Alerts + approval flow
├── trade_logger.py    # SQLite logging + analytics
├── backtest.py        # Test strategies on historical data
└── requirements.txt
```

## Backtesting
`backtest.py` allows testing all strategies on historical data before risking real money. Essential for confidence-building and a strong portfolio feature.

## Constraints
- ₹1000 (~$12 USD) starting capital
- Binance exchange (P2P for INR deposits)
- Local execution on macOS
- Semi-autonomous with Telegram approval flow
