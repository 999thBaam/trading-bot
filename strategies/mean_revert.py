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
        if rsi < config.RSI_OVERSOLD and close <= bb_lower * 1.02:
            distance_to_mean = (bb_middle - close) / close
            confidence = min(0.5 + distance_to_mean * 5, 1.0)
            return Signal(action="buy", confidence=max(confidence, 0.6), stop_loss=close - (1.5 * atr), take_profit=bb_middle, reason=f"RSI oversold ({rsi:.0f}) + near lower BB")
        if rsi > config.RSI_OVERBOUGHT and close >= bb_upper * 0.98:
            distance_to_mean = (close - bb_middle) / close
            confidence = min(0.5 + distance_to_mean * 5, 1.0)
            return Signal(action="sell", confidence=max(confidence, 0.6), stop_loss=close + (1.5 * atr), take_profit=bb_middle, reason=f"RSI overbought ({rsi:.0f}) + near upper BB")
        return Signal(action="hold", confidence=0.0, stop_loss=0.0, reason="RSI in neutral zone")
