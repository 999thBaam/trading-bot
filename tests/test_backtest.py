import pytest
import pandas as pd
from backtest import Backtester

def make_historical_data(n=100):
    import random
    random.seed(42)
    prices = [100.0]
    for _ in range(n - 1):
        change = random.uniform(-2, 2.2)
        prices.append(max(prices[-1] + change, 10))
    return pd.DataFrame({
        "open": prices, "high": [p * 1.015 for p in prices],
        "low": [p * 0.985 for p in prices], "close": prices,
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
