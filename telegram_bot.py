import asyncio
import logging
from telegram import Bot

import config

logger = logging.getLogger(__name__)


class TelegramAlert:
    def __init__(self, token=None, chat_id=None):
        self.token = token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None
        self._approval_responses = {}
        self._approval_id_counter = 0

    async def send(self, message):
        if not self.bot:
            logger.warning("Telegram not configured, logging instead: %s", message)
            return
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error("Telegram send failed: %s", e)

    async def send_trade_alert(self, symbol, side, price, quantity, strategy, stop_loss):
        msg = f"*Trade Executed*\n{'BUY' if side == 'BUY' else 'SELL'} {symbol}\nPrice: ${price:.2f}\nQuantity: {quantity:.6f}\nStrategy: {strategy}\nStop-loss: ${stop_loss:.2f}"
        await self.send(msg)

    async def send_close_alert(self, symbol, exit_price, pnl, reason):
        prefix = "+" if pnl >= 0 else ""
        msg = f"*Trade Closed*\n{symbol}\nExit: ${exit_price:.2f}\nP&L: {prefix}${pnl:.4f}\nReason: {reason}"
        await self.send(msg)

    async def send_daily_summary(self, daily_pnl, total_pnl, win_rate, trades_today):
        msg = f"*Daily Summary*\nToday's P&L: ${daily_pnl:.4f}\nTotal P&L: ${total_pnl:.4f}\nWin Rate: {win_rate:.1%}\nTrades Today: {trades_today}"
        await self.send(msg)

    async def send_weekly_summary(self, weekly_pnl, total_pnl, win_rate, total_trades, strategy_win_rates):
        strategy_lines = "\n".join(f"  {name}: {rate:.1%}" for name, rate in strategy_win_rates.items())
        msg = f"*Weekly Report*\nThis Week's P&L: ${weekly_pnl:.4f}\nTotal P&L: ${total_pnl:.4f}\nWin Rate: {win_rate:.1%}\nTotal Trades: {total_trades}\nPer-Strategy Win Rates:\n{strategy_lines}"
        await self.send(msg)

    async def request_approval(self, reason, timeout=300):
        self._approval_id_counter += 1
        approval_id = self._approval_id_counter
        msg = f"*Approval Required*\n{reason}\n\nReply /approve to continue or /deny to skip.\nAuto-denying in {timeout // 60}m if no response..."
        await self.send(msg)
        elapsed = 0.0
        interval = min(5.0, timeout) if timeout > 0 else 0
        while elapsed < timeout:
            if approval_id in self._approval_responses:
                return self._approval_responses.pop(approval_id)
            await asyncio.sleep(interval)
            elapsed += interval
        logger.info("Approval request timed out — defaulting to deny")
        return False

    def handle_approve(self):
        self._approval_responses[self._approval_id_counter] = True

    def handle_deny(self):
        self._approval_responses[self._approval_id_counter] = False

    async def send_pause_alert(self, reason):
        msg = f"*Bot Paused*\n{reason}\nReply /resume to restart."
        await self.send(msg)
