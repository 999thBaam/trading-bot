import config


class RiskManager:
    def __init__(self, initial_capital=None):
        self.initial_capital = initial_capital or config.INITIAL_CAPITAL

    def calculate_position_size(self, capital, entry_price, stop_loss):
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance == 0:
            return 0.0
        risk_amount = capital * config.MAX_RISK_PER_TRADE
        quantity = risk_amount / stop_distance
        max_quantity = capital / entry_price
        return min(quantity, max_quantity)

    def check_daily_limit(self, trade_logger, capital):
        daily_pnl = trade_logger.get_daily_pnl()
        max_loss = capital * config.MAX_DAILY_LOSS
        return daily_pnl > -max_loss

    def check_drawdown(self, trade_logger):
        total_pnl = trade_logger.get_total_pnl()
        max_dd = self.initial_capital * config.MAX_DRAWDOWN
        return total_pnl > -max_dd

    def passes_fee_filter(self, position_value):
        if position_value <= 0:
            return False
        total_fees = position_value * config.FEE_RATE * 2
        return (total_fees / position_value) < config.MIN_FEE_RATIO

    def validate_trade(self, trade_logger, capital, symbol=None):
        if trade_logger.has_open_position():
            return False, "Blocked: already have an open position"
        if not self.check_daily_limit(trade_logger, capital):
            return False, "Blocked: daily loss limit exceeded. Needs approval to resume."
        if not self.check_drawdown(trade_logger):
            return False, "Blocked: max drawdown exceeded. Needs approval to resume."
        return True, "Trade allowed"
