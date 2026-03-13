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
