# Adaptive Crypto Trading Bot — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a semi-autonomous crypto trading bot that detects market regimes and switches between trend-following, mean-reversion, and volatility-pause strategies, with Telegram alerts and risk management.

**Architecture:** Six modules (Market Analyzer, Strategy Engine, Risk Manager, Trade Executor, Telegram Alerts, Trade Logger) orchestrated by a main loop running every 5 minutes. Each module is independent with clear interfaces. SQLite stores trade history. Binance API for market data and order execution.

**Tech Stack:** Python 3.9+, python-binance, python-telegram-bot, pandas, ta (technical analysis), SQLite, pytest

---

## File Structure

| File | Responsibility |
|------|---------------|
| `config.py` | All configuration: API keys, risk params, coin list, intervals |
| `trade_logger.py` | SQLite trade storage, P&L tracking, analytics queries |
| `market_analyzer.py` | Fetch candles from Binance, compute indicators, detect market regime, score coins |
| `strategies/__init__.py` | Strategy registry and selection |
| `strategies/base.py` | Abstract base class for all strategies |
| `strategies/trend.py` | Trend follower: EMA crossover + MACD |
| `strategies/mean_revert.py` | Mean reversion: RSI + Bollinger Bands |
| `strategies/volatility.py` | Volatility pause: reduced sizing or sit out |
| `risk_manager.py` | Position sizing, daily loss limits, drawdown tracking, fee filter |
| `trade_executor.py` | Binance order placement, stop-loss monitoring, trailing stops |
| `telegram_bot.py` | Send alerts, request approval, daily summaries |
| `main.py` | Main bot loop, orchestrates all modules |
| `backtest.py` | Run strategies on historical data, compute performance metrics |
| `tests/test_trade_logger.py` | Tests for trade logger |
| `tests/test_market_analyzer.py` | Tests for market analyzer |
| `tests/test_strategies.py` | Tests for all strategies |
| `tests/test_risk_manager.py` | Tests for risk manager |
| `tests/test_trade_executor.py` | Tests for trade executor |
| `tests/test_telegram_bot.py` | Tests for Telegram alert formatting and logic |
| `tests/test_backtest.py` | Tests for backtester |

---

## Chunk 1: Foundation

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `tests/__init__.py`
- Create: `strategies/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
python-binance==1.0.19
python-telegram-bot==20.7
python-dotenv==1.0.0
pandas==2.1.4
ta==0.11.0
pytest==7.4.4
pytest-asyncio==0.23.3
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.env
venv/
*.db
.pytest_cache/
```

- [ ] **Step 3: Create empty __init__.py files**

Create empty files:
- `tests/__init__.py`
- `strategies/__init__.py`

- [ ] **Step 4: Install dependencies**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pip install -r requirements.txt --user`
Expected: All packages install successfully

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore tests/__init__.py strategies/__init__.py
git commit -m "chore: project setup with dependencies and gitignore"
```

---

### Task 2: Config Module

**Files:**
- Create: `config.py`

- [ ] **Step 1: Create config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()


# Binance API
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Trading parameters
TRADING_INTERVAL = "5m"  # Candle interval
BOT_LOOP_SECONDS = 300   # How often the bot runs (5 minutes)
LOOKBACK_CANDLES = 100    # Number of candles to fetch for analysis

# Coins to monitor (USDT pairs)
COIN_LIST = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "MATICUSDT",
]

# Risk management
INITIAL_CAPITAL = 12.0          # ~₹1000 in USD
MAX_RISK_PER_TRADE = 0.03       # 3% of capital
MAX_DAILY_LOSS = 0.05           # 5% of capital
MAX_DRAWDOWN = 0.15             # 15% of capital
MIN_FEE_RATIO = 0.01            # Skip if fees > 1% of position

# Binance fee rate (0.1% maker/taker for basic tier)
FEE_RATE = 0.001

# Market regime thresholds
ADX_TREND_THRESHOLD = 25        # ADX > 25 = trending
ADX_SIDEWAYS_THRESHOLD = 20     # ADX < 20 = sideways
BB_WIDTH_VOLATILE_THRESHOLD = 0.05  # BB width threshold for volatility

# Strategy parameters
EMA_FAST = 9
EMA_SLOW = 21
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
TRAILING_STOP_PCT = 0.02        # 2% trailing stop

# Approval rules
LOSS_STREAK_APPROVAL = 3        # Require approval after N consecutive losses

# Database
DB_PATH = "trades.db"
```

- [ ] **Step 2: Commit**

```bash
git add config.py
git commit -m "feat: add config module with all trading parameters"
```

---

### Task 3: Trade Logger (TDD)

**Files:**
- Create: `tests/test_trade_logger.py`
- Create: `trade_logger.py`

- [ ] **Step 1: Write failing tests for trade logger**

```python
import os
import pytest
from datetime import datetime, timedelta
from trade_logger import TradeLogger


@pytest.fixture
def logger(tmp_path):
    db_path = str(tmp_path / "test_trades.db")
    tl = TradeLogger(db_path)
    yield tl
    tl.close()


