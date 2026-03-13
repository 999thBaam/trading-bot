import pandas as pd
from strategies.base import BaseStrategy, Signal
import config


class VolatilityHandler(BaseStrategy):
    name = "volatility"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 3:
            return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="insufficient data")
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        close = curr["close"]
        atr = curr["atr"] if not pd.isna(curr["atr"]) else close * 0.02
        signals_agree = 0
        if curr["rsi"] < 25:
            signals_agree += 1
        elif curr["rsi"] > 75:
            signals_agree -= 1
        if prev["macd_hist"] < 0 and curr["macd_hist"] > 0:
            signals_agree += 1
        elif prev["macd_hist"] > 0 and curr["macd_hist"] < 0:
            signals_agree -= 1
        fast_above_now = curr["ema_fast"] > curr["ema_slow"]
        fast_above_prev = prev["ema_fast"] > prev["ema_slow"]
        if fast_above_now and not fast_above_prev:
            signals_agree += 1
        elif not fast_above_now and fast_above_prev:
            signals_agree -= 1
        if close <= curr["bb_lower"] * 1.01:
            signals_agree += 1
        elif close >= curr["bb_upper"] * 0.99:
            signals_agree -= 1
        if signals_agree >= 3:
            return Signal(action="buy", confidence=0.8, stop_loss=close - (3 * atr), take_profit=curr["bb_middle"], reason=f"High-confidence buy in volatile market ({signals_agree} indicators agree)")
        elif signals_agree <= -3:
            return Signal(action="sell", confidence=0.8, stop_loss=close + (3 * atr), take_profit=curr["bb_middle"], reason=f"High-confidence sell in volatile market ({signals_agree} indicators agree)")
        return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="Volatile market — sitting tight, no strong consensus")
