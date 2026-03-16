import pandas as pd
from strategies.base import BaseStrategy, Signal
import config


class TrendFollower(BaseStrategy):
    name = "trend"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 3:
            return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="insufficient data")
        curr = df.iloc[-1]
        close = curr["close"]
        atr = curr["atr"] if not pd.isna(curr["atr"]) else close * 0.02
        macd_positive = curr["macd_hist"] > 0
        macd_negative = curr["macd_hist"] < 0

        # Scan recent bars for a crossover
        lookback = min(len(df), 8)
        bullish_crossover = False
        bearish_crossover = False
        for i in range(-lookback + 1, 0):
            prev_row = df.iloc[i - 1]
            curr_row = df.iloc[i]
            fast_above_now = curr_row["ema_fast"] > curr_row["ema_slow"]
            fast_above_prev = prev_row["ema_fast"] > prev_row["ema_slow"]
            if fast_above_now and not fast_above_prev:
                bullish_crossover = True
                bearish_crossover = False
            elif not fast_above_now and fast_above_prev:
                bearish_crossover = True
                bullish_crossover = False

        if bullish_crossover and macd_positive:
            confidence = min(abs(curr["macd_hist"]) / (atr + 1e-9), 1.0)
            return Signal(action="buy", confidence=max(confidence, 0.5), stop_loss=close - (1.75 * atr), reason="EMA bullish crossover + MACD confirmation")
        if bearish_crossover and macd_negative:
            confidence = min(abs(curr["macd_hist"]) / (atr + 1e-9), 1.0)
            return Signal(action="sell", confidence=max(confidence, 0.5), stop_loss=close + (1.75 * atr), reason="EMA bearish crossover + MACD confirmation")

        # Trend continuation: buy pullbacks in an established uptrend
        ema_aligned_up = curr["ema_fast"] > curr["ema_slow"]
        rsi = curr["rsi"] if not pd.isna(curr["rsi"]) else 50
        prev = df.iloc[-2]
        macd_rising = curr["macd_hist"] > prev["macd_hist"]
        if ema_aligned_up and macd_positive and rsi < config.RSI_OVERBOUGHT and macd_rising:
            confidence = min(0.4 + abs(curr["macd_hist"]) / (atr + 1e-9) * 0.5, 0.9)
            return Signal(action="buy", confidence=max(confidence, 0.5), stop_loss=close - (2 * atr), reason=f"Trend continuation — EMA aligned up, MACD rising, RSI={rsi:.0f}")

        # Trend continuation: sell rallies in an established downtrend
        ema_aligned_down = curr["ema_fast"] < curr["ema_slow"]
        macd_falling = curr["macd_hist"] < prev["macd_hist"]
        if ema_aligned_down and macd_negative and rsi > config.RSI_OVERSOLD and macd_falling:
            confidence = min(0.4 + abs(curr["macd_hist"]) / (atr + 1e-9) * 0.5, 0.9)
            return Signal(action="sell", confidence=max(confidence, 0.5), stop_loss=close + (2 * atr), reason=f"Trend continuation — EMA aligned down, MACD falling, RSI={rsi:.0f}")

        return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="no trend signal detected")