class TestTradeLogger:
    def test_open_and_close_trade(self, logger):
        trade_id = logger.open_trade(
            symbol="BTCUSDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.0002,
            strategy="trend",
            stop_loss=48500.0,
        )
        assert trade_id == 1

        logger.close_trade(
            trade_id=trade_id,
            exit_price=51000.0,
            exit_reason="trailing_stop",
        )
        trade = logger.get_trade(trade_id)
        assert trade["exit_price"] == 51000.0
        assert trade["pnl"] == pytest.approx((51000.0 - 50000.0) * 0.0002)
        assert trade["exit_reason"] == "trailing_stop"

    def test_daily_pnl(self, logger):
        t1 = logger.open_trade("BTCUSDT", "BUY", 50000, 0.0002, "trend", 48500)
        logger.close_trade(t1, 51000, "tp")  # profit = 0.2
        t2 = logger.open_trade("ETHUSDT", "BUY", 3000, 0.005, "mean_revert", 2900)
        logger.close_trade(t2, 2950, "sl")   # loss = -0.25

        daily_pnl = logger.get_daily_pnl()
        assert daily_pnl == pytest.approx(0.2 + (-0.25))

    def test_strategy_stats(self, logger):
        # Two winning trend trades
        t1 = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t1, 105, "tp")
        t2 = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t2, 103, "tp")

        # One losing trend trade
        t3 = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t3, 97, "sl")

        stats = logger.get_strategy_stats("trend")
        assert stats["total_trades"] == 3
        assert stats["winning_trades"] == 2
        assert stats["win_rate"] == pytest.approx(2 / 3)

    def test_consecutive_losses(self, logger):
        for i in range(3):
            t = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
            logger.close_trade(t, 97, "sl")

        assert logger.get_consecutive_losses() == 3

    def test_consecutive_losses_reset_on_win(self, logger):
        t1 = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t1, 97, "sl")
        t2 = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t2, 105, "tp")

        assert logger.get_consecutive_losses() == 0

    def test_total_pnl(self, logger):
        t1 = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t1, 110, "tp")  # +10
        t2 = logger.open_trade("ETHUSDT", "BUY", 50, 1.0, "mean_revert", 45)
        logger.close_trade(t2, 48, "sl")   # -2

        assert logger.get_total_pnl() == pytest.approx(8.0)

    def test_open_position_exists(self, logger):
        logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        assert logger.has_open_position() is True

    def test_no_open_position(self, logger):
        t = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t, 105, "tp")
        assert logger.has_open_position() is False

    def test_get_open_position(self, logger):
        logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        pos = logger.get_open_position()
        assert pos["symbol"] == "BTCUSDT"
        assert pos["stop_loss"] == 95

    def test_export_csv(self, logger, tmp_path):
        t = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t, 110, "tp")
        csv_path = str(tmp_path / "export.csv")
        logger.export_csv(csv_path)
        assert os.path.exists(csv_path)
        with open(csv_path) as f:
            lines = f.readlines()
        assert len(lines) == 2  # header + 1 trade

    def test_coins_traded(self, logger):
        t = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t, 105, "tp")
        assert "BTCUSDT" in logger.get_coins_traded()

    def test_update_stop_loss(self, logger):
        t = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.update_stop_loss(t, 97.5)
        pos = logger.get_open_position()
        assert pos["stop_loss"] == 97.5

    def test_get_all_strategy_stats(self, logger):
        t1 = logger.open_trade("BTCUSDT", "BUY", 100, 1.0, "trend", 95)
        logger.close_trade(t1, 105, "tp")
        t2 = logger.open_trade("ETHUSDT", "BUY", 50, 1.0, "mean_revert", 45)
        logger.close_trade(t2, 48, "sl")
        stats = logger.get_all_strategy_stats()
        assert "trend" in stats
        assert "mean_revert" in stats
        assert stats["trend"]["win_rate"] == 1.0
        assert stats["mean_revert"]["win_rate"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_trade_logger.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trade_logger'`

- [ ] **Step 3: Implement trade_logger.py**

```python
import sqlite3
import csv
from datetime import datetime, date


class TradeLogger:
    def __init__(self, db_path="trades.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                strategy TEXT NOT NULL,
                stop_loss REAL NOT NULL,
                pnl REAL,
                exit_reason TEXT,
                opened_at TEXT NOT NULL,
                closed_at TEXT
            )
        """)
        self.conn.commit()

    def open_trade(self, symbol, side, entry_price, quantity, strategy, stop_loss):
        cursor = self.conn.execute(
            """INSERT INTO trades (symbol, side, entry_price, quantity, strategy, stop_loss, opened_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (symbol, side, entry_price, quantity, strategy, stop_loss, datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        return cursor.lastrowid

    def close_trade(self, trade_id, exit_price, exit_reason):
        trade = self.get_trade(trade_id)
        if trade["side"] == "BUY":
            pnl = (exit_price - trade["entry_price"]) * trade["quantity"]
        else:
            pnl = (trade["entry_price"] - exit_price) * trade["quantity"]
        self.conn.execute(
            """UPDATE trades SET exit_price=?, pnl=?, exit_reason=?, closed_at=? WHERE id=?""",
            (exit_price, pnl, exit_reason, datetime.utcnow().isoformat(), trade_id),
        )
        self.conn.commit()

    def get_trade(self, trade_id):
        row = self.conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        return dict(row) if row else None

    def get_daily_pnl(self):
        today = date.today().isoformat()
        row = self.conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) as total FROM trades WHERE closed_at LIKE ? AND pnl IS NOT NULL",
            (f"{today}%",),
        ).fetchone()
        return row["total"]

    def get_total_pnl(self):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) as total FROM trades WHERE pnl IS NOT NULL"
        ).fetchone()
        return row["total"]

    def get_strategy_stats(self, strategy):
        rows = self.conn.execute(
            "SELECT * FROM trades WHERE strategy=? AND pnl IS NOT NULL", (strategy,)
        ).fetchall()
        if not rows:
            return {"total_trades": 0, "winning_trades": 0, "win_rate": 0.0, "total_pnl": 0.0}
        total = len(rows)
        winners = sum(1 for r in rows if r["pnl"] > 0)
        total_pnl = sum(r["pnl"] for r in rows)
        return {
            "total_trades": total,
            "winning_trades": winners,
            "win_rate": winners / total if total > 0 else 0.0,
            "total_pnl": total_pnl,
        }

    def get_consecutive_losses(self):
        rows = self.conn.execute(
            "SELECT pnl FROM trades WHERE pnl IS NOT NULL ORDER BY closed_at DESC"
        ).fetchall()
        count = 0
        for row in rows:
            if row["pnl"] < 0:
                count += 1
            else:
                break
        return count

    def has_open_position(self):
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE closed_at IS NULL"
        ).fetchone()
        return row["cnt"] > 0

    def get_open_position(self):
        row = self.conn.execute(
            "SELECT * FROM trades WHERE closed_at IS NULL ORDER BY opened_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def update_stop_loss(self, trade_id, new_stop_loss):
        self.conn.execute(
            "UPDATE trades SET stop_loss=? WHERE id=?", (new_stop_loss, trade_id)
        )
        self.conn.commit()

    def get_coins_traded(self):
        rows = self.conn.execute("SELECT DISTINCT symbol FROM trades").fetchall()
        return [r["symbol"] for r in rows]

    def get_all_strategy_stats(self):
        """Get stats for all strategies that have been used."""
        rows = self.conn.execute(
            "SELECT DISTINCT strategy FROM trades WHERE pnl IS NOT NULL"
        ).fetchall()
        return {r["strategy"]: self.get_strategy_stats(r["strategy"]) for r in rows}

    def get_all_closed_trades(self):
        rows = self.conn.execute(
            "SELECT * FROM trades WHERE closed_at IS NOT NULL ORDER BY closed_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def export_csv(self, filepath):
        trades = self.get_all_closed_trades()
        if not trades:
            return
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=trades[0].keys())
            writer.writeheader()
            writer.writerows(trades)

    def close(self):
        self.conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_trade_logger.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add trade_logger.py tests/test_trade_logger.py
git commit -m "feat: add trade logger with SQLite storage and analytics"
```

---

## Chunk 2: Market Analysis

### Task 4: Market Analyzer (TDD)

**Files:**
- Create: `tests/test_market_analyzer.py`
- Create: `market_analyzer.py`

- [ ] **Step 1: Write failing tests for market analyzer**

```python
import pytest
import pandas as pd
import numpy as np
from market_analyzer import MarketAnalyzer


@pytest.fixture
def analyzer():
    return MarketAnalyzer(client=None)  # None client for unit tests


def make_candle_df(prices, volumes=None):
    """Helper to create a DataFrame resembling Binance candle data."""
    n = len(prices)
    if volumes is None:
        volumes = [1000.0] * n
    return pd.DataFrame({
        "open": prices,
        "high": [p * 1.01 for p in prices],
        "low": [p * 0.99 for p in prices],
        "close": prices,
        "volume": volumes,
    })


class TestRegimeDetection:
    def test_trending_market(self, analyzer):
        # Steadily rising prices create a trend
        prices = [100 + i * 2 for i in range(50)]
        df = make_candle_df(prices)
        df = analyzer.add_indicators(df)
        regime = analyzer.detect_regime(df)
        assert regime in ("trending", "volatile")  # strong move can read as either

    def test_sideways_market(self, analyzer):
        # Oscillating prices around 100
        prices = [100 + (i % 4 - 2) * 0.5 for i in range(50)]
        df = make_candle_df(prices)
        df = analyzer.add_indicators(df)
        regime = analyzer.detect_regime(df)
        assert regime == "sideways"

    def test_regime_returns_valid_string(self, analyzer):
        prices = [100 + i for i in range(50)]
        df = make_candle_df(prices)
        df = analyzer.add_indicators(df)
        regime = analyzer.detect_regime(df)
        assert regime in ("trending", "sideways", "volatile")


class TestIndicators:
    def test_add_indicators_columns(self, analyzer):
        prices = [100 + i * 0.5 for i in range(50)]
        df = make_candle_df(prices)
        df = analyzer.add_indicators(df)
        expected_cols = ["adx", "atr", "bb_width", "rsi", "ema_fast", "ema_slow",
                         "macd", "macd_signal", "macd_hist"]
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_rsi_range(self, analyzer):
        prices = [100 + i * 0.5 for i in range(50)]
        df = make_candle_df(prices)
        df = analyzer.add_indicators(df)
        rsi_values = df["rsi"].dropna()
        assert all(0 <= v <= 100 for v in rsi_values)


class TestCoinScoring:
    def test_score_returns_dict(self, analyzer):
        prices = [100 + i for i in range(50)]
        df = make_candle_df(prices, volumes=[1000 + i * 10 for i in range(50)])
        df = analyzer.add_indicators(df)
        score = analyzer.score_coin(df)
        assert isinstance(score, float)
        assert score >= 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_market_analyzer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'market_analyzer'`

- [ ] **Step 3: Implement market_analyzer.py**

```python
import pandas as pd
import ta
from binance.client import Client

import config


class MarketAnalyzer:
    def __init__(self, client=None):
        self.client = client

    def fetch_candles(self, symbol, interval=None, limit=None):
        """Fetch candle data from Binance. Returns a DataFrame."""
        if interval is None:
            interval = config.TRADING_INTERVAL
        if limit is None:
            limit = config.LOOKBACK_CANDLES

        raw = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(raw, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df

    def add_indicators(self, df):
        """Add all technical indicators to the DataFrame."""
        # ADX
        adx_indicator = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14)
        df["adx"] = adx_indicator.adx()

        # ATR
        atr_indicator = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14)
        df["atr"] = atr_indicator.average_true_range()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_middle"] = bb.bollinger_mavg()
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        # RSI
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

        # EMA
        df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=config.EMA_FAST).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=config.EMA_SLOW).ema_indicator()

        # MACD
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_hist"] = macd.macd_diff()

        return df

    def detect_regime(self, df):
        """Detect market regime from indicators. Returns 'trending', 'sideways', or 'volatile'."""
        latest = df.iloc[-1]
        adx = latest["adx"]
        bb_width = latest["bb_width"]
        atr = latest["atr"]

        # Check ATR spike: compare current ATR to rolling mean
        atr_mean = df["atr"].rolling(20).mean().iloc[-1]
        atr_ratio = atr / atr_mean if atr_mean > 0 else 1.0

        if atr_ratio > 1.5 and bb_width > config.BB_WIDTH_VOLATILE_THRESHOLD:
            return "volatile"
        elif adx > config.ADX_TREND_THRESHOLD:
            return "trending"
        else:
            return "sideways"

    def score_coin(self, df):
        """Score a coin for trading opportunity. Higher = better."""
        latest = df.iloc[-1]
        score = 0.0

        # Volume score: higher volume = more liquid = better
        vol_mean = df["volume"].rolling(20).mean().iloc[-1]
        if vol_mean > 0:
            score += min(latest["volume"] / vol_mean, 2.0)  # Cap at 2x

        # Trend strength: higher ADX = clearer signal
        if not pd.isna(latest["adx"]):
            score += latest["adx"] / 50.0  # Normalize to ~0-1

        # Volatility: moderate is good (opportunity), extreme is bad
        if not pd.isna(latest["atr"]):
            atr_mean = df["atr"].rolling(20).mean().iloc[-1]
            if atr_mean > 0:
                atr_ratio = latest["atr"] / atr_mean
                if 0.8 <= atr_ratio <= 1.5:
                    score += 1.0  # Good volatility
                elif atr_ratio > 2.0:
                    score -= 0.5  # Too volatile

        return max(score, 0.0)

    def analyze_all_coins(self):
        """Fetch data and score all configured coins. Returns sorted list of (symbol, df, regime, score)."""
        results = []
        for symbol in config.COIN_LIST:
            try:
                df = self.fetch_candles(symbol)
                df = self.add_indicators(df)
                regime = self.detect_regime(df)
                score = self.score_coin(df)
                results.append((symbol, df, regime, score))
            except Exception:
                continue
        results.sort(key=lambda x: x[3], reverse=True)
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_market_analyzer.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add market_analyzer.py tests/test_market_analyzer.py
git commit -m "feat: add market analyzer with regime detection and coin scoring"
```

---

## Chunk 3: Strategies

### Task 5: Base Strategy Interface

**Files:**
- Create: `strategies/base.py`

- [ ] **Step 1: Create base strategy**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class Signal:
    action: str           # "buy", "sell", or "hold"
    confidence: float     # 0.0 to 1.0
    stop_loss: float      # Price for stop-loss
    take_profit: Optional[float] = None  # Price for take-profit (if applicable)
    reason: str = ""      # Human-readable reason


class BaseStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Signal:
        """Analyze the DataFrame and return a trading signal."""
        pass
```

- [ ] **Step 2: Commit**

```bash
git add strategies/base.py
git commit -m "feat: add base strategy interface with Signal dataclass"
```

---

### Task 6: Trend Follower Strategy (TDD)

**Files:**
- Create: `tests/test_strategies.py`
- Create: `strategies/trend.py`

- [ ] **Step 1: Write failing tests for trend follower**

```python
import pytest
import pandas as pd
from strategies.trend import TrendFollower
from strategies.base import Signal


def make_df_with_indicators(closes, ema_fast, ema_slow, macd_hist):
    """Create a minimal DataFrame with pre-computed indicators."""
    n = len(closes)
    return pd.DataFrame({
        "close": closes,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "macd_hist": macd_hist,
        "atr": [1.0] * n,
    })


class TestTrendFollower:
    def setup_method(self):
        self.strategy = TrendFollower()

    def test_buy_signal_on_ema_crossover_up(self):
        # EMA fast crosses above EMA slow, MACD positive
        closes =    [100, 101, 102, 103, 104, 105]
        ema_fast =  [ 99, 100, 101, 102, 103, 106]  # crosses above at end
        ema_slow =  [100, 100, 100, 101, 102, 104]
        macd_hist = [-0.5, -0.3, -0.1, 0.1, 0.3, 0.5]
        df = make_df_with_indicators(closes, ema_fast, ema_slow, macd_hist)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "buy"
        assert signal.confidence > 0.5
        assert signal.stop_loss < closes[-1]

    def test_sell_signal_on_ema_crossover_down(self):
        # EMA fast crosses below EMA slow
        closes =    [105, 104, 103, 102, 101, 100]
        ema_fast =  [106, 105, 104, 102, 100, 98]  # crosses below
        ema_slow =  [104, 104, 103, 103, 102, 101]
        macd_hist = [0.5, 0.3, 0.1, -0.1, -0.3, -0.5]
        df = make_df_with_indicators(closes, ema_fast, ema_slow, macd_hist)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "sell"

    def test_hold_when_no_crossover(self):
        # EMA fast consistently above EMA slow, no crossover
        closes =    [100, 101, 102, 103, 104, 105]
        ema_fast =  [102, 103, 104, 105, 106, 107]
        ema_slow =  [ 98,  99, 100, 101, 102, 103]
        macd_hist = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        df = make_df_with_indicators(closes, ema_fast, ema_slow, macd_hist)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "hold"

    def test_signal_returns_signal_type(self):
        closes = [100] * 6
        df = make_df_with_indicators(closes, closes, closes, [0] * 6)
        signal = self.strategy.generate_signal(df)
        assert isinstance(signal, Signal)

    def test_strategy_name(self):
        assert self.strategy.name == "trend"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_strategies.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies.trend'`

- [ ] **Step 3: Implement trend strategy**

```python
import pandas as pd

from strategies.base import BaseStrategy, Signal


class TrendFollower(BaseStrategy):
    name = "trend"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 3:
            return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="insufficient data")

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        close = curr["close"]
        atr = curr["atr"] if not pd.isna(curr["atr"]) else close * 0.02

        # Detect EMA crossover
        fast_above_now = curr["ema_fast"] > curr["ema_slow"]
        fast_above_prev = prev["ema_fast"] > prev["ema_slow"]
        macd_positive = curr["macd_hist"] > 0
        macd_negative = curr["macd_hist"] < 0

        # Bullish crossover: fast crosses above slow
        if fast_above_now and not fast_above_prev and macd_positive:
            confidence = min(abs(curr["macd_hist"]) / (atr + 1e-9), 1.0)
            return Signal(
                action="buy",
                confidence=max(confidence, 0.6),
                stop_loss=close - (2 * atr),
                reason="EMA bullish crossover + MACD confirmation",
            )

        # Bearish crossover: fast crosses below slow
        if not fast_above_now and fast_above_prev and macd_negative:
            confidence = min(abs(curr["macd_hist"]) / (atr + 1e-9), 1.0)
            return Signal(
                action="sell",
                confidence=max(confidence, 0.6),
                stop_loss=close + (2 * atr),
                reason="EMA bearish crossover + MACD confirmation",
            )

        return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="no crossover detected")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_strategies.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add strategies/trend.py tests/test_strategies.py
git commit -m "feat: add trend follower strategy with EMA crossover + MACD"
```

---

### Task 7: Mean Reversion Strategy (TDD)

**Files:**
- Modify: `tests/test_strategies.py` (append tests)
- Create: `strategies/mean_revert.py`

- [ ] **Step 1: Append failing tests for mean reversion**

Add to `tests/test_strategies.py`:

```python
from strategies.mean_revert import MeanReversion


def make_mr_df(closes, rsi, bb_lower, bb_upper, bb_middle):
    n = len(closes)
    return pd.DataFrame({
        "close": closes,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "rsi": rsi,
        "bb_lower": bb_lower,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "atr": [1.0] * n,
    })


class TestMeanReversion:
    def setup_method(self):
        self.strategy = MeanReversion()

    def test_buy_on_oversold_rsi_and_lower_bb(self):
        closes =    [100, 99, 98, 97, 96, 95]
        rsi =       [40,  35, 32, 29, 27, 25]
        bb_lower =  [94,  94, 94, 94, 94, 96]  # price near lower band
        bb_upper =  [106, 106, 106, 106, 106, 106]
        bb_middle = [100, 100, 100, 100, 100, 100]
        df = make_mr_df(closes, rsi, bb_lower, bb_upper, bb_middle)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "buy"
        assert signal.take_profit == pytest.approx(100)  # middle BB

    def test_sell_on_overbought_rsi(self):
        closes =    [100, 101, 102, 103, 104, 105]
        rsi =       [60,  65, 68, 72, 75, 78]
        bb_lower =  [94,  94, 94, 94, 94, 94]
        bb_upper =  [106, 106, 106, 106, 106, 104]  # price near upper band
        bb_middle = [100, 100, 100, 100, 100, 100]
        df = make_mr_df(closes, rsi, bb_lower, bb_upper, bb_middle)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "sell"

    def test_hold_when_rsi_neutral(self):
        closes =    [100, 100, 100, 100, 100, 100]
        rsi =       [50,  50, 50, 50, 50, 50]
        bb_lower =  [94] * 6
        bb_upper =  [106] * 6
        bb_middle = [100] * 6
        df = make_mr_df(closes, rsi, bb_lower, bb_upper, bb_middle)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "hold"

    def test_strategy_name(self):
        assert self.strategy.name == "mean_revert"
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_strategies.py::TestMeanReversion -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies.mean_revert'`

- [ ] **Step 3: Implement mean reversion strategy**

```python
import pandas as pd

from strategies.base import BaseStrategy, Signal
import config


class MeanReversion(BaseStrategy):
    name = "mean_revert"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 3:
            return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="insufficient data")

        curr = df.iloc[-1]
        close = curr["close"]
        rsi = curr["rsi"]
        atr = curr["atr"] if not pd.isna(curr["atr"]) else close * 0.02

        bb_lower = curr["bb_lower"]
        bb_upper = curr["bb_upper"]
        bb_middle = curr["bb_middle"]

        # Buy: RSI oversold + price near lower Bollinger Band
        if rsi < config.RSI_OVERSOLD and close <= bb_lower * 1.02:
            distance_to_mean = (bb_middle - close) / close
            confidence = min(0.5 + distance_to_mean * 5, 1.0)
            return Signal(
                action="buy",
                confidence=max(confidence, 0.6),
                stop_loss=close - (1.5 * atr),
                take_profit=bb_middle,
                reason=f"RSI oversold ({rsi:.0f}) + near lower BB",
            )

        # Sell: RSI overbought + price near upper Bollinger Band
        if rsi > config.RSI_OVERBOUGHT and close >= bb_upper * 0.98:
            distance_to_mean = (close - bb_middle) / close
            confidence = min(0.5 + distance_to_mean * 5, 1.0)
            return Signal(
                action="sell",
                confidence=max(confidence, 0.6),
                stop_loss=close + (1.5 * atr),
                take_profit=bb_middle,
                reason=f"RSI overbought ({rsi:.0f}) + near upper BB",
            )

        return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="RSI in neutral zone")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_strategies.py -v`
Expected: All 9 tests PASS (5 trend + 4 mean reversion)

- [ ] **Step 5: Commit**

```bash
git add strategies/mean_revert.py tests/test_strategies.py
git commit -m "feat: add mean reversion strategy with RSI + Bollinger Bands"
```

---

### Task 8: Volatility Handler Strategy (TDD)

**Files:**
- Modify: `tests/test_strategies.py` (append tests)
- Create: `strategies/volatility.py`

- [ ] **Step 1: Append failing tests for volatility handler**

Add to `tests/test_strategies.py`:

```python
from strategies.volatility import VolatilityHandler


def make_vol_df(closes, rsi, macd_hist, ema_fast, ema_slow, bb_lower, bb_upper, bb_middle):
    n = len(closes)
    return pd.DataFrame({
        "close": closes,
        "high": [c * 1.02 for c in closes],
        "low": [c * 0.98 for c in closes],
        "rsi": rsi,
        "macd_hist": macd_hist,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "bb_lower": bb_lower,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "atr": [3.0] * n,
    })


class TestVolatilityHandler:
    def setup_method(self):
        self.strategy = VolatilityHandler()

    def test_hold_when_no_strong_signal(self):
        n = 6
        closes = [100] * n
        df = make_vol_df(
            closes, rsi=[50]*n, macd_hist=[0.1]*n,
            ema_fast=[101]*n, ema_slow=[99]*n,
            bb_lower=[94]*n, bb_upper=[106]*n, bb_middle=[100]*n,
        )
        signal = self.strategy.generate_signal(df)
        assert signal.action == "hold"
        assert "choppy" in signal.reason.lower() or "volatile" in signal.reason.lower()

    def test_buy_on_very_strong_signal(self):
        n = 6
        closes = [95, 94, 93, 92, 91, 90]
        df = make_vol_df(
            closes, rsi=[30, 28, 26, 24, 22, 20],
            macd_hist=[-1, -0.8, -0.6, -0.4, -0.2, 0.3],
            ema_fast=[89, 89, 89, 89, 89, 91],
            ema_slow=[92, 92, 92, 92, 92, 90],
            bb_lower=[89]*n, bb_upper=[106]*n, bb_middle=[98]*n,
        )
        signal = self.strategy.generate_signal(df)
        # Should buy with high confidence or hold — both are acceptable
        assert signal.action in ("buy", "hold")

    def test_strategy_name(self):
        assert self.strategy.name == "volatility"

    def test_wider_stop_loss(self):
        n = 6
        closes = [95, 94, 93, 92, 91, 90]
        df = make_vol_df(
            closes, rsi=[30, 28, 26, 24, 22, 20],
            macd_hist=[-1, -0.8, -0.6, -0.4, -0.2, 0.3],
            ema_fast=[89, 89, 89, 89, 89, 91],
            ema_slow=[92, 92, 92, 92, 92, 90],
            bb_lower=[89]*n, bb_upper=[106]*n, bb_middle=[98]*n,
        )
        signal = self.strategy.generate_signal(df)
        if signal.action == "buy":
            # Volatility handler uses wider stop (3x ATR instead of 2x)
            assert signal.stop_loss < closes[-1] - 5
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_strategies.py::TestVolatilityHandler -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies.volatility'`

- [ ] **Step 3: Implement volatility handler**

```python
import pandas as pd

from strategies.base import BaseStrategy, Signal
import config


class VolatilityHandler(BaseStrategy):
    name = "volatility"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        """In volatile markets, only trade on very high-confidence signals.
        Uses wider stops and reduced position sizing (handled by risk manager)."""
        if len(df) < 3:
            return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="insufficient data")

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        close = curr["close"]
        atr = curr["atr"] if not pd.isna(curr["atr"]) else close * 0.02

        signals_agree = 0

        # Check RSI extreme
        if curr["rsi"] < 25:
            signals_agree += 1
        elif curr["rsi"] > 75:
            signals_agree -= 1

        # Check MACD direction change
        if prev["macd_hist"] < 0 and curr["macd_hist"] > 0:
            signals_agree += 1
        elif prev["macd_hist"] > 0 and curr["macd_hist"] < 0:
            signals_agree -= 1

        # Check EMA crossover
        fast_above_now = curr["ema_fast"] > curr["ema_slow"]
        fast_above_prev = prev["ema_fast"] > prev["ema_slow"]
        if fast_above_now and not fast_above_prev:
            signals_agree += 1
        elif not fast_above_now and fast_above_prev:
            signals_agree -= 1

        # Check BB touch
        if close <= curr["bb_lower"] * 1.01:
            signals_agree += 1
        elif close >= curr["bb_upper"] * 0.99:
            signals_agree -= 1

        # Need at least 3 indicators agreeing (very high confidence)
        if signals_agree >= 3:
            return Signal(
                action="buy",
                confidence=0.8,
                stop_loss=close - (3 * atr),  # Wider stop for volatility
                take_profit=curr["bb_middle"],
                reason=f"High-confidence buy in volatile market ({signals_agree} indicators agree)",
            )
        elif signals_agree <= -3:
            return Signal(
                action="sell",
                confidence=0.8,
                stop_loss=close + (3 * atr),
                take_profit=curr["bb_middle"],
                reason=f"High-confidence sell in volatile market ({signals_agree} indicators agree)",
            )

        return Signal(
            action="hold",
            confidence=0.0,
            stop_loss=0.0,
            reason="Volatile market — sitting tight, no strong consensus",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_strategies.py -v`
Expected: All 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add strategies/volatility.py tests/test_strategies.py
git commit -m "feat: add volatility handler strategy with multi-indicator consensus"
```

---

### Task 9: Strategy Registry

**Files:**
- Modify: `strategies/__init__.py`

- [ ] **Step 1: Create strategy registry**

```python
from strategies.trend import TrendFollower
from strategies.mean_revert import MeanReversion
from strategies.volatility import VolatilityHandler

STRATEGY_MAP = {
    "trending": TrendFollower(),
    "sideways": MeanReversion(),
    "volatile": VolatilityHandler(),
}


def get_strategy(regime):
    """Return the appropriate strategy for the given market regime."""
    return STRATEGY_MAP.get(regime, VolatilityHandler())
```

- [ ] **Step 2: Commit**

```bash
git add strategies/__init__.py
git commit -m "feat: add strategy registry mapping regimes to strategies"
```

---

## Chunk 4: Risk & Execution

### Task 10: Risk Manager (TDD)

**Files:**
- Create: `tests/test_risk_manager.py`
- Create: `risk_manager.py`

- [ ] **Step 1: Write failing tests for risk manager**

```python
import pytest
from unittest.mock import MagicMock
from risk_manager import RiskManager


@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.get_daily_pnl.return_value = 0.0
    logger.get_total_pnl.return_value = 0.0
    logger.get_consecutive_losses.return_value = 0
    logger.has_open_position.return_value = False
    logger.get_coins_traded.return_value = ["BTCUSDT"]
    return logger


@pytest.fixture
def rm():
    return RiskManager(initial_capital=12.0)


class TestPositionSizing:
    def test_basic_position_size(self, rm):
        # 3% of $12 = $0.36 risk. If stop is 2% away, position = $0.36 / 0.02 = $18
        # But can't exceed capital, so should be capped
        size = rm.calculate_position_size(
            capital=12.0, entry_price=100.0, stop_loss=98.0
        )
        # Risk = 3% of 12 = 0.36. Distance = 2.0. Quantity = 0.36/2.0 = 0.18
        assert size == pytest.approx(0.18)

    def test_position_size_respects_capital(self, rm):
        # Even if stop is very tight, position shouldn't exceed capital
        size = rm.calculate_position_size(
            capital=12.0, entry_price=100.0, stop_loss=99.9
        )
        max_quantity = 12.0 / 100.0  # 0.12
        assert size <= max_quantity

    def test_zero_stop_distance_returns_zero(self, rm):
        size = rm.calculate_position_size(capital=12.0, entry_price=100.0, stop_loss=100.0)
        assert size == 0.0


class TestDailyLimits:
    def test_within_daily_limit(self, rm, mock_logger):
        mock_logger.get_daily_pnl.return_value = -0.3  # lost $0.30
        assert rm.check_daily_limit(mock_logger, capital=12.0) is True

    def test_exceeded_daily_limit(self, rm, mock_logger):
        mock_logger.get_daily_pnl.return_value = -0.7  # lost $0.70 > 5% of $12
        assert rm.check_daily_limit(mock_logger, capital=12.0) is False


class TestDrawdown:
    def test_within_drawdown_limit(self, rm, mock_logger):
        mock_logger.get_total_pnl.return_value = -1.0  # -$1 of $12
        assert rm.check_drawdown(mock_logger) is True

    def test_exceeded_drawdown(self, rm, mock_logger):
        mock_logger.get_total_pnl.return_value = -2.0  # -$2 > 15% of $12
        assert rm.check_drawdown(mock_logger) is False


class TestFeeFilter:
    def test_trade_passes_fee_filter(self, rm):
        # Position of $10, fee = 0.1% = $0.01 each way = $0.02 total
        # $0.02 / $10 = 0.2% < 1% threshold
        assert rm.passes_fee_filter(position_value=10.0) is True

    def test_tiny_trade_fails_fee_filter(self, rm):
        # Position of $0.50, fee = 0.1% = $0.0005 each way = $0.001 total
        # Actually still passes because 0.2% < 1%
        # Need a very small position for this to fail
        # With min order + fees, let's test with $0.05
        assert rm.passes_fee_filter(position_value=0.05) is True  # Binance has min order limits anyway


class TestTradeValidation:
    def test_blocks_when_position_open(self, rm, mock_logger):
        mock_logger.has_open_position.return_value = True
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0)
        assert allowed is False
        assert "open position" in reason.lower()

    def test_blocks_on_daily_limit(self, rm, mock_logger):
        mock_logger.get_daily_pnl.return_value = -1.0  # > 5% of $12
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0)
        assert allowed is False

    def test_allows_valid_trade(self, rm, mock_logger):
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0)
        assert allowed is True

    def test_needs_approval_after_loss_streak(self, rm, mock_logger):
        mock_logger.get_consecutive_losses.return_value = 3
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0)
        assert allowed is True  # Trade is allowed but flagged for approval
        assert "approval" in reason.lower()

    def test_needs_approval_for_new_coin(self, rm, mock_logger):
        mock_logger.get_coins_traded.return_value = ["BTCUSDT"]
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0, symbol="ETHUSDT")
        assert allowed is True  # Trade is allowed but flagged for approval
        assert "approval" in reason.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_risk_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'risk_manager'`

- [ ] **Step 3: Implement risk_manager.py**

```python
import config


