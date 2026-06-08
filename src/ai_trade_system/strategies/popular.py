from __future__ import annotations

from collections import deque
from statistics import mean, pstdev

from ai_trade_system.market import Bar, Signal
from ai_trade_system.strategy import Strategy


class RsiMeanReversionStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        trade_size: int = 100,
    ) -> None:
        if rsi_period <= 1:
            raise ValueError("rsi_period must be greater than 1")
        if oversold >= overbought:
            raise ValueError("oversold must be smaller than overbought")
        self.symbol = symbol
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.trade_size = trade_size
        self.closes: deque[float] = deque(maxlen=rsi_period + 1)
        self.in_position = False

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        self.closes.append(bar.close_price)
        if len(self.closes) < self.rsi_period + 1:
            return []

        rsi = _rsi(list(self.closes))
        if rsi <= self.oversold and not self.in_position:
            self.in_position = True
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "rsi_oversold")]
        if rsi >= self.overbought and self.in_position:
            self.in_position = False
            return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, "rsi_overbought")]
        return []


class BollingerMeanReversionStrategy(Strategy):
    def __init__(self, symbol: str, window: int = 20, num_std: float = 2.0, trade_size: int = 100) -> None:
        if window <= 1:
            raise ValueError("window must be greater than 1")
        if num_std <= 0:
            raise ValueError("num_std must be positive")
        self.symbol = symbol
        self.window = window
        self.num_std = num_std
        self.trade_size = trade_size
        self.closes: deque[float] = deque(maxlen=window)
        self.in_position = False

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        self.closes.append(bar.close_price)
        if len(self.closes) < self.window:
            return []

        middle = mean(self.closes)
        width = pstdev(self.closes) * self.num_std
        lower = middle - width
        if bar.close_price <= lower and not self.in_position:
            self.in_position = True
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "below_lower_band")]
        if bar.close_price >= middle and self.in_position:
            self.in_position = False
            return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, "reverted_to_middle_band")]
        return []


class DonchianBreakoutStrategy(Strategy):
    def __init__(self, symbol: str, entry_window: int = 20, exit_window: int = 10, trade_size: int = 100) -> None:
        if entry_window <= 1 or exit_window <= 1:
            raise ValueError("entry_window and exit_window must be greater than 1")
        self.symbol = symbol
        self.entry_window = entry_window
        self.exit_window = exit_window
        self.trade_size = trade_size
        self.closes: deque[float] = deque(maxlen=max(entry_window, exit_window) + 1)
        self.in_position = False

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        previous = list(self.closes)
        self.closes.append(bar.close_price)
        if len(previous) < self.entry_window:
            return []

        entry_high = max(previous[-self.entry_window :])
        exit_low = min(previous[-self.exit_window :])
        if bar.close_price > entry_high and not self.in_position:
            self.in_position = True
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "donchian_breakout")]
        if bar.close_price < exit_low and self.in_position:
            self.in_position = False
            return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, "donchian_exit")]
        return []


class PriceMomentumStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        lookback: int = 20,
        entry_threshold: float = 0.05,
        exit_threshold: float = -0.03,
        trade_size: int = 100,
    ) -> None:
        if lookback <= 1:
            raise ValueError("lookback must be greater than 1")
        if exit_threshold >= entry_threshold:
            raise ValueError("exit_threshold must be smaller than entry_threshold")
        self.symbol = symbol
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.trade_size = trade_size
        self.closes: deque[float] = deque(maxlen=lookback + 1)
        self.in_position = False

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        self.closes.append(bar.close_price)
        if len(self.closes) < self.lookback + 1:
            return []

        base = self.closes[0]
        if base == 0:
            return []
        momentum = bar.close_price / base - 1
        if momentum >= self.entry_threshold and not self.in_position:
            self.in_position = True
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "positive_momentum")]
        if momentum <= self.exit_threshold and self.in_position:
            self.in_position = False
            return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, "negative_momentum")]
        return []


def _rsi(closes: list[float]) -> float:
    gains = []
    losses = []
    for previous, current in zip(closes, closes[1:]):
        change = current - previous
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    average_gain = sum(gains) / len(gains)
    average_loss = sum(losses) / len(losses)
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))
