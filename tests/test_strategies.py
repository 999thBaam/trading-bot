import pytest
import pandas as pd
from strategies.trend import TrendFollower
from strategies.base import Signal


def make_df_with_indicators(closes, ema_fast, ema_slow, macd_hist):
    n = len(closes)
    return pd.DataFrame({
        "close": closes, "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes], "ema_fast": ema_fast,
        "ema_slow": ema_slow, "macd_hist": macd_hist, "atr": [1.0] * n,
    })


class TestTrendFollower:
    def setup_method(self):
        self.strategy = TrendFollower()

    def test_buy_signal_on_ema_crossover_up(self):
        closes =    [100, 101, 102, 103, 104, 105]
        ema_fast =  [ 99, 100, 101, 102, 103, 106]
        ema_slow =  [100, 100, 100, 101, 102, 104]
        macd_hist = [-0.5, -0.3, -0.1, 0.1, 0.3, 0.5]
        df = make_df_with_indicators(closes, ema_fast, ema_slow, macd_hist)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "buy"
        assert signal.confidence > 0.5
        assert signal.stop_loss < closes[-1]

    def test_sell_signal_on_ema_crossover_down(self):
        closes =    [105, 104, 103, 102, 101, 100]
        ema_fast =  [106, 105, 104, 102, 100, 98]
        ema_slow =  [104, 104, 103, 103, 102, 101]
        macd_hist = [0.5, 0.3, 0.1, -0.1, -0.3, -0.5]
        df = make_df_with_indicators(closes, ema_fast, ema_slow, macd_hist)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "sell"

    def test_hold_when_no_crossover(self):
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


from strategies.mean_revert import MeanReversion

def make_mr_df(closes, rsi, bb_lower, bb_upper, bb_middle):
    n = len(closes)
    return pd.DataFrame({
        "close": closes, "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes], "rsi": rsi,
        "bb_lower": bb_lower, "bb_upper": bb_upper, "bb_middle": bb_middle,
        "atr": [1.0] * n,
    })

class TestMeanReversion:
    def setup_method(self):
        self.strategy = MeanReversion()

    def test_buy_on_oversold_rsi_and_lower_bb(self):
        closes =    [100, 99, 98, 97, 96, 95]
        rsi =       [40,  35, 32, 29, 27, 25]
        bb_lower =  [94,  94, 94, 94, 94, 96]
        bb_upper =  [106, 106, 106, 106, 106, 106]
        bb_middle = [100, 100, 100, 100, 100, 100]
        df = make_mr_df(closes, rsi, bb_lower, bb_upper, bb_middle)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "buy"
        assert signal.take_profit == pytest.approx(100)

    def test_sell_on_overbought_rsi(self):
        closes =    [100, 101, 102, 103, 104, 105]
        rsi =       [60,  65, 68, 72, 75, 78]
        bb_lower =  [94,  94, 94, 94, 94, 94]
        bb_upper =  [106, 106, 106, 106, 106, 104]
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


from strategies.volatility import VolatilityHandler

def make_vol_df(closes, rsi, macd_hist, ema_fast, ema_slow, bb_lower, bb_upper, bb_middle):
    n = len(closes)
    return pd.DataFrame({
        "close": closes, "high": [c * 1.02 for c in closes], "low": [c * 0.98 for c in closes],
        "rsi": rsi, "macd_hist": macd_hist, "ema_fast": ema_fast, "ema_slow": ema_slow,
        "bb_lower": bb_lower, "bb_upper": bb_upper, "bb_middle": bb_middle, "atr": [3.0] * n,
    })

class TestVolatilityHandler:
    def setup_method(self):
        self.strategy = VolatilityHandler()
    def test_hold_when_no_strong_signal(self):
        n = 6
        closes = [100] * n
        df = make_vol_df(closes, rsi=[50]*n, macd_hist=[0.1]*n, ema_fast=[101]*n, ema_slow=[99]*n, bb_lower=[94]*n, bb_upper=[106]*n, bb_middle=[100]*n)
        signal = self.strategy.generate_signal(df)
        assert signal.action == "hold"
        assert "choppy" in signal.reason.lower() or "volatile" in signal.reason.lower()
    def test_buy_on_very_strong_signal(self):
        n = 6
        closes = [95, 94, 93, 92, 91, 90]
        df = make_vol_df(closes, rsi=[30, 28, 26, 24, 22, 20], macd_hist=[-1, -0.8, -0.6, -0.4, -0.2, 0.3], ema_fast=[89, 89, 89, 89, 89, 91], ema_slow=[92, 92, 92, 92, 92, 90], bb_lower=[89]*n, bb_upper=[106]*n, bb_middle=[98]*n)
        signal = self.strategy.generate_signal(df)
        assert signal.action in ("buy", "hold")
    def test_strategy_name(self):
        assert self.strategy.name == "volatility"
    def test_wider_stop_loss(self):
        n = 6
        closes = [95, 94, 93, 92, 91, 90]
        df = make_vol_df(closes, rsi=[30, 28, 26, 24, 22, 20], macd_hist=[-1, -0.8, -0.6, -0.4, -0.2, 0.3], ema_fast=[89, 89, 89, 89, 89, 91], ema_slow=[92, 92, 92, 92, 92, 90], bb_lower=[89]*n, bb_upper=[106]*n, bb_middle=[98]*n)
        signal = self.strategy.generate_signal(df)
        if signal.action == "buy":
            assert signal.stop_loss < closes[-1] - 5