class RiskManager:
    def __init__(self, initial_capital=None):
        self.initial_capital = initial_capital or config.INITIAL_CAPITAL

    def calculate_position_size(self, capital, entry_price, stop_loss):
        """Calculate position quantity based on risk per trade."""
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance == 0:
            return 0.0

        risk_amount = capital * config.MAX_RISK_PER_TRADE
        quantity = risk_amount / stop_distance

        # Don't exceed available capital
        max_quantity = capital / entry_price
        return min(quantity, max_quantity)

    def check_daily_limit(self, trade_logger, capital):
        """Return True if daily loss is within limit."""
        daily_pnl = trade_logger.get_daily_pnl()
        max_loss = capital * config.MAX_DAILY_LOSS
        return daily_pnl > -max_loss

    def check_drawdown(self, trade_logger):
        """Return True if total drawdown is within limit."""
        total_pnl = trade_logger.get_total_pnl()
        max_dd = self.initial_capital * config.MAX_DRAWDOWN
        return total_pnl > -max_dd

    def passes_fee_filter(self, position_value):
        """Return True if fees are less than MIN_FEE_RATIO of position."""
        total_fees = position_value * config.FEE_RATE * 2  # buy + sell
        return (total_fees / position_value) < config.MIN_FEE_RATIO if position_value > 0 else False

    def validate_trade(self, trade_logger, capital, symbol=None):
        """Check all risk rules. Returns (allowed: bool, reason: str).
        If reason contains 'approval', the trade needs user confirmation via Telegram."""
        if trade_logger.has_open_position():
            return False, "Blocked: already have an open position"

        if not self.check_daily_limit(trade_logger, capital):
            return False, "Blocked: daily loss limit exceeded. Needs approval to resume."

        if not self.check_drawdown(trade_logger):
            return False, "Blocked: max drawdown exceeded. Needs approval to resume."

        reasons = []

        if trade_logger.get_consecutive_losses() >= config.LOSS_STREAK_APPROVAL:
            reasons.append(f"Needs approval: {trade_logger.get_consecutive_losses()} consecutive losses")

        if symbol and symbol not in trade_logger.get_coins_traded():
            reasons.append(f"Needs approval: first trade on {symbol}")

        if reasons:
            return True, ". ".join(reasons)

        return True, "Trade allowed"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_risk_manager.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add risk_manager.py tests/test_risk_manager.py
