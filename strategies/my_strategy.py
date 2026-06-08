from ai_trade_system.market import Signal
from ai_trade_system.strategy import Strategy


class MyStrategy(Strategy):
    def __init__(self, symbol: str, trade_size: int = 100):
        self.symbol = symbol
        self.trade_size = trade_size

    def on_bar(self, bar):
        if bar.symbol != self.symbol:
            return []
        # Replace this demo condition with your own trading logic.
        if bar.close_price > bar.open_price:
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "close_above_open")]
        return []
