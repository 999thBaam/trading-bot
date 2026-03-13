import logging
import pandas as pd
import ta

import config
from market_analyzer import MarketAnalyzer
from strategies.trend import TrendFollower
from strategies.mean_revert import MeanReversion
from strategies.volatility import VolatilityHandler
from risk_manager import RiskManager

logger = logging.getLogger(__name__)

STRATEGY_INSTANCES = {
    "trend": TrendFollower(),
    "mean_revert": MeanReversion(),
    "volatility": VolatilityHandler(),
}


class Backtester:
    def __init__(self, initial_capital=12.0, fee_rate=None):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate or config.FEE_RATE
        self.risk_manager = RiskManager(initial_capital=initial_capital)

    def _add_indicators(self, df):
        """Add technical indicators to the DataFrame for backtesting."""
        df = df.copy()
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

    def run(self, df, strategy_name="trend"):
        """Run backtest on historical data with a given strategy.

        Returns a dict with total_pnl, win_rate, total_trades, max_drawdown, final_capital, trades.
        """
        df = self._add_indicators(df)
        strategy = STRATEGY_INSTANCES.get(strategy_name)
        if not strategy:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        capital = self.initial_capital
        peak_capital = capital
        max_drawdown = 0.0
        trades = []
        in_position = False
        entry_price = 0.0
        quantity = 0.0
        stop_loss = 0.0

        # Need at least enough rows for indicators to warm up
        start_idx = max(30, len(df) // 5)

        for i in range(start_idx, len(df)):
            window = df.iloc[:i + 1].copy()
            current_price = window.iloc[-1]["close"]

            if in_position:
                # Check stop-loss
                if current_price <= stop_loss:
                    fee = current_price * quantity * self.fee_rate
                    pnl = (current_price - entry_price) * quantity - fee
                    capital += (current_price * quantity) - fee
                    capital = max(capital, 0.0)
                    trades.append({
                        "entry": entry_price,
                        "exit": current_price,
                        "pnl": pnl,
                        "reason": "stop_loss",
                    })
                    in_position = False
                    continue

                # Check trailing stop update
                new_stop = current_price * (1 - config.TRAILING_STOP_PCT)
                if new_stop > stop_loss:
                    stop_loss = new_stop

                # Check sell signal
                signal = strategy.generate_signal(window)
                if signal.action == "sell":
                    fee = current_price * quantity * self.fee_rate
                    pnl = (current_price - entry_price) * quantity - fee
                    capital += (current_price * quantity) - fee
                    capital = max(capital, 0.0)
                    trades.append({
                        "entry": entry_price,
                        "exit": current_price,
                        "pnl": pnl,
                        "reason": "signal",
                    })
                    in_position = False
            else:
                # Look for buy signal
                if capital <= 0:
                    continue
                signal = strategy.generate_signal(window)
                if signal.action == "buy" and signal.stop_loss > 0:
                    stop_distance = abs(current_price - signal.stop_loss)
                    if stop_distance == 0:
                        continue
                    risk_amount = capital * config.MAX_RISK_PER_TRADE
                    quantity = risk_amount / stop_distance
                    max_quantity = capital / current_price
                    quantity = min(quantity, max_quantity)
                    if quantity <= 0:
                        continue
                    fee = current_price * quantity * self.fee_rate
                    cost = current_price * quantity + fee
                    if cost > capital:
                        quantity = (capital / (current_price * (1 + self.fee_rate)))
                        fee = current_price * quantity * self.fee_rate
                        cost = current_price * quantity + fee
                    capital -= cost
                    capital = max(capital, 0.0)
                    entry_price = current_price
                    stop_loss = signal.stop_loss
                    in_position = True

            # Track drawdown
            total_value = capital + (quantity * current_price if in_position else 0)
            if total_value > peak_capital:
                peak_capital = total_value
            drawdown = (peak_capital - total_value) / peak_capital if peak_capital > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Close any open position at end
        if in_position:
            final_price = df.iloc[-1]["close"]
            fee = final_price * quantity * self.fee_rate
            pnl = (final_price - entry_price) * quantity - fee
            capital += (final_price * quantity) - fee
            capital = max(capital, 0.0)
            trades.append({
                "entry": entry_price,
                "exit": final_price,
                "pnl": pnl,
                "reason": "end_of_data",
            })

        total_pnl = capital - self.initial_capital
        winning = [t for t in trades if t["pnl"] > 0]
        win_rate = len(winning) / len(trades) if trades else 0.0

        return {
            "strategy": strategy_name,
            "total_pnl": total_pnl,
            "final_capital": capital,
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "trades": trades,
        }

    def run_all_strategies(self, df):
        """Run backtest for all strategies and return a dict of results."""
        results = {}
        for name in STRATEGY_INSTANCES:
            results[name] = self.run(df, strategy_name=name)
        return results


def generate_sample_data(n=200):
    """Generate sample price data for backtesting without API keys."""
    import random
    random.seed(42)
    prices = [100.0]
    for _ in range(n - 1):
        change = random.uniform(-2, 2.2)
        prices.append(max(prices[-1] + change, 10))
    return pd.DataFrame({
        "open": prices,
        "high": [p * 1.015 for p in prices],
        "low": [p * 0.985 for p in prices],
        "close": prices,
        "volume": [1000 + i * 10 for i in range(n)],
    })


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Try to fetch real data, fall back to sample data
    try:
        from binance.client import Client
        client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
        analyzer = MarketAnalyzer(client=client)
        df = analyzer.fetch_candles("BTCUSDT", limit=200)
        logger.info("Using real BTCUSDT data (200 candles)")
    except Exception:
        logger.info("No API keys or connection — using generated sample data")
        df = generate_sample_data(200)

    bt = Backtester(initial_capital=12.0)

    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    all_results = bt.run_all_strategies(df)
    for name, result in all_results.items():
        print(f"\n--- {name.upper()} ---")
        print(f"  Total P&L:      ${result['total_pnl']:.4f}")
        print(f"  Final Capital:   ${result['final_capital']:.4f}")
        print(f"  Total Trades:    {result['total_trades']}")
        print(f"  Win Rate:        {result['win_rate']:.1%}")
        print(f"  Max Drawdown:    {result['max_drawdown']:.1%}")

    # Find best strategy
    best = max(all_results.items(), key=lambda x: x[1]["total_pnl"])
    print(f"\nBest strategy: {best[0].upper()} (P&L: ${best[1]['total_pnl']:.4f})")
    print("=" * 60)