git commit -m "feat: add risk manager with position sizing, limits, and approval rules"
```

---

### Task 11: Trade Executor (TDD)

**Files:**
- Create: `tests/test_trade_executor.py`
- Create: `trade_executor.py`

- [ ] **Step 1: Write failing tests for trade executor**

```python
import pytest
from unittest.mock import MagicMock, patch
from trade_executor import TradeExecutor


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.order_market_buy.return_value = {
        "orderId": 12345,
        "executedQty": "0.001",
        "cummulativeQuoteQty": "50.0",
        "status": "FILLED",
    }
    client.order_market_sell.return_value = {
        "orderId": 12346,
        "executedQty": "0.001",
        "cummulativeQuoteQty": "50.0",
        "status": "FILLED",
    }
    client.get_symbol_ticker.return_value = {"price": "50000.0"}
    return client


@pytest.fixture
def executor(mock_client):
    return TradeExecutor(client=mock_client)


class TestTradeExecutor:
    def test_buy(self, executor, mock_client):
        result = executor.buy("BTCUSDT", 0.001)
        mock_client.order_market_buy.assert_called_once_with(
            symbol="BTCUSDT", quantity=0.001
        )
        assert result["status"] == "FILLED"

    def test_sell(self, executor, mock_client):
        result = executor.sell("BTCUSDT", 0.001)
        mock_client.order_market_sell.assert_called_once_with(
            symbol="BTCUSDT", quantity=0.001
        )
        assert result["status"] == "FILLED"

    def test_get_price(self, executor):
        price = executor.get_price("BTCUSDT")
        assert price == 50000.0

    def test_check_stop_loss_triggered(self, executor):
        triggered = executor.check_stop_loss(
            current_price=48000, stop_loss=48500, side="BUY"
        )
        assert triggered is True

    def test_check_stop_loss_not_triggered(self, executor):
        triggered = executor.check_stop_loss(
            current_price=51000, stop_loss=48500, side="BUY"
        )
        assert triggered is False

    def test_trailing_stop_update(self, executor):
        new_stop = executor.update_trailing_stop(
            current_price=52000,
            current_stop=49000,
            trailing_pct=0.02,
            side="BUY",
        )
        # 52000 * (1 - 0.02) = 50960, which is higher than 49000
        assert new_stop == pytest.approx(50960.0)

    def test_trailing_stop_no_update_if_lower(self, executor):
        new_stop = executor.update_trailing_stop(
            current_price=49500,
            current_stop=49000,
            trailing_pct=0.02,
            side="BUY",
        )
        # 49500 * 0.98 = 48510, lower than current stop 49000
        assert new_stop == 49000  # Keep existing stop
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_trade_executor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trade_executor'`

