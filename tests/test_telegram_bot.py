import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram_bot import TelegramAlert

@pytest.fixture
def alert():
    ta = TelegramAlert(token="fake_token", chat_id="fake_chat")
    ta.bot = AsyncMock()
    return ta

@pytest.mark.asyncio
class TestTelegramAlert:
    async def test_send_calls_bot(self, alert):
        await alert.send("hello")
        alert.bot.send_message.assert_called_once()
    async def test_send_without_bot_does_not_crash(self):
        ta = TelegramAlert(token="", chat_id="")
        await ta.send("test")
    async def test_trade_alert_format(self, alert):
        await alert.send_trade_alert("BTCUSDT", "BUY", 50000.0, 0.001, "trend", 48500.0)
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "BTCUSDT" in msg
        assert "BUY" in msg
        assert "50000" in msg
        assert "trend" in msg
    async def test_close_alert_format(self, alert):
        await alert.send_close_alert("BTCUSDT", 51000.0, 0.5, "trailing_stop")
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "BTCUSDT" in msg
        assert "trailing_stop" in msg
        assert "+" in msg
    async def test_close_alert_negative_pnl(self, alert):
        await alert.send_close_alert("BTCUSDT", 49000.0, -0.3, "stop_loss")
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "-" in msg
    async def test_daily_summary_format(self, alert):
        await alert.send_daily_summary(0.5, 1.2, 0.65, 3)
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "Daily Summary" in msg
        assert "65.0%" in msg
    async def test_weekly_summary_format(self, alert):
        await alert.send_weekly_summary(2.5, 5.0, 0.6, 15, {"trend": 0.7, "mean_revert": 0.5})
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "Weekly" in msg
        assert "trend" in msg
    async def test_request_approval_sends_message(self, alert):
        alert._approval_responses[alert._approval_id_counter + 1] = True
        result = await alert.request_approval("test reason", timeout=0.1)
        alert.bot.send_message.assert_called()
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "Approval Required" in msg
    async def test_pause_alert(self, alert):
        await alert.send_pause_alert("drawdown exceeded")
        msg = alert.bot.send_message.call_args.kwargs["text"]
        assert "Paused" in msg
        assert "drawdown" in msg
