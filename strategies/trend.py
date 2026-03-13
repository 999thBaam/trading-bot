import pandas as pd
from strategies.base import BaseStrategy, Signal


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
        lookback = min(len(df), 6)
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
            return Signal(action="buy", confidence=max(confidence, 0.6), stop_loss=close - (2 * atr), reason="EMA bullish crossover + MACD confirmation")
        if bearish_crossover and macd_negative:
            confidence = min(abs(curr["macd_hist"]) / (atr + 1e-9), 1.0)
            return Signal(action="sell", confidence=max(confidence, 0.6), stop_loss=close + (2 * atr), reason="EMA bearish crossover + MACD confirmation")
        return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="no crossover detected")
