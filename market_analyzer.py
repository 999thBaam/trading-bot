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