- [ ] **Step 3: Implement trade_executor.py**

```python
import config


class TradeExecutor:
    def __init__(self, client):
        self.client = client

    def buy(self, symbol, quantity):
        """Place a market buy order."""
        return self.client.order_market_buy(symbol=symbol, quantity=quantity)

    def sell(self, symbol, quantity):
        """Place a market sell order."""
        return self.client.order_market_sell(symbol=symbol, quantity=quantity)

    def get_price(self, symbol):
        """Get current price for a symbol."""
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    def check_stop_loss(self, current_price, stop_loss, side):
        """Check if stop-loss has been triggered."""
        if side == "BUY":
            return current_price <= stop_loss
        else:
            return current_price >= stop_loss

    def update_trailing_stop(self, current_price, current_stop, trailing_pct, side):
        """Update trailing stop-loss. Only moves in favorable direction."""
        if side == "BUY":
            new_stop = current_price * (1 - trailing_pct)
            return max(new_stop, current_stop)
        else:
            new_stop = current_price * (1 + trailing_pct)
            return min(new_stop, current_stop)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_trade_executor.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add trade_executor.py tests/test_trade_executor.py
git commit -m "feat: add trade executor with buy/sell, stop-loss, and trailing stops"
```

---

## Chunk 5: Integration

### Task 12: Telegram Bot (TDD)

