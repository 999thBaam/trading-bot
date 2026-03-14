import pytest
from unittest.mock import MagicMock, patch
from trade_executor import TradeExecutor

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.order_market_buy.return_value = {"orderId": 12345, "executedQty": "0.001", "cummulativeQuoteQty": "50.0", "status": "FILLED"}
    client.order_market_sell.return_value = {"orderId": 12346, "executedQty": "0.001", "cummulativeQuoteQty": "50.0", "status": "FILLED"}
    client.get_symbol_ticker.return_value = {"price": "50000.0"}
    return client

@pytest.fixture
def executor(mock_client):
    return TradeExecutor(client=mock_client)

class TestTradeExecutor:
    @patch("trade_executor.config")
    def test_buy(self, mock_config, executor, mock_client):
        mock_config.PAPER_TRADING = False
        result = executor.buy("BTCUSDT", 0.001)
        mock_client.order_market_buy.assert_called_once_with(symbol="BTCUSDT", quantity=0.001)
        assert result["status"] == "FILLED"
    @patch("trade_executor.config")
    def test_sell(self, mock_config, executor, mock_client):
        mock_config.PAPER_TRADING = False
        result = executor.sell("BTCUSDT", 0.001)
        mock_client.order_market_sell.assert_called_once_with(symbol="BTCUSDT", quantity=0.001)
        assert result["status"] == "FILLED"
    @patch("trade_executor.config")
    def test_buy_paper_mode(self, mock_config, executor, mock_client):
        mock_config.PAPER_TRADING = True
        result = executor.buy("BTCUSDT", 0.001)
        mock_client.order_market_buy.assert_not_called()
        assert result["status"] == "FILLED"
        assert result["symbol"] == "BTCUSDT"
    @patch("trade_executor.config")
    def test_sell_paper_mode(self, mock_config, executor, mock_client):
        mock_config.PAPER_TRADING = True
        result = executor.sell("BTCUSDT", 0.001)
        mock_client.order_market_sell.assert_not_called()
        assert result["status"] == "FILLED"
        assert result["symbol"] == "BTCUSDT"
    def test_get_price(self, executor):
        price = executor.get_price("BTCUSDT")
        assert price == 50000.0
    def test_check_stop_loss_triggered(self, executor):
        assert executor.check_stop_loss(current_price=48000, stop_loss=48500, side="BUY") is True
    def test_check_stop_loss_not_triggered(self, executor):
        assert executor.check_stop_loss(current_price=51000, stop_loss=48500, side="BUY") is False
    def test_trailing_stop_update(self, executor):
        new_stop = executor.update_trailing_stop(current_price=52000, current_stop=49000, trailing_pct=0.02, side="BUY")
        assert new_stop == pytest.approx(50960.0)
    def test_trailing_stop_no_update_if_lower(self, executor):
        new_stop = executor.update_trailing_stop(current_price=49500, current_stop=49000, trailing_pct=0.02, side="BUY")
        assert new_stop == 49000
