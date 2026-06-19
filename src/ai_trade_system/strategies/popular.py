from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import mean, pstdev

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


@dataclass(frozen=True)
class ArmedChanWatch:
    action: str
    kind: str
    score: float
    price: float
    reason: str
    trading_day: object
    bar_index: int


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