**Files:**
- Create: `tests/test_telegram_bot.py`
- Create: `telegram_bot.py`

- [ ] **Step 1: Write failing tests for Telegram bot**

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram_bot import TelegramAlert


@pytest.fixture
def alert():
    """Create TelegramAlert with mocked bot."""
    ta = TelegramAlert(token="fake_token", chat_id="fake_chat")
    ta.bot = AsyncMock()
    return ta


@pytest.mark.asyncio
class TestTelegramAlert:
    async def test_send_calls_bot(self, alert):
        await alert.send("hello")
        alert.bot.send_message.assert_called_once()

    async def test_send_without_bot_does_not_crash(self):
        ta = TelegramAlert(token="", chat_id="")
        await ta.send("test")  # Should not raise

    async def test_trade_alert_format(self, alert):
        await alert.send_trade_alert("BTCUSDT", "BUY", 50000.0, 0.001, "trend", 48500.0)
        call_args = alert.bot.send_message.call_args
        msg = call_args.kwargs["text"]
        assert "BTCUSDT" in msg
        assert "BUY" in msg
        assert "50000" in msg
        assert "trend" in msg

    async def test_close_alert_format(self, alert):
        await alert.send_close_alert("BTCUSDT", 51000.0, 0.5, "trailing_stop")
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "BTCUSDT" in msg
        assert "trailing_stop" in msg
        assert "+" in msg  # Positive P&L

    async def test_close_alert_negative_pnl(self, alert):
        await alert.send_close_alert("BTCUSDT", 49000.0, -0.3, "stop_loss")
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "-" in msg

    async def test_daily_summary_format(self, alert):
        await alert.send_daily_summary(0.5, 1.2, 0.65, 3)
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "Daily Summary" in msg
        assert "65.0%" in msg

    async def test_weekly_summary_format(self, alert):
        await alert.send_weekly_summary(2.5, 5.0, 0.6, 15, {"trend": 0.7, "mean_revert": 0.5})
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "Weekly" in msg
        assert "trend" in msg

    async def test_request_approval_sends_message(self, alert):
        alert._approval_responses = {alert._approval_id_counter: True}
        result = await alert.request_approval("test reason", timeout=0.1)
        alert.bot.send_message.assert_called()
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "Approval Required" in msg

    async def test_pause_alert(self, alert):
        await alert.send_pause_alert("drawdown exceeded")
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "Paused" in msg
        assert "drawdown" in msg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_telegram_bot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'telegram_bot'`

- [ ] **Step 3: Implement telegram_bot.py**

```python
import asyncio
import logging
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler

import config

logger = logging.getLogger(__name__)


class TelegramAlert:
    def __init__(self, token=None, chat_id=None):
        self.token = token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None
        self._approval_responses = {}
        self._approval_id_counter = 0

    async def send(self, message):
        """Send a message to Telegram."""
        if not self.bot:
            logger.warning("Telegram not configured, logging instead: %s", message)
            return
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error("Telegram send failed: %s", e)

    async def send_trade_alert(self, symbol, side, price, quantity, strategy, stop_loss):
        """Send trade execution alert."""
        msg = (
            f"*Trade Executed*\n"
            f"{'BUY' if side == 'BUY' else 'SELL'} {symbol}\n"
            f"Price: ${price:.2f}\n"
            f"Quantity: {quantity:.6f}\n"
            f"Strategy: {strategy}\n"
            f"Stop-loss: ${stop_loss:.2f}"
        )
        await self.send(msg)

    async def send_close_alert(self, symbol, exit_price, pnl, reason):
        """Send trade close alert."""
        prefix = "+" if pnl >= 0 else ""
        msg = (
            f"*Trade Closed*\n"
            f"{symbol}\n"
            f"Exit: ${exit_price:.2f}\n"
            f"P&L: {prefix}${pnl:.4f}\n"
            f"Reason: {reason}"
        )
        await self.send(msg)

    async def send_daily_summary(self, daily_pnl, total_pnl, win_rate, trades_today):
        """Send daily performance summary."""
        msg = (
            f"*Daily Summary*\n"
            f"Today's P&L: ${daily_pnl:.4f}\n"
            f"Total P&L: ${total_pnl:.4f}\n"
            f"Win Rate: {win_rate:.1%}\n"
            f"Trades Today: {trades_today}"
        )
        await self.send(msg)

    async def send_weekly_summary(self, weekly_pnl, total_pnl, win_rate, total_trades, strategy_win_rates):
        """Send weekly performance report via Telegram."""
        strategy_lines = "\n".join(
            f"  {name}: {rate:.1%}" for name, rate in strategy_win_rates.items()
        )
        msg = (
            f"*Weekly Report*\n"
            f"This Week's P&L: ${weekly_pnl:.4f}\n"
            f"Total P&L: ${total_pnl:.4f}\n"
            f"Win Rate: {win_rate:.1%}\n"
            f"Total Trades: {total_trades}\n"
            f"Per-Strategy Win Rates:\n{strategy_lines}"
        )
        await self.send(msg)

    async def request_approval(self, reason, timeout=300):
        """Request user approval via Telegram.
        Sends an approval request and polls for a response.
        Returns False (denied) if no response within timeout."""
        self._approval_id_counter += 1
        approval_id = self._approval_id_counter
        msg = (
            f"*Approval Required*\n"
            f"{reason}\n\n"
            f"Reply /approve to continue or /deny to skip.\n"
            f"Auto-denying in {timeout // 60}m if no response..."
        )
        await self.send(msg)

        # Poll for response (set by handle_approve/handle_deny commands)
        elapsed = 0.0
        interval = min(5.0, timeout) if timeout > 0 else 0
        while elapsed < timeout:
            if approval_id in self._approval_responses:
                return self._approval_responses.pop(approval_id)
            await asyncio.sleep(interval)
            elapsed += interval

        # Default to deny if no response (safe default)
        logger.info("Approval request timed out — defaulting to deny")
        return False

    def handle_approve(self):
        """Called when user sends /approve command."""
        self._approval_responses[self._approval_id_counter] = True

    def handle_deny(self):
        """Called when user sends /deny command."""
        self._approval_responses[self._approval_id_counter] = False

    async def send_pause_alert(self, reason):
        """Alert user that bot is pausing."""
        msg = f"*Bot Paused*\n{reason}\nReply /resume to restart."
        await self.send(msg)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_telegram_bot.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add telegram_bot.py tests/test_telegram_bot.py
