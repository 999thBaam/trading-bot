import config


class TradeExecutor:
    def __init__(self, client):
        self.client = client

    def buy(self, symbol, quantity):
        return self.client.order_market_buy(symbol=symbol, quantity=quantity)

    def sell(self, symbol, quantity):
        return self.client.order_market_sell(symbol=symbol, quantity=quantity)

    def get_price(self, symbol):
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    def check_stop_loss(self, current_price, stop_loss, side):
        if side == "BUY":
            return current_price <= stop_loss
        else:
            return current_price >= stop_loss

    def update_trailing_stop(self, current_price, current_stop, trailing_pct, side):
        if side == "BUY":
            new_stop = current_price * (1 - trailing_pct)
            return max(new_stop, current_stop)
        else:
            new_stop = current_price * (1 + trailing_pct)
            return min(new_stop, current_stop)
