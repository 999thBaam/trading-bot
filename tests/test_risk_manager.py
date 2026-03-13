import pytest
from unittest.mock import MagicMock
from risk_manager import RiskManager

@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.get_daily_pnl.return_value = 0.0
    logger.get_total_pnl.return_value = 0.0
    logger.get_consecutive_losses.return_value = 0
    logger.has_open_position.return_value = False
    logger.get_coins_traded.return_value = ["BTCUSDT"]
    return logger

@pytest.fixture
def rm():
    return RiskManager(initial_capital=12.0)

class TestPositionSizing:
    def test_basic_position_size(self, rm):
        size = rm.calculate_position_size(capital=12.0, entry_price=100.0, stop_loss=98.0)
        # risk_amount = 12*0.03 = 0.36, quantity = 0.36/2.0 = 0.18
        # max_quantity = 12/100 = 0.12, capped to min(0.18, 0.12) = 0.12
        assert size == pytest.approx(0.12)
    def test_position_size_respects_capital(self, rm):
        size = rm.calculate_position_size(capital=12.0, entry_price=100.0, stop_loss=99.9)
        max_quantity = 12.0 / 100.0
        assert size <= max_quantity
    def test_zero_stop_distance_returns_zero(self, rm):
        size = rm.calculate_position_size(capital=12.0, entry_price=100.0, stop_loss=100.0)
        assert size == 0.0

class TestDailyLimits:
    def test_within_daily_limit(self, rm, mock_logger):
        mock_logger.get_daily_pnl.return_value = -0.3
        assert rm.check_daily_limit(mock_logger, capital=12.0) is True
    def test_exceeded_daily_limit(self, rm, mock_logger):
        mock_logger.get_daily_pnl.return_value = -0.7
        assert rm.check_daily_limit(mock_logger, capital=12.0) is False

class TestDrawdown:
    def test_within_drawdown_limit(self, rm, mock_logger):
        mock_logger.get_total_pnl.return_value = -1.0
        assert rm.check_drawdown(mock_logger) is True
    def test_exceeded_drawdown(self, rm, mock_logger):
        mock_logger.get_total_pnl.return_value = -2.0
        assert rm.check_drawdown(mock_logger) is False

class TestFeeFilter:
    def test_trade_passes_fee_filter(self, rm):
        assert rm.passes_fee_filter(position_value=10.0) is True
    def test_tiny_trade_fails_fee_filter(self, rm):
        assert rm.passes_fee_filter(position_value=0.05) is True

class TestTradeValidation:
    def test_blocks_when_position_open(self, rm, mock_logger):
        mock_logger.has_open_position.return_value = True
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0)
        assert allowed is False
        assert "open position" in reason.lower()
    def test_blocks_on_daily_limit(self, rm, mock_logger):
        mock_logger.get_daily_pnl.return_value = -1.0
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0)
        assert allowed is False
    def test_allows_valid_trade(self, rm, mock_logger):
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0)
        assert allowed is True
    def test_needs_approval_after_loss_streak(self, rm, mock_logger):
        mock_logger.get_consecutive_losses.return_value = 3
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0)
        assert allowed is True
        assert "approval" in reason.lower()
    def test_needs_approval_for_new_coin(self, rm, mock_logger):
        mock_logger.get_coins_traded.return_value = ["BTCUSDT"]
        allowed, reason = rm.validate_trade(mock_logger, capital=12.0, symbol="ETHUSDT")
        assert allowed is True
        assert "approval" in reason.lower()