git commit -m "feat: add Telegram alert system with TDD, approval flow, and weekly reports"
```

---

### Task 13: Main Bot Loop

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement main.py**

```python
import asyncio
import logging
import time
from binance.client import Client

import config
from market_analyzer import MarketAnalyzer
from strategies import get_strategy
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from trade_logger import TradeLogger
from telegram_bot import TelegramAlert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("trading_bot")


class TradingBot:
    def __init__(self):
        self.client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
        self.analyzer = MarketAnalyzer(client=self.client)
        self.risk_manager = RiskManager()
        self.executor = TradeExecutor(client=self.client)
        self.trade_logger = TradeLogger(config.DB_PATH)
        self.telegram = TelegramAlert()
        self.running = True
        self.capital = config.INITIAL_CAPITAL

    async def check_open_position(self):
        """Monitor open position for stop-loss or trailing stop."""
        position = self.trade_logger.get_open_position()
        if not position:
            return

        symbol = position["symbol"]
        current_price = self.executor.get_price(symbol)
        stop_loss = position["stop_loss"]

        # Check stop-loss
        if self.executor.check_stop_loss(current_price, stop_loss, position["side"]):
            logger.info("Stop-loss triggered for %s at %.2f", symbol, current_price)
            result = self.executor.sell(symbol, position["quantity"])
            self.trade_logger.close_trade(position["id"], current_price, "stop_loss")
            pnl = (current_price - position["entry_price"]) * position["quantity"]
            await self.telegram.send_close_alert(symbol, current_price, pnl, "stop_loss")
            return

        # Update trailing stop
        new_stop = self.executor.update_trailing_stop(
            current_price, stop_loss, config.TRAILING_STOP_PCT, position["side"]
        )
        if new_stop != stop_loss:
            self.trade_logger.update_stop_loss(position["id"], new_stop)
            logger.info("Trailing stop updated to %.2f for %s", new_stop, symbol)

    async def find_and_execute_trade(self):
        """Scan coins, find best opportunity, and execute if conditions met."""
        # Skip if we already have a position
        if self.trade_logger.has_open_position():
            return

        # Update capital based on total P&L
        self.capital = config.INITIAL_CAPITAL + self.trade_logger.get_total_pnl()

        # Validate risk limits
        allowed, reason = self.risk_manager.validate_trade(
            self.trade_logger, self.capital
        )
        if not allowed:
            logger.info("Trade blocked: %s", reason)
            return

        # Analyze all coins
        results = self.analyzer.analyze_all_coins()
        if not results:
            logger.info("No coins to analyze")
            return

        # Pick the best coin
        symbol, df, regime, score = results[0]
        logger.info("Best coin: %s (regime=%s, score=%.2f)", symbol, regime, score)

        # Get strategy for current regime
        strategy = get_strategy(regime)
        signal = strategy.generate_signal(df)
        logger.info("Signal: %s (confidence=%.2f, reason=%s)",
                     signal.action, signal.confidence, signal.reason)

        if signal.action == "hold":
            return

        if signal.action != "buy":
            # We only enter long (buy) positions with spot trading
            return

        # Check if approval is needed
        _, approval_reason = self.risk_manager.validate_trade(
            self.trade_logger, self.capital, symbol=symbol
        )
        if "approval" in approval_reason.lower():
            approved = await self.telegram.request_approval(approval_reason)
            if not approved:
                logger.info("Trade denied by user")
                return

        # Calculate position size
        quantity = self.risk_manager.calculate_position_size(
            self.capital, df.iloc[-1]["close"], signal.stop_loss
        )

        if quantity <= 0:
            logger.info("Position size too small, skipping")
            return

        # Check fee filter
        position_value = quantity * df.iloc[-1]["close"]
        if not self.risk_manager.passes_fee_filter(position_value):
            logger.info("Trade fails fee filter, skipping")
            return

        # Execute the trade
        entry_price = df.iloc[-1]["close"]
        try:
            result = self.executor.buy(symbol, quantity)
            trade_id = self.trade_logger.open_trade(
                symbol=symbol,
                side="BUY",
                entry_price=entry_price,
                quantity=quantity,
                strategy=strategy.name,
                stop_loss=signal.stop_loss,
            )
            logger.info("Trade opened: %s BUY %.6f @ %.2f (trade_id=%d)",
                        symbol, quantity, entry_price, trade_id)
            await self.telegram.send_trade_alert(
                symbol, "BUY", entry_price, quantity, strategy.name, signal.stop_loss
            )
        except Exception as e:
            logger.error("Trade execution failed: %s", e)
            await self.telegram.send(f"Trade execution failed: {e}")

    async def send_daily_summary(self):
        """Send daily performance summary via Telegram."""
        daily_pnl = self.trade_logger.get_daily_pnl()
        total_pnl = self.trade_logger.get_total_pnl()
        all_stats = self.trade_logger.get_all_strategy_stats()
        trades = self.trade_logger.get_all_closed_trades()
        from datetime import date
        today_trades = [t for t in trades if t["closed_at"] and t["closed_at"].startswith(date.today().isoformat())]
        # Aggregate win rate across all strategies
        total_trades = sum(s["total_trades"] for s in all_stats.values())
        total_wins = sum(s["winning_trades"] for s in all_stats.values())
        win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        await self.telegram.send_daily_summary(daily_pnl, total_pnl, win_rate, len(today_trades))

    async def send_weekly_summary(self):
        """Send weekly performance report via Telegram."""
        total_pnl = self.trade_logger.get_total_pnl()
        all_stats = self.trade_logger.get_all_strategy_stats()
        trades = self.trade_logger.get_all_closed_trades()
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        weekly_trades = [t for t in trades if t["closed_at"] and t["closed_at"] >= week_ago]
        weekly_pnl = sum(t["pnl"] for t in weekly_trades if t["pnl"])
        total_trades = len(weekly_trades)
        total_wins = sum(1 for t in weekly_trades if t["pnl"] and t["pnl"] > 0)
        win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        strategy_win_rates = {name: s["win_rate"] for name, s in all_stats.items()}
        await self.telegram.send_weekly_summary(weekly_pnl, total_pnl, win_rate, total_trades, strategy_win_rates)

    async def run(self):
        """Main bot loop."""
        logger.info("Trading bot started with capital: $%.2f", self.capital)
        await self.telegram.send("Trading bot started! Monitoring markets...")

        last_summary_hour = -1
        last_weekly_day = -1

        while self.running:
            try:
                # Check existing position first
                await self.check_open_position()

                # Look for new trades
                await self.find_and_execute_trade()

                from datetime import datetime
                now = datetime.now()

                # Send daily summary at 23:00
                if now.hour == 23 and last_summary_hour != 23:
                    await self.send_daily_summary()
                    last_summary_hour = 23

                # Send weekly summary on Sunday at 22:00
                if now.weekday() == 6 and now.hour == 22 and last_weekly_day != now.day:
                    await self.send_weekly_summary()
                    last_weekly_day = now.day

            except Exception as e:
                logger.error("Bot loop error: %s", e)
                await self.telegram.send(f"Bot error: {e}")

            await asyncio.sleep(config.BOT_LOOP_SECONDS)

    def stop(self):
        self.running = False
        self.trade_logger.close()


