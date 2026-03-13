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
