from __future__ import annotations

from collections import deque

from ai_trade_system.market import Bar, Signal
from ai_trade_system.strategy import Strategy


class DualMovingAverageStrategy(Strategy):
    def __init__(self, symbol: str, fast_window: int = 5, slow_window: int = 20, trade_size: int = 100) -> None:
        if fast_window <= 0 or slow_window <= 0:
            raise ValueError("windows must be positive")
        if fast_window >= slow_window:
            raise ValueError("fast_window must be smaller than slow_window")
        self.symbol = symbol
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.trade_size = trade_size
        self.closes: deque[float] = deque(maxlen=slow_window)
        self.previous_fast: float | None = None
        self.previous_slow: float | None = None
        self.in_position = False

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []

        self.closes.append(bar.close_price)
        if len(self.closes) < self.slow_window:
            return []

        closes = list(self.closes)
        fast = sum(closes[-self.fast_window :]) / self.fast_window
        slow = sum(closes) / self.slow_window
        signals: list[Signal] = []

        if self.previous_fast is None or self.previous_slow is None:
            if fast > slow and not self.in_position:
                signals.append(Signal("buy", bar.symbol, bar.close_price, self.trade_size, "fast_ma_above_slow_ma"))
                self.in_position = True
        else:
            crossed_up = self.previous_fast <= self.previous_slow and fast > slow
            crossed_down = self.previous_fast >= self.previous_slow and fast < slow
            if crossed_up and not self.in_position:
                signals.append(Signal("buy", bar.symbol, bar.close_price, self.trade_size, "fast_ma_cross_up"))
                self.in_position = True
            elif crossed_down and self.in_position:
                signals.append(Signal("sell", bar.symbol, bar.close_price, self.trade_size, "fast_ma_cross_down"))
                self.in_position = False

        self.previous_fast = fast
        self.previous_slow = slow
        return signals
