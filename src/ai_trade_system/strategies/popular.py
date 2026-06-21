from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from statistics import mean, pstdev

from ai_trade_system.data import normalize_timeframe, read_bars_csv
from ai_trade_system.market import Bar, Signal
from ai_trade_system.research import preview_research_signals
from ai_trade_system.research.chan_core_v2 import ChanCoreV2Analyzer
from ai_trade_system.strategy import Strategy


CHAN_CONFIRMATION_SIGNAL_KINDS = {
    "CHAN_STRUCT_BUY_T1_DIVERGENCE",
    "CHAN_STRUCT_SELL_T1_DIVERGENCE",
    "CHAN_STRUCT_BUY_CONFIRM",
    "CHAN_STRUCT_SELL_CONFIRM",
    "CHAN_STRUCT_BUY_T3",
    "CHAN_STRUCT_SELL_T3",
}
CHAN_STRUCTURE_SIGNAL_KINDS = {
    "CHAN_STRUCT_BUY_T2",
    "CHAN_STRUCT_SELL_T2",
    "CHAN_STRUCT_BUY_T3",
    "CHAN_STRUCT_SELL_T3",
}
CHAN_SIGNAL_MODES = {"confirmation", "structure", "all"}
CHAN_WATCH_SIGNAL_KINDS = {
    "CHAN_STRUCT_BUY_T1_DIVERGENCE",
    "CHAN_STRUCT_SELL_T1_DIVERGENCE",
}
CHAN_ARMED_CONFIRMATION_SIGNAL_KINDS = {
    "CHAN_STRUCT_BUY_CONFIRM",
    "CHAN_STRUCT_SELL_CONFIRM",
    "CHAN_STRUCT_BUY_T2",
    "CHAN_STRUCT_SELL_T2",
    "CHAN_STRUCT_BUY_T3",
    "CHAN_STRUCT_SELL_T3",
}
CHAN_POINT_TYPES = {
    "first-buy",
    "first-sell",
    "second-buy",
    "second-sell",
    "third-buy",
    "third-sell",
}
CHAN_LEVELS = {"segment", "stroke", "fractal"}
CHAN_LOW_CONFIDENCE_GATES = {"off", "divergence", "trend", "divergence_or_trend"}
CHAN_LOW_CONFIDENCE_SIGNAL_KINDS = {"CHAN_STRUCT_BUY_T2", "CHAN_STRUCT_SELL_T2"}
CHAN_CORE_V2_TREND_LEVELS = {"stroke", "segment"}
CHAN_POSITION_CAP_MODES = {"off", "trend", "risk", "trend_risk"}
CHAN_VOLUME_WEAK_EXIT_MODES = {"reduce", "exit", "ignore"}
CHAN_MULTI_LEVEL_POLICIES = {"confirm_then_risk", "confirm_only"}
CHAN_MINUTE_MISSING_POLICIES = {"skip_entry", "daily_only"}
CHAN_MINUTE_SELL_MODES = {"reduce", "exit"}
CHAN_CONFIRM_TIMEFRAMES = {"30m"}
CHAN_RISK_TIMEFRAMES = {"15m"}
CHAN_SESSION_CLOSE = time(15, 0)


@dataclass(frozen=True)
class ArmedChanWatch:
    action: str
    kind: str
    score: float
    price: float
    reason: str
    trading_day: object
    bar_index: int


@dataclass
class ChanLowerLevelContext:
    timeframe: str
    csv_path: Path
    analyzer: object
    bars: list[Bar]
    next_index: int = 0
    latest_result: object | None = None

    @property
    def has_data(self) -> bool:
        return bool(self.bars)

    @property
    def has_consumed_data(self) -> bool:
        return self.next_index > 0


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


class MacdTrendStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        fast_period: int = 12,
        slow_period: int = 18,
        signal_period: int = 9,
        trend_window: int = 90,
        trade_size: int = 100,
    ) -> None:
        if fast_period <= 1 or slow_period <= 1 or signal_period <= 1 or trend_window <= 1:
            raise ValueError("fast_period, slow_period, signal_period, and trend_window must be greater than 1")
        if fast_period >= slow_period:
            raise ValueError("fast_period must be smaller than slow_period")
        self.symbol = symbol
        self.fast_period = int(fast_period)
        self.slow_period = int(slow_period)
        self.signal_period = int(signal_period)
        self.trend_window = int(trend_window)
        self.trade_size = max(1, int(trade_size))
        self.closes: deque[float] = deque(maxlen=self.trend_window)
        self.fast_ema: float | None = None
        self.slow_ema: float | None = None
        self.signal_ema: float | None = None
        self.previous_macd: float | None = None
        self.previous_signal: float | None = None
        self.bar_count = 0
        self.in_position = False

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []

        self.bar_count += 1
        self.closes.append(bar.close_price)
        self.fast_ema = _next_ema(self.fast_ema, bar.close_price, self.fast_period)
        self.slow_ema = _next_ema(self.slow_ema, bar.close_price, self.slow_period)
        macd_line = self.fast_ema - self.slow_ema
        self.signal_ema = _next_ema(self.signal_ema, macd_line, self.signal_period)

        if self.bar_count < max(self.slow_period, self.signal_period, self.trend_window):
            self.previous_macd = macd_line
            self.previous_signal = self.signal_ema
            return []

        bullish_cross = (
            self.previous_macd is not None
            and self.previous_signal is not None
            and self.previous_macd <= self.previous_signal
            and macd_line > self.signal_ema
        )
        bearish_cross = (
            self.previous_macd is not None
            and self.previous_signal is not None
            and self.previous_macd >= self.previous_signal
            and macd_line < self.signal_ema
        )
        trend_average = mean(self.closes)
        self.previous_macd = macd_line
        self.previous_signal = self.signal_ema

        if bullish_cross and not self.in_position and bar.close_price >= trend_average:
            self.in_position = True
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "macd_bullish_cross")]
        if self.in_position and bearish_cross:
            self.in_position = False
            return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, "macd_bearish_cross")]
        if self.in_position and bar.close_price < trend_average:
            self.in_position = False
            return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, "macd_trend_break")]
        return []


class AtrVolatilityBreakoutStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        breakout_window: int = 30,
        atr_window: int = 10,
        entry_atr_multiplier: float = 0.0,
        stop_atr_multiplier: float = 2.0,
        trailing_atr_multiplier: float = 3.0,
        max_holding_bars: int = 45,
        trade_size: int = 100,
    ) -> None:
        if breakout_window <= 1 or atr_window <= 1:
            raise ValueError("breakout_window and atr_window must be greater than 1")
        if entry_atr_multiplier < 0 or stop_atr_multiplier <= 0 or trailing_atr_multiplier <= 0:
            raise ValueError("ATR multipliers must be non-negative for entry and positive for exits")
        if max_holding_bars <= 0:
            raise ValueError("max_holding_bars must be positive")
        self.symbol = symbol
        self.breakout_window = int(breakout_window)
        self.atr_window = int(atr_window)
        self.entry_atr_multiplier = float(entry_atr_multiplier)
        self.stop_atr_multiplier = float(stop_atr_multiplier)
        self.trailing_atr_multiplier = float(trailing_atr_multiplier)
        self.max_holding_bars = int(max_holding_bars)
        self.trade_size = max(1, int(trade_size))
        self.highs: deque[float] = deque(maxlen=self.breakout_window)
        self.lows: deque[float] = deque(maxlen=self.breakout_window)
        self.closes: deque[float] = deque(maxlen=max(self.breakout_window, self.atr_window) + 1)
        self.true_ranges: deque[float] = deque(maxlen=self.atr_window)
        self.in_position = False
        self.entry_price: float | None = None
        self.highest_close_since_entry: float | None = None
        self.holding_bars = 0

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []

        previous_highs = list(self.highs)
        previous_close = self.closes[-1] if self.closes else None
        self.true_ranges.append(_true_range(bar, previous_close))
        self.highs.append(bar.high_price)
        self.lows.append(bar.low_price)
        self.closes.append(bar.close_price)
        if len(self.true_ranges) < self.atr_window:
            return []

        atr = mean(self.true_ranges)
        if self.in_position:
            self.holding_bars += 1
            if self.highest_close_since_entry is None or bar.close_price > self.highest_close_since_entry:
                self.highest_close_since_entry = bar.close_price
            exit_reason = self._exit_reason(bar.close_price, atr)
            if exit_reason:
                self.in_position = False
                self.entry_price = None
                self.highest_close_since_entry = None
                self.holding_bars = 0
                return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, exit_reason)]
            return []

        if len(previous_highs) < self.breakout_window:
            return []
        breakout_level = max(previous_highs[-self.breakout_window :]) + self.entry_atr_multiplier * atr
        if bar.close_price > breakout_level:
            self.in_position = True
            self.entry_price = bar.close_price
            self.highest_close_since_entry = bar.close_price
            self.holding_bars = 0
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "atr_volatility_breakout")]
        return []

    def _exit_reason(self, close_price: float, atr: float) -> str | None:
        if self.entry_price is not None and close_price <= self.entry_price - self.stop_atr_multiplier * atr:
            return "atr_stop_loss"
        if (
            self.highest_close_since_entry is not None
            and close_price <= self.highest_close_since_entry - self.trailing_atr_multiplier * atr
        ):
            return "atr_trailing_stop"
        if self.holding_bars >= self.max_holding_bars:
            return "time_exit"
        return None


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
        min_signal_score: float = 28.0,
        signal_mode: str = "all",
        allowed_point_types: str = "all",
        allowed_levels: str = "all",
        max_holding_bars: int = 15,
        watch_confirm_bars: int = 20,
        low_confidence_gate: str = "divergence_or_trend",
        low_confidence_min_score: float = 32.0,
        range_max_units: int = 1,
        position_cap_mode: str = "risk",
        trend_cap_units: int = 2,
        risk_drawdown_cap_pct: float = 8.0,
        low_confidence_units: int = 1,
        divergence_confirm_units: int = 2,
        high_confidence_units: int = 3,
        sell_confirm_units: int = 1,
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
        allowed_point_type_set = _parse_chan_filter_values(
            allowed_point_types, CHAN_POINT_TYPES, "allowed_point_types"
        )
        allowed_level_set = _parse_chan_filter_values(allowed_levels, CHAN_LEVELS, "allowed_levels")
        if max_holding_bars < 0:
            raise ValueError("max_holding_bars must be non-negative")
        if watch_confirm_bars < 0:
            raise ValueError("watch_confirm_bars must be non-negative")
        if low_confidence_gate not in CHAN_LOW_CONFIDENCE_GATES:
            raise ValueError("low_confidence_gate must be one of: off, divergence, trend, divergence_or_trend")
        if low_confidence_min_score < 0:
            raise ValueError("low_confidence_min_score must be non-negative")
        if position_cap_mode not in CHAN_POSITION_CAP_MODES:
            raise ValueError("position_cap_mode must be one of: off, trend, risk, trend_risk")
        if risk_drawdown_cap_pct < 0:
            raise ValueError("risk_drawdown_cap_pct must be non-negative")
        if low_confidence_units < 1:
            raise ValueError("low_confidence_units must be at least 1 units")
        if divergence_confirm_units < low_confidence_units:
            raise ValueError("divergence_confirm_units must be greater than or equal to low_confidence_units")
        if high_confidence_units < divergence_confirm_units:
            raise ValueError("high_confidence_units must be greater than or equal to divergence_confirm_units")
        if range_max_units < 0 or range_max_units > high_confidence_units:
            raise ValueError("range_max_units must be between 0 and high_confidence_units")
        if trend_cap_units < 1 or trend_cap_units > high_confidence_units:
            raise ValueError("trend_cap_units must be between 1 and high_confidence_units")
        if sell_confirm_units < 0 or sell_confirm_units >= high_confidence_units:
            raise ValueError("sell_confirm_units must be non-negative and smaller than high_confidence_units")
        if trade_size <= 0:
            raise ValueError("trade_size must be positive")
        self.symbol = symbol
        self.min_bars = min_bars
        self.lookback = lookback
        self.min_stroke_bars = min_stroke_bars
        self.min_rebound_pct = min_rebound_pct
        self.min_signal_score = min_signal_score
        self.signal_mode = signal_mode
        self.allowed_point_types = allowed_point_types
        self.allowed_levels = allowed_levels
        self.allowed_point_type_set = allowed_point_type_set
        self.allowed_level_set = allowed_level_set
        self.max_holding_bars = max_holding_bars
        self.watch_confirm_bars = watch_confirm_bars
        self.low_confidence_gate = low_confidence_gate
        self.low_confidence_min_score = low_confidence_min_score
        self.range_max_units = range_max_units
        self.position_cap_mode = position_cap_mode
        self.trend_cap_units = trend_cap_units
        self.risk_drawdown_cap_pct = risk_drawdown_cap_pct
        self.low_confidence_units = low_confidence_units
        self.divergence_confirm_units = divergence_confirm_units
        self.high_confidence_units = high_confidence_units
        self.sell_confirm_units = sell_confirm_units
        self.trade_size = trade_size
        self.bars: deque[Bar] = deque(maxlen=lookback)
        self.chan_analyzer = ChanCoreV2Analyzer(
            min_stroke_bars=self.min_stroke_bars,
            min_rebound_pct=self.min_rebound_pct,
            lookback=self.lookback,
        )
        self._position_units = 0
        self.holding_bars = 0
        self.bar_index = 0
        self.armed_watch: ArmedChanWatch | None = None
        self.average_entry_price: float | None = None
        self.emitted: set[tuple[object, str, str]] = set()

    @property
    def position_units(self) -> int:
        return self._position_units

    @position_units.setter
    def position_units(self, units: int) -> None:
        if units < 0:
            raise ValueError("position_units must be non-negative units")
        self._position_units = min(units, self.high_confidence_units)

    @property
    def in_position(self) -> bool:
        return self.position_units > 0

    @in_position.setter
    def in_position(self, value: bool) -> None:
        self.position_units = self.low_confidence_units if value else 0

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        self.bar_index += 1
        self.bars.append(bar)
        result = self.chan_analyzer.update_bar(bar)
        if self.in_position:
            self.holding_bars += 1
        if len(self.bars) < self.min_bars:
            return []

        self._expire_armed_watch()
        candidates = [signal for signal in result.signals if signal.trading_day == bar.trading_day]
        candidates.sort(key=lambda signal: abs(signal.score), reverse=True)
        for signal in candidates:
            if self._is_watch_signal(signal):
                self._arm_watch(signal)
                continue
            if self._armed_watch_confirms(signal):
                armed_watch = self.armed_watch
                if armed_watch is None:
                    continue
                key = (signal.trading_day, f"ARMED_CONFIRM:{armed_watch.kind}->{signal.kind}", signal.action)
                if key in self.emitted:
                    continue
                target_units = self._target_units_for_armed_confirmation(signal)
                target_units = self._cap_target_units(signal, result, target_units)
                if self._can_emit_target_units(signal.action, target_units):
                    self.emitted.add(key)
                    self.armed_watch = None
                    return self._emit_position_delta(
                        target_units,
                        bar,
                        signal.price,
                        f"chan_structure:ARMED_CONFIRM:{armed_watch.kind}->{signal.kind}:{signal.reason}",
                    )
            if (
                abs(signal.score) < self.min_signal_score
                or not self._signal_mode_allows(signal.kind)
                or not self._signal_filters_allow(signal)
            ):
                continue
            if not self._low_confidence_gate_allows(signal, result):
                continue
            key = (signal.trading_day, signal.kind, signal.action)
            if key in self.emitted:
                continue
            target_units = self._target_units_for_signal(signal)
            target_units = self._cap_target_units(signal, result, target_units)
            if self._can_emit_target_units(signal.action, target_units):
                self.emitted.add(key)
                self.armed_watch = None
                return self._emit_position_delta(
                    target_units,
                    bar,
                    signal.price,
                    f"chan_structure:{signal.kind}:{signal.reason}",
                )
        if self.in_position and self.max_holding_bars > 0 and self.holding_bars >= self.max_holding_bars:
            volume = self.position_units * self.trade_size
            self.position_units = 0
            self.average_entry_price = None
            self.holding_bars = 0
            self.armed_watch = None
            return [
                Signal(
                    "sell",
                    bar.symbol,
                    bar.close_price,
                    volume,
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

    def _signal_filters_allow(self, signal) -> bool:
        metadata = getattr(signal, "metadata", {}) or {}
        if self.allowed_point_type_set is not None and metadata.get("point_type") not in self.allowed_point_type_set:
            return False
        if self.allowed_level_set is not None and metadata.get("level") not in self.allowed_level_set:
            return False
        return True

    def _low_confidence_gate_allows(self, signal, result) -> bool:
        if signal.kind not in CHAN_LOW_CONFIDENCE_SIGNAL_KINDS:
            return True
        if self.low_confidence_gate == "off":
            return True
        if self.low_confidence_gate == "divergence":
            return False
        if abs(signal.score) >= self.low_confidence_min_score:
            return True
        return self._trend_context_allows_low_confidence(signal, result)

    def _trend_context_allows_low_confidence(self, signal, result) -> bool:
        if self.low_confidence_gate not in {"trend", "divergence_or_trend"}:
            return False
        trend = self._trend_for_signal(signal, result)
        if trend is None:
            return True
        trend_type = getattr(trend, "trend_type", "")
        if signal.action == "buy":
            if trend_type in {"up", "transition"}:
                return True
            if trend_type == "range":
                return self.position_units < self.range_max_units
            return False
        if signal.action == "sell":
            if trend_type in {"down", "transition", "range"}:
                return True
            return False
        return False

    def _trend_for_signal(self, signal, result):
        core_v2 = getattr(result, "core_v2", None)
        trends = list(getattr(core_v2, "trends", []) or [])
        if not trends:
            return None
        metadata = getattr(signal, "metadata", {}) or {}
        level = metadata.get("level")
        if level in CHAN_CORE_V2_TREND_LEVELS:
            for trend in reversed(trends):
                if getattr(trend, "level", None) == level:
                    return trend
        for fallback_level in ("stroke", "segment"):
            for trend in reversed(trends):
                if getattr(trend, "level", None) == fallback_level:
                    return trend
        return None

    def _cap_target_units(self, signal, result, target_units: int) -> int:
        target_units = self._clamp_position_units(target_units)
        if signal.action != "buy" or self.position_cap_mode == "off":
            return target_units
        capped = target_units
        if self.position_cap_mode in {"trend", "trend_risk"}:
            capped = min(capped, self._trend_cap_units(signal, result))
        if self.position_cap_mode in {"risk", "trend_risk"} and self._drawdown_cap_blocks_add(signal.price):
            capped = min(capped, self.position_units)
        return self._clamp_position_units(capped)

    def _trend_cap_units(self, signal, result) -> int:
        trend = self._trend_for_signal(signal, result)
        if trend is None:
            return self.high_confidence_units
        trend_type = getattr(trend, "trend_type", "")
        if trend_type == "up":
            return self.high_confidence_units
        if trend_type in {"transition", "range"}:
            return self.trend_cap_units
        if trend_type == "down":
            return self.low_confidence_units
        return self.high_confidence_units

    def _drawdown_cap_blocks_add(self, price: float) -> bool:
        if self.position_units <= 0 or self.average_entry_price is None:
            return False
        if self.average_entry_price <= 0:
            return False
        drawdown_pct = (price / self.average_entry_price - 1) * 100
        return drawdown_pct <= -self.risk_drawdown_cap_pct

    def _is_watch_signal(self, signal) -> bool:
        return signal.kind in CHAN_WATCH_SIGNAL_KINDS and "watch" in signal.tags

    def _arm_watch(self, signal) -> None:
        if self.watch_confirm_bars == 0:
            return
        if self.signal_mode == "structure":
            return
        if abs(signal.score) < self.min_signal_score:
            return
        if not self._can_arm_watch_action(signal.action):
            return
        self.armed_watch = ArmedChanWatch(
            action=signal.action,
            kind=signal.kind,
            score=signal.score,
            price=signal.price,
            reason=signal.reason,
            trading_day=signal.trading_day,
            bar_index=self.bar_index,
        )

    def _expire_armed_watch(self) -> None:
        if self.armed_watch is None:
            return
        if self.bar_index - self.armed_watch.bar_index > self.watch_confirm_bars:
            self.armed_watch = None

    def _armed_watch_confirms(self, signal) -> bool:
        if self.armed_watch is None:
            return False
        if self.bar_index <= self.armed_watch.bar_index:
            return False
        return (
            signal.action == self.armed_watch.action
            and signal.kind in CHAN_ARMED_CONFIRMATION_SIGNAL_KINDS
            and self._signal_filters_allow(signal)
        )

    def _can_emit_action(self, action: str) -> bool:
        return self._can_emit_target_units(action, self._target_units_for_action(action))

    def _target_units_for_action(self, action: str) -> int:
        if action == "buy":
            return self.divergence_confirm_units
        if action == "sell":
            return self.sell_confirm_units
        return self.position_units

    def _target_units_for_signal(self, signal) -> int:
        if signal.kind == "CHAN_STRUCT_BUY_T2":
            return self.low_confidence_units
        if signal.kind in {"CHAN_STRUCT_BUY_T1_DIVERGENCE", "CHAN_STRUCT_BUY_CONFIRM"}:
            return self.divergence_confirm_units
        if signal.kind == "CHAN_STRUCT_BUY_T3":
            return self.high_confidence_units
        if signal.kind == "CHAN_STRUCT_SELL_T2":
            return max(0, self.position_units - self.low_confidence_units)
        if signal.kind in {"CHAN_STRUCT_SELL_T1_DIVERGENCE", "CHAN_STRUCT_SELL_CONFIRM"}:
            return self.sell_confirm_units
        if signal.kind == "CHAN_STRUCT_SELL_T3":
            return 0
        return self.position_units

    def _target_units_for_armed_confirmation(self, signal) -> int:
        if signal.action == "buy":
            if signal.kind == "CHAN_STRUCT_BUY_T3":
                return self.high_confidence_units
            return self.divergence_confirm_units
        if signal.action == "sell":
            if signal.kind == "CHAN_STRUCT_SELL_T3":
                return 0
            return self.sell_confirm_units
        return self.position_units

    def _can_arm_watch_action(self, action: str) -> bool:
        if action == "buy":
            return self.position_units < self.high_confidence_units
        if action == "sell":
            return self.position_units > 0
        return False

    def _can_emit_target_units(self, action: str, target_units: int) -> bool:
        target_units = self._clamp_position_units(target_units)
        if action == "buy":
            return target_units > self.position_units
        if action == "sell":
            return target_units < self.position_units
        return False

    def _emit_position_delta(self, target_units: int, bar: Bar, price: float, reason: str) -> list[Signal]:
        target_units = self._clamp_position_units(target_units)
        current_units = self.position_units
        if target_units == current_units:
            return []
        action = "buy" if target_units > current_units else "sell"
        delta_units = abs(target_units - current_units)
        volume = delta_units * self.trade_size
        if action == "buy":
            previous_cost = (self.average_entry_price or price) * current_units
            new_cost = previous_cost + price * delta_units
            self.average_entry_price = new_cost / target_units if target_units > 0 else None
        elif target_units == 0:
            self.average_entry_price = None
        self.position_units = target_units
        self.holding_bars = 0
        return [Signal(action, bar.symbol, price, volume, reason)]

    def _clamp_position_units(self, units: int) -> int:
        return min(max(units, 0), self.high_confidence_units)


def _managed_level_csv_path(
    symbol: str,
    exchange: str,
    timeframe: str,
    adjust: str = "qfq",
    data_root: str | Path = "data/market/a_share",
) -> Path:
    normalized_timeframe = normalize_timeframe(timeframe)
    upper_exchange = exchange.upper()
    root = Path(data_root)
    return root / upper_exchange / symbol / f"{symbol}_{upper_exchange}_{normalized_timeframe}_{adjust}_latest.csv"


def _daily_session_close(bar: Bar) -> datetime:
    return datetime.combine(bar.trading_day, CHAN_SESSION_CLOSE)


def _bar_datetime(bar: Bar) -> datetime:
    return bar.timestamp or _daily_session_close(bar)


class ChanMultiLevelReversalStrategy(ChanStructureStrategy):
    def __init__(
        self,
        symbol: str,
        exchange: str = "SZSE",
        min_bars: int = 60,
        lookback: int = 160,
        min_stroke_bars: int = 5,
        min_rebound_pct: float = 0.03,
        min_daily_score: float = 28.0,
        min_confirm_score: float = 28.0,
        min_risk_score: float = 24.0,
        confirm_timeframe: str = "30m",
        risk_timeframe: str = "15m",
        lower_level_policy: str = "confirm_then_risk",
        minute_missing_policy: str = "skip_entry",
        minute_sell_mode: str = "reduce",
        confirm_csv_path: str | Path | None = None,
        risk_csv_path: str | Path | None = None,
        data_root: str | Path = "data/market/a_share",
        adjust: str = "qfq",
        signal_mode: str = "all",
        allowed_point_types: str = "all",
        allowed_levels: str = "all",
        max_holding_bars: int = 15,
        watch_confirm_bars: int = 20,
        low_confidence_gate: str = "divergence_or_trend",
        low_confidence_min_score: float = 32.0,
        range_max_units: int = 1,
        position_cap_mode: str = "risk",
        trend_cap_units: int = 2,
        risk_drawdown_cap_pct: float = 8.0,
        low_confidence_units: int = 1,
        divergence_confirm_units: int = 2,
        high_confidence_units: int = 3,
        sell_confirm_units: int = 1,
        trade_size: int = 100,
    ) -> None:
        if lower_level_policy not in CHAN_MULTI_LEVEL_POLICIES:
            raise ValueError("lower_level_policy must be one of: confirm_only, confirm_then_risk")
        if minute_missing_policy not in CHAN_MINUTE_MISSING_POLICIES:
            raise ValueError("minute_missing_policy must be one of: daily_only, skip_entry")
        if minute_sell_mode not in CHAN_MINUTE_SELL_MODES:
            raise ValueError("minute_sell_mode must be one of: exit, reduce")
        if min_daily_score < 0:
            raise ValueError("min_daily_score must be non-negative")
        if min_confirm_score < 0:
            raise ValueError("min_confirm_score must be non-negative")
        if min_risk_score < 0:
            raise ValueError("min_risk_score must be non-negative")
        if min_bars < 1:
            raise ValueError("min_bars must be at least 1")
        try:
            confirm_timeframe = normalize_timeframe(confirm_timeframe)
        except ValueError as exc:
            raise ValueError("confirm_timeframe must be one of: 30m") from exc
        if confirm_timeframe not in CHAN_CONFIRM_TIMEFRAMES:
            raise ValueError("confirm_timeframe must be one of: 30m")
        try:
            risk_timeframe = normalize_timeframe(risk_timeframe)
        except ValueError as exc:
            raise ValueError("risk_timeframe must be one of: 15m") from exc
        if risk_timeframe not in CHAN_RISK_TIMEFRAMES:
            raise ValueError("risk_timeframe must be one of: 15m")

        super().__init__(
            symbol=symbol,
            min_bars=max(min_bars, 3),
            lookback=lookback,
            min_stroke_bars=min_stroke_bars,
            min_rebound_pct=min_rebound_pct,
            min_signal_score=min_daily_score,
            signal_mode=signal_mode,
            allowed_point_types=allowed_point_types,
            allowed_levels=allowed_levels,
            max_holding_bars=max_holding_bars,
            watch_confirm_bars=watch_confirm_bars,
            low_confidence_gate=low_confidence_gate,
            low_confidence_min_score=low_confidence_min_score,
            range_max_units=range_max_units,
            position_cap_mode=position_cap_mode,
            trend_cap_units=trend_cap_units,
            risk_drawdown_cap_pct=risk_drawdown_cap_pct,
            low_confidence_units=low_confidence_units,
            divergence_confirm_units=divergence_confirm_units,
            high_confidence_units=high_confidence_units,
            sell_confirm_units=sell_confirm_units,
            trade_size=trade_size,
        )
        self.min_bars = min_bars
        self.exchange = exchange.upper()
        self.min_daily_score = min_daily_score
        self.min_confirm_score = min_confirm_score
        self.min_risk_score = min_risk_score
        self.confirm_timeframe = confirm_timeframe
        self.risk_timeframe = risk_timeframe
        self.lower_level_policy = lower_level_policy
        self.minute_missing_policy = minute_missing_policy
        self.minute_sell_mode = minute_sell_mode
        confirm_path = (
            Path(confirm_csv_path)
            if confirm_csv_path is not None
            else _managed_level_csv_path(symbol, self.exchange, confirm_timeframe, adjust, data_root)
        )
        risk_path = (
            Path(risk_csv_path)
            if risk_csv_path is not None
            else _managed_level_csv_path(symbol, self.exchange, risk_timeframe, adjust, data_root)
        )
        self.confirm_context = self._build_lower_level_context(confirm_timeframe, confirm_path)
        self.risk_context = self._build_lower_level_context(risk_timeframe, risk_path)

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []

        self.bar_index += 1
        self.bars.append(bar)
        daily_result = self.chan_analyzer.update_bar(bar)
        cutoff = _daily_session_close(bar)
        confirm_result = self._update_lower_level_context(self.confirm_context, cutoff)
        risk_result = self._update_lower_level_context(self.risk_context, cutoff)

        if self.in_position:
            self.holding_bars += 1
        if len(self.bars) < self.min_bars:
            return []

        risk_signal = self._best_signal(risk_result, bar, "sell", self.min_risk_score)
        if self.in_position and risk_signal is not None and self.lower_level_policy == "confirm_then_risk":
            target_units = 0 if self.minute_sell_mode == "exit" else max(0, self.position_units - 1)
            return self._emit_position_delta_or_time_exit(
                target_units,
                bar,
                risk_signal.price,
                f"chan_multilevel:RISK_15M:{risk_signal.kind}:{risk_signal.reason}",
            )

        daily_sell = self._best_signal(daily_result, bar, "sell", self.min_daily_score)
        confirm_sell = self._best_signal(confirm_result, bar, "sell", self.min_confirm_score)
        sell_signal = daily_sell or confirm_sell
        if self.in_position and sell_signal is not None:
            target_units = self._target_units_for_signal(sell_signal)
            if sell_signal is confirm_sell and target_units >= self.position_units:
                target_units = max(0, self.position_units - 1)
            return self._emit_position_delta_or_time_exit(
                target_units,
                bar,
                sell_signal.price,
                f"chan_multilevel:{'CONFIRM_30M' if sell_signal is confirm_sell else 'DAILY'}:{sell_signal.kind}:{sell_signal.reason}",
            )

        daily_buy = self._best_signal(daily_result, bar, "buy", self.min_daily_score)
        if daily_buy is None:
            return self._time_exit_if_needed(bar)

        confirm_buy = self._best_signal(confirm_result, bar, "buy", self.min_confirm_score)
        if confirm_buy is None:
            if self.minute_missing_policy != "daily_only" or self.confirm_context.has_consumed_data:
                return self._time_exit_if_needed(bar)
            target_units = self._cap_target_units(daily_buy, daily_result, self._target_units_for_signal(daily_buy))
            return self._emit_position_delta_or_time_exit(
                target_units,
                bar,
                daily_buy.price,
                f"chan_multilevel:DAILY_FALLBACK:{daily_buy.kind}:{daily_buy.reason}",
            )

        if self.lower_level_policy == "confirm_then_risk" and risk_signal is not None:
            return []
        target_units = self._cap_target_units(daily_buy, daily_result, self._target_units_for_signal(daily_buy))
        return self._emit_position_delta_or_time_exit(
            target_units,
            bar,
            confirm_buy.price,
            f"chan_multilevel:CONFIRM_30M:{daily_buy.kind}+{confirm_buy.kind}:{daily_buy.reason}",
        )

    def _build_lower_level_context(self, timeframe: str, csv_path: Path) -> ChanLowerLevelContext:
        bars: list[Bar] = []
        if csv_path.exists():
            loaded = read_bars_csv(csv_path)
            bars = [
                bar
                for bar in loaded
                if bar.symbol == self.symbol
                and bar.exchange.upper() == self.exchange
                and normalize_timeframe(bar.timeframe) == timeframe
            ]
            bars.sort(key=_bar_datetime)
        return ChanLowerLevelContext(
            timeframe=timeframe,
            csv_path=csv_path,
            analyzer=ChanCoreV2Analyzer(
                min_stroke_bars=self.min_stroke_bars,
                min_rebound_pct=self.min_rebound_pct,
                lookback=self.lookback,
            ),
            bars=bars,
        )

    def _update_lower_level_context(self, context: ChanLowerLevelContext, cutoff: datetime):
        while context.next_index < len(context.bars) and _bar_datetime(context.bars[context.next_index]) <= cutoff:
            context.latest_result = context.analyzer.update_bar(context.bars[context.next_index])
            context.next_index += 1
        return context.latest_result

    def _best_signal(self, result, bar: Bar, action: str, min_score: float):
        if result is None:
            return None
        candidates = [
            signal
            for signal in getattr(result, "signals", []) or []
            if signal.trading_day == bar.trading_day
            and signal.action == action
            and abs(signal.score) >= min_score
            and self._signal_mode_allows(signal.kind)
            and self._signal_filters_allow(signal)
        ]
        candidates.sort(key=lambda signal: abs(signal.score), reverse=True)
        return candidates[0] if candidates else None

    def _emit_position_delta_or_time_exit(self, target_units: int, bar: Bar, price: float, reason: str) -> list[Signal]:
        signals = self._emit_position_delta(target_units, bar, price, reason)
        if signals:
            return signals
        return self._time_exit_if_needed(bar)

    def _time_exit_if_needed(self, bar: Bar) -> list[Signal]:
        if not self.in_position or self.max_holding_bars <= 0 or self.holding_bars < self.max_holding_bars:
            return []
        volume = self.position_units * self.trade_size
        self.position_units = 0
        self.average_entry_price = None
        self.holding_bars = 0
        self.armed_watch = None
        return [
            Signal(
                "sell",
                bar.symbol,
                bar.close_price,
                volume,
                f"chan_multilevel:TIME_EXIT:max_holding_bars={self.max_holding_bars}",
            )
        ]


class ChanVolumeFusionStrategy(ChanStructureStrategy):
    def __init__(
        self,
        symbol: str,
        min_bars: int = 60,
        lookback: int = 160,
        min_stroke_bars: int = 5,
        min_rebound_pct: float = 0.03,
        min_signal_score: float = 28.0,
        signal_mode: str = "all",
        allowed_point_types: str = "all",
        allowed_levels: str = "all",
        max_holding_bars: int = 15,
        watch_confirm_bars: int = 20,
        low_confidence_gate: str = "divergence_or_trend",
        low_confidence_min_score: float = 32.0,
        range_max_units: int = 1,
        position_cap_mode: str = "risk",
        trend_cap_units: int = 2,
        risk_drawdown_cap_pct: float = 8.0,
        momentum_window: int = 15,
        min_momentum_pct: float = 0.08,
        volume_window: int = 20,
        volume_multiplier: float = 1.1,
        trend_window: int = 60,
        low_confidence_requires_volume: bool = True,
        high_confidence_volume_boost: bool = True,
        volume_boost_units: int = 1,
        strong_volume_extend_bars: int = 5,
        weak_volume_exit_mode: str = "reduce",
        weak_volume_momentum_pct: float = -0.02,
        weak_volume_requires_trend_break: bool = True,
        continuation_trend_window: int = 60,
        severe_weak_momentum_pct: float = -0.04,
        low_confidence_units: int = 1,
        divergence_confirm_units: int = 2,
        high_confidence_units: int = 2,
        sell_confirm_units: int = 1,
        max_units: int = 3,
        trade_size: int = 100,
    ) -> None:
        if momentum_window <= 0 or volume_window <= 0 or trend_window <= 0:
            raise ValueError("momentum_window, volume_window, and trend_window must be positive")
        if continuation_trend_window <= 0:
            raise ValueError("continuation_trend_window must be positive")
        if volume_multiplier < 0:
            raise ValueError("volume_multiplier must be non-negative")
        if volume_boost_units < 0:
            raise ValueError("volume_boost_units must be non-negative")
        if strong_volume_extend_bars < 0:
            raise ValueError("strong_volume_extend_bars must be non-negative")
        if weak_volume_exit_mode not in CHAN_VOLUME_WEAK_EXIT_MODES:
            raise ValueError("weak_volume_exit_mode must be one of: reduce, exit, ignore")
        if max_units < high_confidence_units:
            raise ValueError("max_units must be greater than or equal to high_confidence_units")

        self.max_units = int(max_units)
        super().__init__(
            symbol=symbol,
            min_bars=min_bars,
            lookback=lookback,
            min_stroke_bars=min_stroke_bars,
            min_rebound_pct=min_rebound_pct,
            min_signal_score=min_signal_score,
            signal_mode=signal_mode,
            allowed_point_types=allowed_point_types,
            allowed_levels=allowed_levels,
            max_holding_bars=max_holding_bars,
            watch_confirm_bars=watch_confirm_bars,
            low_confidence_gate=low_confidence_gate,
            low_confidence_min_score=low_confidence_min_score,
            range_max_units=range_max_units,
            position_cap_mode=position_cap_mode,
            trend_cap_units=trend_cap_units,
            risk_drawdown_cap_pct=risk_drawdown_cap_pct,
            low_confidence_units=low_confidence_units,
            divergence_confirm_units=divergence_confirm_units,
            high_confidence_units=high_confidence_units,
            sell_confirm_units=sell_confirm_units,
            trade_size=trade_size,
        )
        self.momentum_window = int(momentum_window)
        self.min_momentum_pct = float(min_momentum_pct)
        self.volume_window = int(volume_window)
        self.volume_multiplier = float(volume_multiplier)
        self.trend_window = int(trend_window)
        self.low_confidence_requires_volume = bool(low_confidence_requires_volume)
        self.high_confidence_volume_boost = bool(high_confidence_volume_boost)
        self.volume_boost_units = int(volume_boost_units)
        self.strong_volume_extend_bars = int(strong_volume_extend_bars)
        self.weak_volume_exit_mode = weak_volume_exit_mode
        self.weak_volume_momentum_pct = float(weak_volume_momentum_pct)
        self.weak_volume_requires_trend_break = bool(weak_volume_requires_trend_break)
        self.continuation_trend_window = int(continuation_trend_window)
        self.severe_weak_momentum_pct = float(severe_weak_momentum_pct)
        self._latest_volume_momentum = 0.0
        self._latest_continuation_trend_average: float | None = None
        self.volume_closes: deque[float] = deque(
            maxlen=max(self.momentum_window, self.trend_window, self.continuation_trend_window) + 1
        )
        self.volume_volumes: deque[float] = deque(maxlen=self.volume_window + 1)

    @property
    def position_units(self) -> int:
        return self._position_units

    @position_units.setter
    def position_units(self, units: int) -> None:
        if units < 0:
            raise ValueError("position_units must be non-negative units")
        self._position_units = self._clamp_position_units(units)

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        self.bar_index += 1
        self.bars.append(bar)
        volume_state = self._update_volume_state(bar)
        result = self.chan_analyzer.update_bar(bar)
        if self.in_position:
            self.holding_bars += 1
        if len(self.bars) < self.min_bars:
            return []

        self._expire_armed_watch()
        candidates = [signal for signal in result.signals if signal.trading_day == bar.trading_day]
        candidates.sort(key=lambda signal: abs(signal.score), reverse=True)
        for signal in candidates:
            if self._is_watch_signal(signal):
                self._arm_watch(signal)
                continue
            if self._armed_watch_confirms(signal):
                armed_watch = self.armed_watch
                if armed_watch is None:
                    continue
                key = (signal.trading_day, f"ARMED_CONFIRM:{armed_watch.kind}->{signal.kind}", signal.action)
                if key in self.emitted:
                    continue
                target_units = self._target_units_for_armed_confirmation(signal)
                target_units = self._cap_target_units(signal, result, target_units)
                target_units = self._apply_buy_volume_boost(signal, target_units, volume_state)
                target_units = self._apply_risk_cap_after_volume_boost(signal, target_units)
                if self._can_emit_target_units(signal.action, target_units):
                    self.emitted.add(key)
                    self.armed_watch = None
                    return self._emit_position_delta(
                        target_units,
                        bar,
                        signal.price,
                        self._armed_reason(armed_watch, signal, volume_state),
                    )
            if (
                abs(signal.score) < self.min_signal_score
                or not self._signal_mode_allows(signal.kind)
                or not self._signal_filters_allow(signal)
            ):
                continue
            if not self._low_confidence_gate_allows(signal, result):
                continue
            if signal.kind == "CHAN_STRUCT_BUY_T2" and not self._volume_allows_low_confidence(volume_state):
                continue
            key = (signal.trading_day, signal.kind, signal.action)
            if key in self.emitted:
                continue
            base_target_units = self._target_units_for_signal(signal)
            target_units = self._cap_target_units(signal, result, base_target_units)
            target_units = self._apply_buy_volume_boost(signal, target_units, volume_state)
            target_units = self._apply_risk_cap_after_volume_boost(signal, target_units)
            if self._can_emit_target_units(signal.action, target_units):
                self.emitted.add(key)
                self.armed_watch = None
                return self._emit_position_delta(
                    target_units,
                    bar,
                    signal.price,
                    self._signal_reason(signal, volume_state, target_units, base_target_units),
                )

        if self.in_position and volume_state == "weak" and self._weak_volume_should_reduce(bar, result):
            target_units = self._weak_volume_target_units(self.position_units)
            if self._can_emit_target_units("sell", target_units):
                return self._emit_position_delta(
                    target_units,
                    bar,
                    bar.close_price,
                    f"chan_volume_fusion:CHAN_VOLUME_WEAK_{self.weak_volume_exit_mode.upper()}:volume=weak",
                )

        effective_max_holding = self._effective_max_holding_bars(volume_state)
        if self.in_position and effective_max_holding > 0 and self.holding_bars >= effective_max_holding:
            volume = self.position_units * self.trade_size
            self.position_units = 0
            self.average_entry_price = None
            self.holding_bars = 0
            self.armed_watch = None
            return [
                Signal(
                    "sell",
                    bar.symbol,
                    bar.close_price,
                    volume,
                    f"chan_volume_fusion:TIME_EXIT:max_holding_bars={effective_max_holding}:volume={volume_state}",
                )
            ]
        return []

    def _update_volume_state(self, bar: Bar) -> str:
        previous_closes = list(self.volume_closes)
        previous_volumes = list(self.volume_volumes)
        self.volume_closes.append(bar.close_price)
        self.volume_volumes.append(bar.volume)
        return self._classify_volume_state(bar.close_price, bar.volume, previous_closes, previous_volumes)

    def _classify_volume_state(
        self,
        close_price: float,
        volume: float,
        previous_closes: list[float],
        previous_volumes: list[float],
    ) -> str:
        self._latest_volume_momentum = 0.0
        self._latest_continuation_trend_average = (
            mean(previous_closes[-self.continuation_trend_window :])
            if len(previous_closes) >= self.continuation_trend_window
            else None
        )
        if (
            len(previous_closes) < max(self.momentum_window, self.trend_window)
            or len(previous_volumes) < self.volume_window
        ):
            return "neutral"
        base = previous_closes[-self.momentum_window]
        if base <= 0:
            return "neutral"
        momentum = close_price / base - 1
        self._latest_volume_momentum = momentum
        trend_average = mean(previous_closes[-self.trend_window :])
        baseline_volume = mean(previous_volumes[-self.volume_window :])
        volume_ratio = volume / baseline_volume if baseline_volume > 0 else 0.0
        if (
            momentum >= self.min_momentum_pct
            and volume_ratio >= self.volume_multiplier
            and close_price > trend_average
        ):
            return "strong"
        if momentum <= self.weak_volume_momentum_pct or close_price < trend_average:
            return "weak"
        return "neutral"

    def _volume_allows_low_confidence(self, volume_state: str) -> bool:
        return not self.low_confidence_requires_volume or volume_state == "strong"

    def _apply_volume_boost(self, target_units: int, volume_state: str) -> int:
        if self.high_confidence_volume_boost and volume_state == "strong":
            return self._clamp_position_units(target_units + self.volume_boost_units)
        return self._clamp_position_units(target_units)

    def _apply_buy_volume_boost(self, signal, target_units: int, volume_state: str) -> int:
        if signal.action != "buy" or not self._is_boostable_buy_signal(signal):
            return self._clamp_position_units(target_units)
        return self._apply_volume_boost(target_units, volume_state)

    def _apply_risk_cap_after_volume_boost(self, signal, target_units: int) -> int:
        if signal.action == "buy" and self.position_cap_mode in {"risk", "trend_risk"}:
            if self._drawdown_cap_blocks_add(signal.price):
                return min(self.position_units, self._clamp_position_units(target_units))
        return self._clamp_position_units(target_units)

    def _is_boostable_buy_signal(self, signal) -> bool:
        return signal.kind in {
            "CHAN_STRUCT_BUY_T1_DIVERGENCE",
            "CHAN_STRUCT_BUY_CONFIRM",
            "CHAN_STRUCT_BUY_T3",
        }

    def _weak_volume_target_units(self, current_units: int) -> int:
        current_units = self._clamp_position_units(current_units)
        if self.weak_volume_exit_mode == "exit":
            return 0
        if self.weak_volume_exit_mode == "reduce":
            return max(0, current_units - 1)
        return current_units

    def _weak_volume_should_reduce(self, bar: Bar, result) -> bool:
        if not self.weak_volume_requires_trend_break:
            return True
        if self._latest_volume_momentum <= self.severe_weak_momentum_pct:
            return True
        trend_average = self._latest_continuation_trend_average
        if trend_average is not None and bar.close_price < trend_average:
            return True
        return self._chan_context_is_bearish(result)

    def _chan_context_is_bearish(self, result) -> bool:
        core_v2 = getattr(result, "core_v2", None)
        trends = list(getattr(core_v2, "trends", []) or [])
        for trend in reversed(trends):
            if getattr(trend, "level", None) in CHAN_CORE_V2_TREND_LEVELS:
                return getattr(trend, "trend_type", "") == "down"
        return False

    def _effective_max_holding_bars(self, volume_state: str) -> int:
        if self.max_holding_bars <= 0:
            return 0
        if volume_state == "strong":
            return self.max_holding_bars + self.strong_volume_extend_bars
        return self.max_holding_bars

    def _signal_reason(self, signal, volume_state: str, target_units: int, base_target_units: int) -> str:
        if signal.kind == "CHAN_STRUCT_BUY_T2" and volume_state == "strong":
            label = "CHAN_VOLUME_T2_BUY_VOLUME_CONFIRMED"
        elif signal.action == "buy" and target_units > base_target_units and volume_state == "strong":
            label = "CHAN_VOLUME_HIGH_CONFIDENCE_BOOST"
        elif signal.action == "sell":
            label = "CHAN_VOLUME_CHAN_SELL"
        else:
            label = signal.kind
        return f"chan_volume_fusion:{label}:{signal.kind}:volume={volume_state}:{signal.reason}"

    def _armed_reason(self, armed_watch: ArmedChanWatch, signal, volume_state: str) -> str:
        return (
            "chan_volume_fusion:ARMED_CONFIRM:"
            f"{armed_watch.kind}->{signal.kind}:volume={volume_state}:{signal.reason}"
        )

    def _clamp_position_units(self, units: int) -> int:
        return min(max(units, 0), self.max_units)


class VolumeConfirmedMomentumStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        momentum_window: int = 15,
        min_momentum_pct: float = 0.10,
        volume_window: int = 20,
        volume_multiplier: float = 1.1,
        trend_window: int = 60,
        max_holding_bars: int = 45,
        trailing_stop_pct: float = 0.18,
        trade_size: int = 100,
    ) -> None:
        self.symbol = symbol
        self.momentum_window = max(1, int(momentum_window))
        self.min_momentum_pct = float(min_momentum_pct)
        self.volume_window = max(1, int(volume_window))
        self.volume_multiplier = max(0.0, float(volume_multiplier))
        self.trend_window = max(1, int(trend_window))
        self.max_holding_bars = max(1, int(max_holding_bars))
        self.trailing_stop_pct = max(0.0, float(trailing_stop_pct))
        self.trade_size = max(1, int(trade_size))
        self.closes: deque[float] = deque(maxlen=max(self.momentum_window, self.trend_window) + 1)
        self.volumes: deque[float] = deque(maxlen=self.volume_window + 1)
        self.in_position = False
        self.holding_bars = 0
        self.highest_close_since_entry: float | None = None

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []

        previous_closes = list(self.closes)
        previous_volumes = list(self.volumes)
        self.closes.append(bar.close_price)
        self.volumes.append(bar.volume)

        if self.in_position:
            self.holding_bars += 1
            if self.highest_close_since_entry is None or bar.close_price > self.highest_close_since_entry:
                self.highest_close_since_entry = bar.close_price
            exit_reason = self._exit_reason(bar.close_price, previous_closes)
            if exit_reason:
                self.in_position = False
                self.holding_bars = 0
                self.highest_close_since_entry = None
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
        self.highest_close_since_entry = bar.close_price
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
        if (
            self.trailing_stop_pct > 0
            and self.highest_close_since_entry is not None
            and close_price <= self.highest_close_since_entry * (1 - self.trailing_stop_pct)
        ):
            return "trailing_stop_exit"
        if len(previous_closes) >= self.trend_window and close_price < mean(previous_closes[-self.trend_window :]):
            return "trend_exit"
        if self.holding_bars >= self.max_holding_bars:
            return "time_exit"
        return None


def _next_ema(previous: float | None, value: float, period: int) -> float:
    if previous is None:
        return value
    alpha = 2 / (period + 1)
    return value * alpha + previous * (1 - alpha)


def _true_range(bar: Bar, previous_close: float | None) -> float:
    high_low = bar.high_price - bar.low_price
    if previous_close is None:
        return high_low
    return max(high_low, abs(bar.high_price - previous_close), abs(bar.low_price - previous_close))


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


def _parse_chan_filter_values(raw_value: str, allowed_values: set[str], parameter_name: str) -> set[str] | None:
    value = raw_value.strip().lower()
    if value == "all":
        return None
    selected = {part.strip().lower() for part in value.split(",") if part.strip()}
    unknown = selected - allowed_values
    if not selected or unknown:
        allowed = ", ".join(["all", *sorted(allowed_values)])
        bad = ", ".join(sorted(unknown)) if unknown else raw_value
        raise ValueError(f"{parameter_name} contains unsupported values: {bad}; allowed values: {allowed}")
    return selected
