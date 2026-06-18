from __future__ import annotations

from collections import deque
from statistics import mean, pstdev

from ai_trade_system.market import Bar, Signal
from ai_trade_system.research import preview_research_signals
from ai_trade_system.research.chan_structure import scan_chan_structure
from ai_trade_system.research.dataframe import bars_to_frame
from ai_trade_system.strategy import Strategy


CHAN_CONFIRMATION_SIGNAL_KINDS = {
    "CHAN_STRUCT_BUY_T1_DIVERGENCE",
    "CHAN_STRUCT_SELL_T1_DIVERGENCE",
    "CHAN_STRUCT_BUY_CONFIRM",
    "CHAN_STRUCT_SELL_CONFIRM",
}
CHAN_STRUCTURE_SIGNAL_KINDS = {
    "CHAN_STRUCT_BUY_T2",
    "CHAN_STRUCT_SELL_T2",
    "CHAN_STRUCT_BUY_T3",
    "CHAN_STRUCT_SELL_T3",
}
CHAN_SIGNAL_MODES = {"confirmation", "structure", "all"}


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


class ChanRsiResearchStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        min_bars: int = 60,
        lookback: int = 120,
        trade_size: int = 100,
        min_signal_score: float = 18.0,
    ) -> None:
        if min_bars < 3:
            raise ValueError("min_bars must be at least 3")
        if lookback < min_bars:
            raise ValueError("lookback must be greater than or equal to min_bars")
        if trade_size <= 0:
            raise ValueError("trade_size must be positive")
        if min_signal_score < 0:
            raise ValueError("min_signal_score must be non-negative")
        self.symbol = symbol
        self.min_bars = min_bars
        self.lookback = lookback
        self.trade_size = trade_size
        self.min_signal_score = min_signal_score
        self.bars: deque[Bar] = deque(maxlen=lookback)
        self.in_position = False
        self.emitted: set[tuple[object, str, str]] = set()

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        self.bars.append(bar)
        if len(self.bars) < self.min_bars:
            return []

        preview = preview_research_signals(list(self.bars), min_bars=self.min_bars, lookback=self.lookback)
        candidates = [
            signal
            for signal in preview.signals
            if signal.trading_day == bar.trading_day and abs(signal.score) >= self.min_signal_score
        ]
        candidates.sort(key=lambda signal: abs(signal.score), reverse=True)
        for signal in candidates:
            key = (signal.trading_day, signal.kind, signal.action)
            if key in self.emitted:
                continue
            if signal.action == "buy" and not self.in_position:
                self.emitted.add(key)
                self.in_position = True
                return [Signal("buy", bar.symbol, signal.price, self.trade_size, f"research:{signal.kind}:{signal.reason}")]
            if signal.action == "sell" and self.in_position:
                self.emitted.add(key)
                self.in_position = False
                return [Signal("sell", bar.symbol, signal.price, self.trade_size, f"research:{signal.kind}:{signal.reason}")]
        return []


class ChanStructureStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        min_bars: int = 60,
        lookback: int = 160,
        min_stroke_bars: int = 5,
        min_rebound_pct: float = 0.03,
        min_signal_score: float = 30.0,
        signal_mode: str = "all",
        max_holding_bars: int = 0,
        trade_size: int = 100,
    ) -> None:
        if min_bars < 3:
            raise ValueError("min_bars must be at least 3")
        if lookback < min_bars:
            raise ValueError("lookback must be greater than or equal to min_bars")
        if min_stroke_bars < 1:
            raise ValueError("min_stroke_bars must be positive")
        if min_rebound_pct < 0:
            raise ValueError("min_rebound_pct must be non-negative")
        if min_signal_score < 0:
            raise ValueError("min_signal_score must be non-negative")
        if signal_mode not in CHAN_SIGNAL_MODES:
            raise ValueError("signal_mode must be one of: all, confirmation, structure")
        if max_holding_bars < 0:
            raise ValueError("max_holding_bars must be non-negative")
        if trade_size <= 0:
            raise ValueError("trade_size must be positive")
        self.symbol = symbol
        self.min_bars = min_bars
        self.lookback = lookback
        self.min_stroke_bars = min_stroke_bars
        self.min_rebound_pct = min_rebound_pct
        self.min_signal_score = min_signal_score
        self.signal_mode = signal_mode
        self.max_holding_bars = max_holding_bars
        self.trade_size = trade_size
        self.bars: deque[Bar] = deque(maxlen=lookback)
        self.in_position = False
        self.holding_bars = 0
        self.emitted: set[tuple[object, str, str]] = set()

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        self.bars.append(bar)
        if self.in_position:
            self.holding_bars += 1
        if len(self.bars) < self.min_bars:
            return []

        result = scan_chan_structure(
            bars_to_frame(list(self.bars)),
            min_stroke_bars=self.min_stroke_bars,
            min_rebound_pct=self.min_rebound_pct,
            lookback=self.lookback,
        )
        candidates = [
            signal
            for signal in result.signals
            if signal.trading_day == bar.trading_day
            and abs(signal.score) >= self.min_signal_score
            and self._signal_mode_allows(signal.kind)
        ]
        candidates.sort(key=lambda signal: abs(signal.score), reverse=True)
        for signal in candidates:
            key = (signal.trading_day, signal.kind, signal.action)
            if key in self.emitted:
                continue
            if signal.action == "buy" and not self.in_position:
                self.emitted.add(key)
                self.in_position = True
                self.holding_bars = 0
                return [Signal("buy", bar.symbol, signal.price, self.trade_size, f"chan_structure:{signal.kind}:{signal.reason}")]
            if signal.action == "sell" and self.in_position:
                self.emitted.add(key)
                self.in_position = False
                self.holding_bars = 0
                return [Signal("sell", bar.symbol, signal.price, self.trade_size, f"chan_structure:{signal.kind}:{signal.reason}")]
        if self.in_position and self.max_holding_bars > 0 and self.holding_bars >= self.max_holding_bars:
            self.in_position = False
            self.holding_bars = 0
            return [
                Signal(
                    "sell",
                    bar.symbol,
                    bar.close_price,
                    self.trade_size,
                    f"chan_structure:TIME_EXIT:max_holding_bars={self.max_holding_bars}",
                )
            ]
        return []

    def _signal_mode_allows(self, kind: str) -> bool:
        if self.signal_mode == "all":
            return True
        if self.signal_mode == "confirmation":
            return kind in CHAN_CONFIRMATION_SIGNAL_KINDS
        return kind in CHAN_STRUCTURE_SIGNAL_KINDS


class VolumeConfirmedMomentumStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        momentum_window: int = 20,
        min_momentum_pct: float = 0.08,
        volume_window: int = 20,
        volume_multiplier: float = 1.5,
        trend_window: int = 60,
        max_holding_bars: int = 20,
        trade_size: int = 100,
    ) -> None:
        self.symbol = symbol
        self.momentum_window = max(1, int(momentum_window))
        self.min_momentum_pct = float(min_momentum_pct)
        self.volume_window = max(1, int(volume_window))
        self.volume_multiplier = max(0.0, float(volume_multiplier))
        self.trend_window = max(1, int(trend_window))
        self.max_holding_bars = max(1, int(max_holding_bars))
        self.trade_size = max(1, int(trade_size))
        self.closes: deque[float] = deque(maxlen=max(self.momentum_window, self.trend_window) + 1)
        self.volumes: deque[float] = deque(maxlen=self.volume_window + 1)
        self.in_position = False
        self.holding_bars = 0

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []

        previous_closes = list(self.closes)
        previous_volumes = list(self.volumes)
        self.closes.append(bar.close_price)
        self.volumes.append(bar.volume)

        if self.in_position:
            self.holding_bars += 1
            exit_reason = self._exit_reason(bar.close_price, previous_closes)
            if exit_reason:
                self.in_position = False
                self.holding_bars = 0
                return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, exit_reason)]
            return []

        if not self._entry_ready(previous_closes, previous_volumes):
            return []
        if not self._has_price_momentum(bar.close_price, previous_closes):
            return []
        if not self._has_volume_confirmation(bar.volume, previous_volumes):
            return []
        if not self._passes_trend_filter(bar.close_price, previous_closes):
            return []

        self.in_position = True
        self.holding_bars = 0
        return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "volume_confirmed_momentum_entry")]

    def _entry_ready(self, previous_closes: list[float], previous_volumes: list[float]) -> bool:
        return len(previous_closes) >= max(self.momentum_window, self.trend_window) and len(previous_volumes) >= self.volume_window

    def _has_price_momentum(self, close_price: float, previous_closes: list[float]) -> bool:
        base = previous_closes[-self.momentum_window]
        return base > 0 and close_price / base - 1 >= self.min_momentum_pct

    def _has_volume_confirmation(self, volume: float, previous_volumes: list[float]) -> bool:
        if volume <= 0:
            return False
        baseline = mean(previous_volumes[-self.volume_window :])
        return baseline > 0 and volume >= baseline * self.volume_multiplier

    def _passes_trend_filter(self, close_price: float, previous_closes: list[float]) -> bool:
        trend_average = mean(previous_closes[-self.trend_window :])
        return close_price > trend_average

    def _exit_reason(self, close_price: float, previous_closes: list[float]) -> str | None:
        if len(previous_closes) >= self.momentum_window:
            base = previous_closes[-self.momentum_window]
            if base > 0 and close_price <= base:
                return "momentum_exit"
        if len(previous_closes) >= self.trend_window and close_price < mean(previous_closes[-self.trend_window :]):
            return "trend_exit"
        if self.holding_bars >= self.max_holding_bars:
            return "time_exit"
        return None


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
