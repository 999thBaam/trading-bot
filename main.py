import asyncio
import logging
import time
from binance.client import Client

import config
from market_analyzer import MarketAnalyzer
from strategies import get_strategy
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from trade_logger import TradeLogger
from telegram_bot import TelegramAlert

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("trading_bot")

class TradingBot:
    def __init__(self):
        self.client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
        self.analyzer = MarketAnalyzer(client=self.client)
        self.risk_manager = RiskManager()
        self.executor = TradeExecutor(client=self.client)
        db_path = config.PAPER_DB_PATH if config.PAPER_TRADING else config.DB_PATH
        self.trade_logger = TradeLogger(db_path)
        self.telegram = TelegramAlert()
        self.running = True
        self.capital = config.INITIAL_CAPITAL
        self.mode_label = "[PAPER] " if config.PAPER_TRADING else ""

    async def check_open_position(self):
        position = self.trade_logger.get_open_position()
        if not position:
            return
        symbol = position["symbol"]
        current_price = self.executor.get_price(symbol)
        stop_loss = position["stop_loss"]
        if self.executor.check_stop_loss(current_price, stop_loss, position["side"]):
            logger.info("%sStop-loss triggered for %s at %.2f", self.mode_label, symbol, current_price)
            self.executor.sell(symbol, position["quantity"])
            self.trade_logger.close_trade(position["id"], current_price, "stop_loss")
            pnl = (current_price - position["entry_price"]) * position["quantity"]
            prefix = "+" if pnl >= 0 else ""
            await self.telegram.send(f"{self.mode_label}*Trade Closed*\n{symbol}\nExit: ${current_price:.2f}\nP&L: {prefix}${pnl:.4f}\nReason: stop_loss")
            return
        new_stop = self.executor.update_trailing_stop(current_price, stop_loss, config.TRAILING_STOP_PCT, position["side"])
        if new_stop != stop_loss:
            self.trade_logger.update_stop_loss(position["id"], new_stop)
            logger.info("Trailing stop updated to %.2f for %s", new_stop, symbol)

    async def find_and_execute_trade(self):
        if self.trade_logger.has_open_position():
            return
        self.capital = config.INITIAL_CAPITAL + self.trade_logger.get_total_pnl()
        allowed, reason = self.risk_manager.validate_trade(self.trade_logger, self.capital)
        if not allowed:
            logger.info("Trade blocked: %s", reason)
            return
        results = self.analyzer.analyze_all_coins()
        if not results:
            return
        symbol, df, regime, score = results[0]
        logger.info("Best coin: %s (regime=%s, score=%.2f)", symbol, regime, score)
        strategy = get_strategy(regime)
        signal = strategy.generate_signal(df)
        logger.info("Signal: %s (confidence=%.2f, reason=%s)", signal.action, signal.confidence, signal.reason)
        if signal.action == "hold" or signal.action != "buy":
            return
        _, approval_reason = self.risk_manager.validate_trade(self.trade_logger, self.capital, symbol=symbol)
        if "approval" in approval_reason.lower():
            approved = await self.telegram.request_approval(approval_reason)
            if not approved:
                return
        quantity = self.risk_manager.calculate_position_size(self.capital, df.iloc[-1]["close"], signal.stop_loss)
        if quantity <= 0:
            return
        position_value = quantity * df.iloc[-1]["close"]
        if not self.risk_manager.passes_fee_filter(position_value):
            return
        entry_price = df.iloc[-1]["close"]
        try:
            self.executor.buy(symbol, quantity)
            trade_id = self.trade_logger.open_trade(symbol=symbol, side="BUY", entry_price=entry_price, quantity=quantity, strategy=strategy.name, stop_loss=signal.stop_loss)
            logger.info("%sTrade opened: %s BUY %.6f @ %.2f (trade_id=%d)", self.mode_label, symbol, quantity, entry_price, trade_id)
            await self.telegram.send(f"{self.mode_label}*Trade Executed*\nBUY {symbol}\nPrice: ${entry_price:.2f}\nQuantity: {quantity:.6f}\nStrategy: {strategy.name}\nStop-loss: ${signal.stop_loss:.2f}")
        except Exception as e:
            logger.error("Trade execution failed: %s", e)
            await self.telegram.send(f"Trade execution failed: {e}")

    async def send_daily_summary(self):
        daily_pnl = self.trade_logger.get_daily_pnl()
        total_pnl = self.trade_logger.get_total_pnl()
        all_stats = self.trade_logger.get_all_strategy_stats()
        trades = self.trade_logger.get_all_closed_trades()
        from datetime import date
        today_trades = [t for t in trades if t["closed_at"] and t["closed_at"].startswith(date.today().isoformat())]
        total_trades_count = sum(s["total_trades"] for s in all_stats.values())
        total_wins = sum(s["winning_trades"] for s in all_stats.values())
        win_rate = total_wins / total_trades_count if total_trades_count > 0 else 0.0
        await self.telegram.send_daily_summary(daily_pnl, total_pnl, win_rate, len(today_trades))

    async def send_weekly_summary(self):
        total_pnl = self.trade_logger.get_total_pnl()
        all_stats = self.trade_logger.get_all_strategy_stats()
        trades = self.trade_logger.get_all_closed_trades()
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        weekly_trades = [t for t in trades if t["closed_at"] and t["closed_at"] >= week_ago]
        weekly_pnl = sum(t["pnl"] for t in weekly_trades if t["pnl"])
        total_trades = len(weekly_trades)
        total_wins = sum(1 for t in weekly_trades if t["pnl"] and t["pnl"] > 0)
        win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        strategy_win_rates = {name: s["win_rate"] for name, s in all_stats.items()}
        await self.telegram.send_weekly_summary(weekly_pnl, total_pnl, win_rate, total_trades, strategy_win_rates)

    async def run(self):
        logger.info("%sTrading bot started with capital: $%.2f", self.mode_label, self.capital)
        await self.telegram.send(f"{self.mode_label}Trading bot started! Monitoring markets...")
        last_summary_hour = -1
        last_weekly_day = -1
        while self.running:
            try:
                await self.check_open_position()
                await self.find_and_execute_trade()
                from datetime import datetime
                now = datetime.now()
                if now.hour == 23 and last_summary_hour != 23:
                    await self.send_daily_summary()
                    last_summary_hour = 23
                if now.weekday() == 6 and now.hour == 22 and last_weekly_day != now.day:
                    await self.send_weekly_summary()
                    last_weekly_day = now.day
            except Exception as e:
                logger.error("Bot loop error: %s", e)
                await self.telegram.send(f"Bot error: {e}")
            await asyncio.sleep(config.BOT_LOOP_SECONDS)

    def stop(self):
        self.running = False
        self.trade_logger.close()

def main():
    bot = TradingBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.stop()

if __name__ == "__main__":
    main()