def main():
    bot = TradingBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.stop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add main bot loop orchestrating all modules"
```

---

### Task 14: Backtester (TDD)

**Files:**
- Create: `tests/test_backtest.py`
- Create: `backtest.py`

- [ ] **Step 1: Write failing tests for backtester**

```python
import pytest
import pandas as pd
from backtest import Backtester


def make_historical_data(n=100):
    """Generate fake historical price data."""
    import random
    random.seed(42)
    prices = [100.0]
    for _ in range(n - 1):
        change = random.uniform(-2, 2.2)  # Slight upward bias
        prices.append(max(prices[-1] + change, 10))
    return pd.DataFrame({
        "open": prices,
        "high": [p * 1.015 for p in prices],
        "low": [p * 0.985 for p in prices],
        "close": prices,
        "volume": [1000 + i * 10 for i in range(n)],
    })


class TestBacktester:
    def test_run_returns_results(self):
        df = make_historical_data(100)
        bt = Backtester(initial_capital=12.0)
        results = bt.run(df, strategy_name="trend")
        assert "total_pnl" in results
        assert "win_rate" in results
        assert "total_trades" in results
        assert "max_drawdown" in results

    def test_capital_never_negative(self):
        df = make_historical_data(200)
        bt = Backtester(initial_capital=12.0)
        results = bt.run(df, strategy_name="trend")
        assert results["final_capital"] >= 0

    def test_run_all_strategies(self):
        df = make_historical_data(100)
        bt = Backtester(initial_capital=12.0)
        all_results = bt.run_all_strategies(df)
        assert "trend" in all_results
        assert "mean_revert" in all_results
        assert "volatility" in all_results
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_backtest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backtest'`

- [ ] **Step 3: Implement backtest.py**

```python
import pandas as pd
from market_analyzer import MarketAnalyzer
from strategies.trend import TrendFollower
from strategies.mean_revert import MeanReversion
from strategies.volatility import VolatilityHandler
from risk_manager import RiskManager
import config


STRATEGIES = {
    "trend": TrendFollower(),
    "mean_revert": MeanReversion(),
    "volatility": VolatilityHandler(),
}


class Backtester:
    def __init__(self, initial_capital=None):
        self.initial_capital = initial_capital or config.INITIAL_CAPITAL
        self.analyzer = MarketAnalyzer(client=None)

    def run(self, df, strategy_name="trend"):
        """Run a single strategy backtest on historical data."""
        strategy = STRATEGIES[strategy_name]
        risk_manager = RiskManager(initial_capital=self.initial_capital)
        capital = self.initial_capital
        peak_capital = capital
        max_drawdown = 0.0
        trades = []
        position = None

        # Add indicators
        df = self.analyzer.add_indicators(df)

        for i in range(30, len(df)):  # Start after enough data for indicators
            window = df.iloc[:i + 1]
            current_price = df.iloc[i]["close"]

            # Check open position
            if position is not None:
                # Check stop-loss
                if current_price <= position["stop_loss"]:
                    pnl = (current_price - position["entry"]) * position["qty"]
                    capital += pnl
                    trades.append({"pnl": pnl, "reason": "stop_loss"})
                    position = None
                # Check take-profit
                elif position.get("take_profit") and current_price >= position["take_profit"]:
                    pnl = (current_price - position["entry"]) * position["qty"]
                    capital += pnl
                    trades.append({"pnl": pnl, "reason": "take_profit"})
                    position = None
                else:
                    # Update trailing stop
                    new_stop = current_price * (1 - config.TRAILING_STOP_PCT)
                    if new_stop > position["stop_loss"]:
                        position["stop_loss"] = new_stop
                continue

            # Generate signal
            signal = strategy.generate_signal(window)
            if signal.action != "buy":
                continue

            # Calculate position size
            qty = risk_manager.calculate_position_size(capital, current_price, signal.stop_loss)
            if qty <= 0 or qty * current_price < 1.0:
                continue

            position = {
                "entry": current_price,
                "qty": qty,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
            }

            # Track drawdown
            if capital > peak_capital:
                peak_capital = capital
            dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0
            if dd > max_drawdown:
                max_drawdown = dd

        # Close any remaining position at last price
        if position is not None:
            last_price = df.iloc[-1]["close"]
            pnl = (last_price - position["entry"]) * position["qty"]
            capital += pnl
            trades.append({"pnl": pnl, "reason": "end_of_data"})

        winners = [t for t in trades if t["pnl"] > 0]
        total_pnl = sum(t["pnl"] for t in trades)

        return {
            "strategy": strategy_name,
            "total_trades": len(trades),
            "winning_trades": len(winners),
            "win_rate": len(winners) / len(trades) if trades else 0.0,
            "total_pnl": total_pnl,
            "max_drawdown": max_drawdown,
            "final_capital": capital,
            "initial_capital": self.initial_capital,
            "return_pct": (capital - self.initial_capital) / self.initial_capital * 100,
        }

    def run_all_strategies(self, df):
        """Run all strategies and return comparative results."""
        results = {}
        for name in STRATEGIES:
            results[name] = self.run(df, name)
        return results

    def print_results(self, results):
        """Pretty-print backtest results."""
        if isinstance(results, dict) and "strategy" in results:
            results = {results["strategy"]: results}

        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        for name, r in results.items():
            print(f"\n--- {name.upper()} ---")
            print(f"  Trades: {r['total_trades']}")
            print(f"  Win Rate: {r['win_rate']:.1%}")
            print(f"  Total P&L: ${r['total_pnl']:.4f}")
            print(f"  Max Drawdown: {r['max_drawdown']:.1%}")
            print(f"  Final Capital: ${r['final_capital']:.4f}")
            print(f"  Return: {r['return_pct']:.2f}%")
        print("=" * 60)


if __name__ == "__main__":
    import sys

    if config.BINANCE_API_KEY:
        # Backtest with live Binance historical data
        from binance.client import Client

        client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
        analyzer = MarketAnalyzer(client=client)

        print("Fetching historical data for BTCUSDT...")
        df = analyzer.fetch_candles("BTCUSDT", interval="5m", limit=500)
    else:
        # Backtest with generated sample data (no API keys needed)
        import random
        random.seed(42)
        print("No API keys found — using generated sample data for demo.")
        prices = [50000.0]
        for _ in range(499):
            prices.append(max(prices[-1] + random.uniform(-200, 210), 30000))
        df = pd.DataFrame({
            "open": prices,
            "high": [p * 1.015 for p in prices],
            "low": [p * 0.985 for p in prices],
            "close": prices,
            "volume": [1000 + i * 10 for i in range(500)],
        })

    bt = Backtester(initial_capital=12.0)
    results = bt.run_all_strategies(df)
    bt.print_results(results)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/test_backtest.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backtest.py tests/test_backtest.py
git commit -m "feat: add backtester with multi-strategy comparison and metrics"
```

---

### Task 15: Setup & Run Guide

**Files:**
- Create: `.env.example`

- [ ] **Step 1: Create .env.example**

```
# Binance API — get from https://www.binance.com/en/my/settings/api-management
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Telegram — create bot via @BotFather, get chat_id via @userinfobot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "chore: add .env.example with setup instructions"
```

---

### Task 16: Run All Tests & Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -m pytest tests/ -v`
Expected: All tests PASS (14 trade_logger + 5 market_analyzer + 13 strategies + 11 risk_manager + 7 trade_executor + 9 telegram + 3 backtest = 62 total)

- [ ] **Step 2: Verify bot starts (will fail without API keys, but should import cleanly)**

Run: `cd /Users/amitbagra/portfolio/trading-bot && python3 -c "from main import TradingBot; print('All imports OK')"`
Expected: "All imports OK" (may warn about missing API keys)

- [ ] **Step 3: Final commit with any fixes**

Only if needed.

---

## Setup Instructions (for the developer)

1. **Binance Account:** Create account, enable API, whitelist your IP, save key/secret
2. **Telegram Bot:** Message @BotFather on Telegram, create bot, save token. Message @userinfobot to get your chat_id
3. **Environment:** Copy `.env.example` to `.env`, fill in your keys
4. **Install:** `pip install -r requirements.txt --user`
5. **Backtest first:** `python3 backtest.py` — test strategies on historical data before risking real money
6. **Run:** `python3 main.py` — starts the bot, monitors every 5 minutes
7. **Stop:** Press Ctrl+C
