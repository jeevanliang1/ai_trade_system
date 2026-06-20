# Chan Multi-Level Reversal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new built-in `ChanMultiLevelReversalStrategy` that uses daily Chan structure as the major setup, `30m` bars as required confirmation, and `15m` bars as execution/risk control.

**Architecture:** Keep the existing daily backtest loop and strategy interface. The new strategy subclasses the existing Chan structure strategy, loads lower-level CSVs through `read_bars_csv()`, advances independent `30m` and `15m` Chan analyzers only up to the current daily session close, and emits one daily-loop position delta without changing existing Chan defaults.

**Tech Stack:** Python strategy core, existing `Bar`/`Signal` dataclasses, `read_bars_csv()`, `ChanCoreV2Analyzer`, strategy registry metadata, pytest, React/FastAPI existing strategy surfaces, headless Chrome screenshot workflow.

---

## File Structure

- Modify `src/ai_trade_system/strategies/popular.py`: add constants, managed-path helper, lower-level context helper, and `ChanMultiLevelReversalStrategy`.
- Modify `src/ai_trade_system/strategy_registry.py`: register the new built-in strategy and add Chinese parameter guidance/options for new parameters.
- Create `tests/test_chan_multilevel_reversal_strategy.py`: focused TDD tests for validation, missing-minute policy, lower-level confirmation, 15m risk gating, and future-leak prevention.
- Modify `tests/test_builtin_popular_strategies.py`: add registry inclusion/import coverage if needed.
- Modify `tests/test_strategy_registry.py`: assert strategy metadata, default params, and guidance options.
- Create `docs/qa/2026-06-21-chan-multilevel-reversal-qa.md`: record RED/GREEN commands, full verification, benchmark coverage/results, and browser screenshots.
- Modify `docs/context/pending-features.md`: move this feature into implemented baseline and record the next strategy-development follow-up.

## Task 1: Add Failing Multi-Level Strategy Tests

**Files:**
- Create: `tests/test_chan_multilevel_reversal_strategy.py`
- Modify: none

- [ ] **Step 1: Create focused failing tests**

Create `tests/test_chan_multilevel_reversal_strategy.py` with this full initial test module:

```python
from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from ai_trade_system.data import write_bars_csv
from ai_trade_system.market import Bar
from ai_trade_system.research.models import ResearchSignal
from ai_trade_system.strategies import popular as popular_strategies
from ai_trade_system.strategies.popular import ChanMultiLevelReversalStrategy


def make_daily_bar(index: int, close: float = 10.0) -> Bar:
    day = date(2024, 1, 1) + timedelta(days=index)
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=day,
        open_price=close,
        high_price=close + 0.4,
        low_price=close - 0.4,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
        timeframe="daily",
    )


def make_minute_bar(index: int, timeframe: str, hour: int, minute: int, close: float = 10.0) -> Bar:
    day = date(2024, 1, 1) + timedelta(days=index)
    stamp = datetime(day.year, day.month, day.day, hour, minute)
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=day,
        timestamp=stamp,
        timeframe=timeframe,
        open_price=close,
        high_price=close + 0.2,
        low_price=close - 0.2,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
    )


def make_signal(day: date, kind: str, action: str, score: float, point_type: str, level: str = "segment") -> ResearchSignal:
    return ResearchSignal(
        trading_day=day,
        symbol="000001",
        exchange="SZSE",
        kind=kind,
        action=action,
        price=10.0,
        strength=min(0.95, abs(score) / 100),
        score=score,
        title=kind,
        reason=f"test {kind}",
        tags=("chan", "structure", point_type),
        metadata={"point_type": point_type, "level": level},
    )


def patch_multilevel_analyzers(monkeypatch, scripts: dict[str, list[ResearchSignal]], seen: list[tuple[str, object]]) -> None:
    class FakeAnalyzer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.latest_by_timeframe: dict[str, list[ResearchSignal]] = {}

        def update_bar(self, bar):
            timeframe = getattr(bar, "timeframe", "daily")
            seen.append((timeframe, bar.timestamp or bar.trading_day))
            signals = scripts.get(timeframe, [])
            trends = [SimpleNamespace(level="stroke", trend_type=scripts.get(f"{timeframe}:trend", ["transition"])[0])]
            return SimpleNamespace(signals=signals, core_v2=SimpleNamespace(trends=trends))

    monkeypatch.setattr(popular_strategies, "ChanCoreV2Analyzer", FakeAnalyzer, raising=False)


def test_chan_multilevel_strategy_rejects_invalid_configuration(tmp_path):
    with pytest.raises(ValueError, match="lower_level_policy"):
        ChanMultiLevelReversalStrategy("000001", lower_level_policy="bad")
    with pytest.raises(ValueError, match="minute_missing_policy"):
        ChanMultiLevelReversalStrategy("000001", minute_missing_policy="bad")
    with pytest.raises(ValueError, match="minute_sell_mode"):
        ChanMultiLevelReversalStrategy("000001", minute_sell_mode="bad")
    with pytest.raises(ValueError, match="min_confirm_score"):
        ChanMultiLevelReversalStrategy("000001", min_confirm_score=-1)
    with pytest.raises(ValueError, match="confirm_timeframe"):
        ChanMultiLevelReversalStrategy("000001", confirm_timeframe="5m")


def test_chan_multilevel_skip_entry_blocks_daily_buy_when_minute_data_missing(monkeypatch):
    day = date(2024, 1, 1)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {"daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")]},
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        confirm_csv_path="/tmp/missing-30m.csv",
        risk_csv_path="/tmp/missing-15m.csv",
        minute_missing_policy="skip_entry",
    )

    assert strategy.on_bar(make_daily_bar(0)) == []


def test_chan_multilevel_daily_only_fallback_preserves_daily_buy_when_configured(monkeypatch):
    day = date(2024, 1, 1)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {"daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")]},
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        confirm_csv_path="/tmp/missing-30m.csv",
        risk_csv_path="/tmp/missing-15m.csv",
        minute_missing_policy="daily_only",
    )

    signals = strategy.on_bar(make_daily_bar(0))

    assert [signal.action for signal in signals] == ["buy"]
    assert "DAILY_FALLBACK" in signals[0].reason


def test_chan_multilevel_daily_buy_requires_30m_confirmation(monkeypatch, tmp_path):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm.csv"
    risk_path = tmp_path / "risk.csv"
    write_bars_csv([make_minute_bar(0, "30m", 10, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "15m", 10, 15)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "30m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
            "15m": [],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
        lower_level_policy="confirm_only",
    )

    signals = strategy.on_bar(make_daily_bar(0))

    assert [signal.action for signal in signals] == ["buy"]
    assert "CONFIRM_30M" in signals[0].reason


def test_chan_multilevel_bearish_15m_blocks_confirmed_buy(monkeypatch, tmp_path):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm.csv"
    risk_path = tmp_path / "risk.csv"
    write_bars_csv([make_minute_bar(0, "30m", 10, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "15m", 10, 15)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "30m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
            "15m": [make_signal(day, "CHAN_STRUCT_SELL_T3", "sell", -35, "third-sell")],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        min_risk_score=20,
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
    )

    assert strategy.on_bar(make_daily_bar(0)) == []


def test_chan_multilevel_15m_risk_signal_reduces_or_exits_existing_position(monkeypatch, tmp_path):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm.csv"
    risk_path = tmp_path / "risk.csv"
    write_bars_csv([make_minute_bar(0, "30m", 10, 0), make_minute_bar(1, "30m", 10, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "15m", 10, 15), make_minute_bar(1, "15m", 10, 15)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "30m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
            "15m": [make_signal(day + timedelta(days=1), "CHAN_STRUCT_SELL_T3", "sell", -35, "third-sell")],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        min_risk_score=20,
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
        minute_sell_mode="exit",
    )

    strategy.on_bar(make_daily_bar(0))
    signals = strategy.on_bar(make_daily_bar(1))

    assert [signal.action for signal in signals] == ["sell"]
    assert "RISK_15M" in signals[0].reason


def test_chan_multilevel_does_not_consume_future_minute_bars(monkeypatch, tmp_path):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm.csv"
    risk_path = tmp_path / "risk.csv"
    write_bars_csv([make_minute_bar(0, "30m", 10, 0), make_minute_bar(1, "30m", 10, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "15m", 10, 15), make_minute_bar(1, "15m", 10, 15)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "30m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
        lower_level_policy="confirm_only",
    )

    strategy.on_bar(make_daily_bar(0))

    assert ("30m", datetime(2024, 1, 1, 10, 0)) in seen
    assert ("30m", datetime(2024, 1, 2, 10, 0)) not in seen
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected: FAIL during import with `ImportError` or `AttributeError` showing `ChanMultiLevelReversalStrategy` does not exist.

- [ ] **Step 3: Commit RED tests**

```bash
git add tests/test_chan_multilevel_reversal_strategy.py
git commit -m "test: specify chan multilevel reversal behavior"
```

## Task 2: Implement Lower-Level Context And Strategy Core

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`
- Test: `tests/test_chan_multilevel_reversal_strategy.py`

- [ ] **Step 1: Add imports and constants**

In `src/ai_trade_system/strategies/popular.py`, extend imports and add constants near the existing Chan constants:

```python
from datetime import datetime, time
from pathlib import Path

from ai_trade_system.data import read_bars_csv, normalize_timeframe
```

```python
CHAN_MULTI_LEVEL_POLICIES = {"confirm_then_risk", "confirm_only"}
CHAN_MINUTE_MISSING_POLICIES = {"skip_entry", "daily_only"}
CHAN_MINUTE_SELL_MODES = {"reduce", "exit"}
CHAN_CONFIRM_TIMEFRAMES = {"30m"}
CHAN_RISK_TIMEFRAMES = {"15m"}
CHAN_SESSION_CLOSE = time(15, 0)
```

- [ ] **Step 2: Add lower-level helpers**

Add these helpers above `ChanStructureStrategy`:

```python
@dataclass
class ChanLowerLevelContext:
    timeframe: str
    path: Path
    analyzer: object
    bars: list[Bar]
    cursor: int = 0
    latest_result: object | None = None
    missing: bool = False

    @classmethod
    def from_csv(
        cls,
        *,
        symbol: str,
        exchange: str,
        timeframe: str,
        path: str | Path,
        min_stroke_bars: int,
        min_rebound_pct: float,
        lookback: int,
    ) -> "ChanLowerLevelContext":
        resolved = Path(path)
        analyzer = ChanCoreV2Analyzer(min_stroke_bars=min_stroke_bars, min_rebound_pct=min_rebound_pct, lookback=lookback)
        try:
            bars = [
                bar
                for bar in read_bars_csv(resolved)
                if bar.symbol == symbol and bar.exchange == exchange and normalize_timeframe(bar.timeframe) == timeframe
            ]
        except FileNotFoundError:
            return cls(timeframe=timeframe, path=resolved, analyzer=analyzer, bars=[], missing=True)
        bars.sort(key=_bar_datetime)
        return cls(timeframe=timeframe, path=resolved, analyzer=analyzer, bars=bars)

    def update_until(self, cutoff: datetime):
        while self.cursor < len(self.bars) and _bar_datetime(self.bars[self.cursor]) <= cutoff:
            self.latest_result = self.analyzer.update_bar(self.bars[self.cursor])
            self.cursor += 1
        return self.latest_result

    @property
    def available(self) -> bool:
        return not self.missing and bool(self.bars)


def _managed_level_csv_path(symbol: str, exchange: str, timeframe: str, adjust: str) -> str:
    clean_symbol = str(symbol).strip()
    clean_exchange = str(exchange).strip().upper()
    clean_timeframe = normalize_timeframe(timeframe)
    clean_adjust = str(adjust or "qfq").strip().lower()
    return f"data/market/a_share/{clean_exchange}/{clean_symbol}/{clean_symbol}_{clean_exchange}_{clean_timeframe}_{clean_adjust}_latest.csv"


def _daily_session_close(bar: Bar) -> datetime:
    if bar.timestamp is not None:
        return bar.timestamp
    return datetime.combine(bar.trading_day, CHAN_SESSION_CLOSE)


def _bar_datetime(bar: Bar) -> datetime:
    return bar.timestamp or _daily_session_close(bar)
```

- [ ] **Step 3: Add strategy constructor and validation**

Add `ChanMultiLevelReversalStrategy` after `ChanVolumeFusionStrategy` or before it if shared logic is easier. Use this constructor shape:

```python
class ChanMultiLevelReversalStrategy(ChanStructureStrategy):
    def __init__(
        self,
        symbol: str,
        exchange: str = "SZSE",
        adjust: str = "qfq",
        confirm_timeframe: str = "30m",
        risk_timeframe: str = "15m",
        confirm_csv_path: str = "",
        risk_csv_path: str = "",
        lower_level_policy: str = "confirm_then_risk",
        minute_missing_policy: str = "skip_entry",
        minute_sell_mode: str = "reduce",
        min_daily_score: float = 28.0,
        min_confirm_score: float = 28.0,
        min_risk_score: float = 24.0,
        min_bars: int = 60,
        lookback: int = 160,
        min_stroke_bars: int = 5,
        min_rebound_pct: float = 0.03,
        max_holding_bars: int = 15,
        low_confidence_units: int = 1,
        divergence_confirm_units: int = 2,
        high_confidence_units: int = 3,
        sell_confirm_units: int = 1,
        trade_size: int = 100,
    ) -> None:
        confirm_timeframe = normalize_timeframe(confirm_timeframe)
        risk_timeframe = normalize_timeframe(risk_timeframe)
        if confirm_timeframe not in CHAN_CONFIRM_TIMEFRAMES:
            raise ValueError("confirm_timeframe must be 30m")
        if risk_timeframe not in CHAN_RISK_TIMEFRAMES:
            raise ValueError("risk_timeframe must be 15m")
        if lower_level_policy not in CHAN_MULTI_LEVEL_POLICIES:
            raise ValueError("lower_level_policy must be one of: confirm_then_risk, confirm_only")
        if minute_missing_policy not in CHAN_MINUTE_MISSING_POLICIES:
            raise ValueError("minute_missing_policy must be one of: skip_entry, daily_only")
        if minute_sell_mode not in CHAN_MINUTE_SELL_MODES:
            raise ValueError("minute_sell_mode must be one of: reduce, exit")
        if min_daily_score < 0:
            raise ValueError("min_daily_score must be non-negative")
        if min_confirm_score < 0:
            raise ValueError("min_confirm_score must be non-negative")
        if min_risk_score < 0:
            raise ValueError("min_risk_score must be non-negative")

        self.exchange = exchange.upper()
        self.adjust = adjust
        self.confirm_timeframe = confirm_timeframe
        self.risk_timeframe = risk_timeframe
        self.lower_level_policy = lower_level_policy
        self.minute_missing_policy = minute_missing_policy
        self.minute_sell_mode = minute_sell_mode
        self.min_daily_score = float(min_daily_score)
        self.min_confirm_score = float(min_confirm_score)
        self.min_risk_score = float(min_risk_score)
        self.confirm_csv_path = confirm_csv_path or _managed_level_csv_path(symbol, self.exchange, confirm_timeframe, adjust)
        self.risk_csv_path = risk_csv_path or _managed_level_csv_path(symbol, self.exchange, risk_timeframe, adjust)

        super().__init__(
            symbol=symbol,
            min_bars=min_bars,
            lookback=lookback,
            min_stroke_bars=min_stroke_bars,
            min_rebound_pct=min_rebound_pct,
            min_signal_score=min_daily_score,
            signal_mode="all",
            allowed_point_types="all",
            allowed_levels="all",
            max_holding_bars=max_holding_bars,
            watch_confirm_bars=20,
            low_confidence_gate="divergence_or_trend",
            low_confidence_min_score=32.0,
            range_max_units=1,
            position_cap_mode="risk",
            trend_cap_units=2,
            risk_drawdown_cap_pct=8.0,
            low_confidence_units=low_confidence_units,
            divergence_confirm_units=divergence_confirm_units,
            high_confidence_units=high_confidence_units,
            sell_confirm_units=sell_confirm_units,
            trade_size=trade_size,
        )
        self.confirm_context = ChanLowerLevelContext.from_csv(
            symbol=symbol,
            exchange=self.exchange,
            timeframe=confirm_timeframe,
            path=self.confirm_csv_path,
            min_stroke_bars=min_stroke_bars,
            min_rebound_pct=min_rebound_pct,
            lookback=lookback,
        )
        self.risk_context = ChanLowerLevelContext.from_csv(
            symbol=symbol,
            exchange=self.exchange,
            timeframe=risk_timeframe,
            path=self.risk_csv_path,
            min_stroke_bars=min_stroke_bars,
            min_rebound_pct=min_rebound_pct,
            lookback=lookback,
        )
```

- [ ] **Step 4: Run tests to confirm constructor-related tests progress**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py::test_chan_multilevel_strategy_rejects_invalid_configuration -q
```

Expected: PASS for constructor validation, while the rest of the new test file still fails because `on_bar()` semantics are not implemented.

- [ ] **Step 5: Implement `on_bar()` and signal selection**

Override `on_bar()` in `ChanMultiLevelReversalStrategy` with these methods in the same class:

```python
    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []
        self.bar_index += 1
        self.bars.append(bar)
        daily_result = self.chan_analyzer.update_bar(bar)
        cutoff = _daily_session_close(bar)
        confirm_result = self.confirm_context.update_until(cutoff)
        risk_result = self.risk_context.update_until(cutoff) if self.lower_level_policy == "confirm_then_risk" else None
        if self.in_position:
            self.holding_bars += 1
        if len(self.bars) < self.min_bars:
            return []

        risk_signal = self._latest_lower_signal(risk_result, "sell", self.min_risk_score)
        if self.in_position and risk_signal is not None:
            target_units = 0 if self.minute_sell_mode == "exit" else max(0, self.position_units - self.low_confidence_units)
            if self._can_emit_target_units("sell", target_units):
                return self._emit_position_delta(
                    target_units,
                    bar,
                    bar.close_price,
                    f"chan_multilevel:RISK_15M:{risk_signal.kind}:{risk_signal.reason}",
                )

        daily_sell = self._latest_daily_signal(daily_result, bar, "sell")
        if self.in_position and daily_sell is not None:
            target_units = self._target_units_for_signal(daily_sell)
            if self._can_emit_target_units("sell", target_units):
                return self._emit_position_delta(
                    target_units,
                    bar,
                    daily_sell.price,
                    f"chan_multilevel:DAILY_SELL:{daily_sell.kind}:{daily_sell.reason}",
                )

        confirm_sell = self._latest_lower_signal(confirm_result, "sell", self.min_confirm_score)
        if self.in_position and confirm_sell is not None:
            target_units = self.sell_confirm_units if self.minute_sell_mode == "reduce" else 0
            if self._can_emit_target_units("sell", target_units):
                return self._emit_position_delta(
                    target_units,
                    bar,
                    bar.close_price,
                    f"chan_multilevel:CONFIRM_30M_SELL:{confirm_sell.kind}:{confirm_sell.reason}",
                )

        daily_buy = self._latest_daily_signal(daily_result, bar, "buy")
        if daily_buy is None and not self._daily_trend_allows_buy(daily_result):
            return self._time_exit_if_needed(bar)

        confirm_buy = self._latest_lower_signal(confirm_result, "buy", self.min_confirm_score)
        if confirm_buy is None:
            if self.minute_missing_policy == "daily_only" and daily_buy is not None:
                target_units = self._target_units_for_signal(daily_buy)
                if self._can_emit_target_units("buy", target_units):
                    return self._emit_position_delta(
                        target_units,
                        bar,
                        daily_buy.price,
                        f"chan_multilevel:DAILY_FALLBACK:{daily_buy.kind}:{daily_buy.reason}",
                    )
            return self._time_exit_if_needed(bar)

        if risk_signal is not None:
            return self._time_exit_if_needed(bar)

        buy_source = daily_buy or confirm_buy
        target_units = self._target_units_for_signal(buy_source)
        target_units = self._cap_target_units(buy_source, daily_result, target_units)
        if self._can_emit_target_units("buy", target_units):
            return self._emit_position_delta(
                target_units,
                bar,
                buy_source.price,
                f"chan_multilevel:CONFIRM_30M:{confirm_buy.kind}:{confirm_buy.reason}",
            )
        return self._time_exit_if_needed(bar)

    def _latest_daily_signal(self, result, bar: Bar, action: str):
        candidates = [
            signal
            for signal in getattr(result, "signals", [])
            if signal.trading_day == bar.trading_day
            and signal.action == action
            and abs(signal.score) >= self.min_daily_score
            and self._signal_filters_allow(signal)
        ]
        candidates.sort(key=lambda signal: abs(signal.score), reverse=True)
        return candidates[0] if candidates else None

    def _latest_lower_signal(self, result, action: str, min_score: float):
        if result is None:
            return None
        candidates = [
            signal
            for signal in getattr(result, "signals", [])
            if signal.action == action and abs(signal.score) >= min_score and self._signal_filters_allow(signal)
        ]
        candidates.sort(key=lambda signal: (signal.trading_day, abs(signal.score)), reverse=True)
        return candidates[0] if candidates else None

    def _daily_trend_allows_buy(self, result) -> bool:
        core_v2 = getattr(result, "core_v2", None)
        trends = list(getattr(core_v2, "trends", []) or [])
        if not trends:
            return False
        latest = trends[-1]
        return getattr(latest, "trend_type", "") in {"up", "transition", "range"}

    def _time_exit_if_needed(self, bar: Bar) -> list[Signal]:
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
                    f"chan_multilevel:TIME_EXIT:max_holding_bars={self.max_holding_bars}",
                )
            ]
        return []
```

- [ ] **Step 6: Run new strategy tests to verify GREEN**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected: all tests in `tests/test_chan_multilevel_reversal_strategy.py` pass.

- [ ] **Step 7: Commit strategy core**

```bash
git add src/ai_trade_system/strategies/popular.py tests/test_chan_multilevel_reversal_strategy.py
git commit -m "feat: add chan multilevel reversal strategy core"
```

## Task 3: Register Strategy And Parameter Guidance

**Files:**
- Modify: `src/ai_trade_system/strategy_registry.py`
- Modify: `tests/test_strategy_registry.py`
- Optionally modify: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Add failing registry test**

Append to `tests/test_strategy_registry.py`:

```python
def test_chan_multilevel_reversal_strategy_is_registered_with_guidance():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    spec = next(strategy for strategy in specs if strategy.class_name == "ChanMultiLevelReversalStrategy")

    assert spec.display_name == "缠论多级别反转"
    assert "30m" in spec.description
    assert "15m" in spec.description

    parameters = {parameter.name: parameter for parameter in inspect_strategy_parameters(spec)}
    assert parameters["exchange"].display_name == "交易所"
    assert parameters["confirm_timeframe"].display_name == "确认级别"
    assert parameters["confirm_timeframe"].options == ("30m",)
    assert parameters["risk_timeframe"].display_name == "风控级别"
    assert parameters["risk_timeframe"].options == ("15m",)
    assert parameters["lower_level_policy"].options == ("confirm_then_risk", "confirm_only")
    assert parameters["minute_missing_policy"].options == ("skip_entry", "daily_only")
    assert parameters["minute_sell_mode"].options == ("reduce", "exit")
    assert "15m" in parameters["risk_csv_path"].description
    assert "不能单独开仓" in parameters["risk_timeframe"].description
```

- [ ] **Step 2: Run registry test to verify RED**

Run:

```bash
python -m pytest tests/test_strategy_registry.py::test_chan_multilevel_reversal_strategy_is_registered_with_guidance -q
```

Expected: FAIL because the strategy is not registered or guidance is missing.

- [ ] **Step 3: Register the built-in strategy**

Add this `StrategySpec` to `BUILTIN_STRATEGIES` near the other Chan strategies in `src/ai_trade_system/strategy_registry.py`:

```python
    StrategySpec(
        id="builtin:popular:ChanMultiLevelReversalStrategy",
        name="ChanMultiLevelReversalStrategy",
        class_name="ChanMultiLevelReversalStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
        display_name="缠论多级别反转",
        description="以日线缠论结构为主级别，使用 30m 确认反转，使用 15m 做执行过滤和提前风控；15m 信号不能单独开仓。",
    ),
```

- [ ] **Step 4: Add parameter guidance**

Add these entries to `PARAMETER_GUIDANCE` in `src/ai_trade_system/strategy_registry.py`:

```python
    "exchange": ParameterGuidance(
        display_name="交易所",
        description="用于推导托管分钟行情 CSV 路径；SSE 对应沪市，SZSE 对应深市，BSE 对应北交所。",
        increase_effect="该参数不是数值大小；切换交易所会改变默认分钟数据路径。",
        decrease_effect="该参数不是数值大小；需要和当前股票代码实际交易所一致。",
        options=("SZSE", "SSE", "BSE"),
    ),
    "adjust": ParameterGuidance(
        display_name="复权方式",
        description="用于推导托管行情路径，默认 qfq 与现有固定 benchmark 口径一致。",
        increase_effect="该参数不是数值大小；切换复权方式会改变读取的本地行情文件。",
        decrease_effect="该参数不是数值大小；比较策略时应固定同一复权口径。",
        options=("qfq", "hfq", ""),
    ),
    "confirm_timeframe": ParameterGuidance(
        display_name="确认级别",
        description="多级别缠论的主确认周期；第一版固定为 30m，对应日线的下一级趋势确认。",
        increase_effect="该参数不是数值大小；当前只开放 30m 以保持验证口径稳定。",
        decrease_effect="该参数不是数值大小；后续可扩展其他确认级别但需要重新 benchmark。",
        options=("30m",),
    ),
    "risk_timeframe": ParameterGuidance(
        display_name="风控级别",
        description="多级别缠论的执行和提前风控周期；第一版固定为 15m，15m 信号不能单独开仓。",
        increase_effect="该参数不是数值大小；当前只开放 15m 作为 30m 确认后的细级别风控。",
        decrease_effect="该参数不是数值大小；关闭细级别风控请使用 lower_level_policy=confirm_only。",
        options=("15m",),
    ),
    "confirm_csv_path": ParameterGuidance(
        display_name="30m确认数据路径",
        description="30m 本地 CSV 路径；留空时按 data/market/a_share/{exchange}/{symbol}/{symbol}_{exchange}_30m_qfq_latest.csv 推导。",
        increase_effect="该参数不是数值大小；改路径会改变确认级别使用的数据源。",
        decrease_effect="该参数不是数值大小；留空会使用托管行情默认路径。",
    ),
    "risk_csv_path": ParameterGuidance(
        display_name="15m风控数据路径",
        description="15m 本地 CSV 路径；留空时按托管行情默认路径推导。15m 只做执行过滤或提前风控，不能单独开仓。",
        increase_effect="该参数不是数值大小；改路径会改变风控级别使用的数据源。",
        decrease_effect="该参数不是数值大小；留空会使用托管行情默认路径。",
    ),
    "lower_level_policy": ParameterGuidance(
        display_name="下级别策略",
        description="confirm_then_risk 使用 30m 确认和 15m 风控；confirm_only 只使用 30m 确认。",
        increase_effect="该参数不是数值大小；confirm_then_risk 更防守，confirm_only 更少过滤。",
        decrease_effect="该参数不是数值大小；切换会改变 15m 是否参与交易控制。",
        options=("confirm_then_risk", "confirm_only"),
    ),
    "minute_missing_policy": ParameterGuidance(
        display_name="分钟缺失处理",
        description="分钟 CSV 缺失时的处理方式：skip_entry 阻止新开仓，daily_only 允许退回日线信号。",
        increase_effect="该参数不是数值大小；skip_entry 更严格，daily_only 更接近日线原策略。",
        decrease_effect="该参数不是数值大小；比较多级别效果时应优先使用 skip_entry。",
        options=("skip_entry", "daily_only"),
    ),
    "minute_sell_mode": ParameterGuidance(
        display_name="分钟卖出方式",
        description="下级别出现卖出或转弱信号时的处理方式：reduce 减一档，exit 清仓。",
        increase_effect="该参数不是数值大小；exit 更防守，reduce 保留部分仓位。",
        decrease_effect="该参数不是数值大小；切换会改变 30m/15m 风控的卖出力度。",
        options=("reduce", "exit"),
    ),
    "min_daily_score": ParameterGuidance(
        display_name="日线最低信号分",
        description="日线结构信号达到该分数后才允许作为多级别反转背景。",
        increase_effect="调大后日线背景更严格，交易更少。",
        decrease_effect="调小后日线背景更宽松，更依赖 30m 确认过滤。",
    ),
    "min_confirm_score": ParameterGuidance(
        display_name="30m确认最低分",
        description="30m 确认信号达到该分数后才允许确认日线反转。",
        increase_effect="调大后 30m 确认更严格，交易更少。",
        decrease_effect="调小后 30m 更容易确认，但可能引入噪音。",
    ),
    "min_risk_score": ParameterGuidance(
        display_name="15m风控最低分",
        description="15m 风控信号达到该分数后才会阻止入场、减仓或退出。",
        increase_effect="调大后 15m 风控更克制，减少过度过滤。",
        decrease_effect="调小后 15m 更敏感，防守更快但可能卖飞。",
    ),
```

- [ ] **Step 5: Run registry tests to verify GREEN**

Run:

```bash
python -m pytest tests/test_strategy_registry.py::test_chan_multilevel_reversal_strategy_is_registered_with_guidance -q
```

Expected: PASS.

- [ ] **Step 6: Add built-in discovery coverage if current test expects explicit strategy list**

If `tests/test_builtin_popular_strategies.py::test_registry_includes_popular_builtin_strategies` does not include the new class, add `"ChanMultiLevelReversalStrategy"` to the expected subset and run:

```bash
python -m pytest tests/test_builtin_popular_strategies.py::test_registry_includes_popular_builtin_strategies -q
```

Expected: PASS.

- [ ] **Step 7: Commit registry integration**

```bash
git add src/ai_trade_system/strategy_registry.py tests/test_strategy_registry.py tests/test_builtin_popular_strategies.py
git commit -m "feat: register chan multilevel reversal strategy"
```

## Task 4: Run Targeted And Full Verification

**Files:**
- No source changes required.

- [ ] **Step 1: Run targeted backend tests**

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py tests/test_strategy_registry.py::test_chan_multilevel_reversal_strategy_is_registered_with_guidance tests/test_builtin_popular_strategies.py::test_registry_includes_popular_builtin_strategies -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full Python suite with local LLM isolated**

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
```

Expected: all Python tests pass.

- [ ] **Step 3: Run frontend tests and build**

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

Expected: all frontend tests pass and production build succeeds.

## Task 5: Benchmark Daily, Daily+30m, And Daily+30m+15m

**Files:**
- Create: `docs/qa/2026-06-21-chan-multilevel-reversal-qa.md`
- Modify: `docs/context/pending-features.md`

- [ ] **Step 1: Check fixture coverage**

Run this command to inspect daily, `30m`, and `15m` fixture availability:

```bash
python - <<'PY'
from pathlib import Path
from ai_trade_system.data import read_bars_csv

fixtures = [
    ("688981", "SSE"),
    ("000858", "SZSE"),
    ("601318", "SSE"),
    ("600901", "SSE"),
    ("600989", "SSE"),
    ("603986", "SSE"),
]
for code, exchange in fixtures:
    for timeframe in ("daily", "30m", "15m"):
        path = Path(f"data/market/a_share/{exchange}/{code}/{code}_{exchange}_{timeframe}_qfq_latest.csv")
        if not path.exists():
            print(code, exchange, timeframe, "missing", path)
            continue
        bars = read_bars_csv(path)
        start = bars[0].timestamp or bars[0].trading_day if bars else None
        end = bars[-1].timestamp or bars[-1].trading_day if bars else None
        print(code, exchange, timeframe, len(bars), start, end, path)
PY
```

Expected: print coverage rows; missing minute fixtures are allowed but must be recorded.

- [ ] **Step 2: Download missing 30m/15m fixtures when practical**

For each fixed symbol with missing minute fixtures, run targeted data updates. Use the local qfq convention and record failures rather than hiding them:

```bash
python - <<'PY'
from ai_trade_system.data_manager import StockTarget, update_stock_data

fixtures = [
    ("688981", "中芯国际", "SSE"),
    ("000858", "五粮液", "SZSE"),
    ("601318", "中国平安", "SSE"),
    ("600901", "江苏金租", "SSE"),
    ("600989", "宝丰能源", "SSE"),
    ("603986", "兆易创新", "SSE"),
]
for code, name, exchange in fixtures:
    for timeframe in ("30m", "15m"):
        result = update_stock_data(
            StockTarget(code=code, name=name, exchange=exchange),
            start_date="20230619",
            end_date="20260619",
            adjust="qfq",
            timeframe=timeframe,
            if_stale=False,
        )
        print(code, exchange, timeframe, result.status, result.rows, result.latest_path, result.error or "")
PY
```

Expected: rows are downloaded where AKShare provides them; upstream history limitations are documented as partial coverage or failures.

- [ ] **Step 3: Run benchmark comparison**

Run:

```bash
python - <<'PY'
from pathlib import Path

from ai_trade_system.analytics import calculate_backtest_metrics
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import read_bars_csv
from ai_trade_system.strategies.popular import ChanStructureStrategy, ChanVolumeFusionStrategy, ChanMultiLevelReversalStrategy

fixtures = [
    ("688981", "SSE"),
    ("000858", "SZSE"),
    ("601318", "SSE"),
    ("600901", "SSE"),
    ("600989", "SSE"),
    ("603986", "SSE"),
]
strategies = [
    ("daily_structure", lambda code, exchange: ChanStructureStrategy(code)),
    ("daily_volume_fusion", lambda code, exchange: ChanVolumeFusionStrategy(code)),
    (
        "daily_30m",
        lambda code, exchange: ChanMultiLevelReversalStrategy(
            code,
            exchange=exchange,
            lower_level_policy="confirm_only",
            minute_missing_policy="skip_entry",
        ),
    ),
    (
        "daily_30m_15m",
        lambda code, exchange: ChanMultiLevelReversalStrategy(
            code,
            exchange=exchange,
            lower_level_policy="confirm_then_risk",
            minute_missing_policy="skip_entry",
        ),
    ),
]
for code, exchange in fixtures:
    daily_path = Path(f"data/market/a_share/{exchange}/{code}/{code}_{exchange}_daily_qfq_latest.csv")
    if not daily_path.exists():
        print(code, exchange, "missing daily fixture")
        continue
    bars = read_bars_csv(daily_path)
    for label, factory in strategies:
        strategy = factory(code, exchange)
        result = run_backtest(bars, strategy, BacktestConfig())
        metrics = calculate_backtest_metrics(result.equity_curve, result.trades, 100_000)
        print(
            "\t".join(
                [
                    code,
                    exchange,
                    label,
                    str(len(bars)),
                    str(bars[0].trading_day),
                    str(bars[-1].trading_day),
                    f"{result.final_equity:.2f}",
                    f"{metrics.total_return_pct:.4f}",
                    f"{metrics.benchmark_return_pct:.4f}",
                    f"{metrics.excess_return_pct:.4f}",
                    f"{metrics.max_drawdown_pct:.4f}",
                    str(metrics.trade_count),
                    f"{metrics.win_rate_pct:.4f}",
                    f"{metrics.profit_factor:.4f}",
                ]
            )
        )
PY
```

Expected: benchmark rows for each strategy/symbol combination where required data exists. Rows with zero trades are valid evidence.

- [ ] **Step 4: Create QA markdown**

Create `docs/qa/2026-06-21-chan-multilevel-reversal-qa.md` with:

```markdown
# Chan Multi-Level Reversal QA

## Scope

Implemented `ChanMultiLevelReversalStrategy`: daily Chan structure, 30m confirmation, and optional 15m risk timing.

## Verification

- RED tests: `python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q` failed before implementation because `ChanMultiLevelReversalStrategy` was missing.
- Targeted tests: record final command and pass count.
- Full backend: record `AI_TRADE_LLM_PROVIDER=mock python -m pytest -q`.
- Frontend: record `npm --prefix frontend test` and `npm --prefix frontend run build`.

## Minute Fixture Coverage

Record daily, 30m, and 15m rows/start/end/path for each fixed symbol. Mark missing or partial AKShare minute coverage explicitly.

## Benchmark Results

Include a table with symbol, strategy, rows, final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor.

## Interpretation

State whether `daily + 30m` and `daily + 30m + 15m` improved false-reversal behavior, returns, drawdown, or trade count compared with daily-only Chan structure and Chan-volume fusion.

## Screenshots

Record desktop and mobile screenshot paths showing the new strategy and parameters in the React Strategy Workshop.
```

- [ ] **Step 5: Update pending feature list**

In `docs/context/pending-features.md`:

- Move `Chan minute-level validation` from `Pending / Strategy Development` into `Already Implemented Baseline` with a concise bullet.
- Set the next recommended feature to the most concrete follow-up discovered from benchmark results, such as parameter tuning, broader minute fixture maintenance, or exact intraday execution modeling.

- [ ] **Step 6: Commit QA and pending list**

```bash
git add docs/qa/2026-06-21-chan-multilevel-reversal-qa.md docs/context/pending-features.md
git commit -m "docs: record chan multilevel reversal QA"
```

## Task 6: Browser Screenshot Acceptance

**Files:**
- Modify: `docs/qa/2026-06-21-chan-multilevel-reversal-qa.md`
- Create screenshots under: `docs/qa/screenshots/`

- [ ] **Step 1: Start the React + FastAPI platform**

```bash
./scripts/run_app.sh
```

Expected: FastAPI listens on `127.0.0.1:8000` and Vite listens on `127.0.0.1:5173`.

- [ ] **Step 2: Capture default desktop/mobile screenshots**

```bash
node scripts/capture_app_screenshots.mjs --url http://localhost:5173 --out-dir docs/qa/screenshots --prefix 2026-06-21-chan-multilevel-reversal
```

Expected:

- `docs/qa/screenshots/2026-06-21-chan-multilevel-reversal_desktop_1440.png`
- `docs/qa/screenshots/2026-06-21-chan-multilevel-reversal_mobile_390.png`

- [ ] **Step 3: Capture Strategy Workshop strategy-selection proof**

Use headless Chrome/CDP or the Browser plugin if available. The interaction path is:

```text
http://localhost:5173 -> 策略工坊 -> select 缠论多级别反转 -> verify parameters include 确认级别=30m and 风控级别=15m -> screenshot
```

Expected screenshots:

- `docs/qa/screenshots/2026-06-21-chan-multilevel-reversal_strategy_desktop_1440.png`
- `docs/qa/screenshots/2026-06-21-chan-multilevel-reversal_strategy_mobile_390.png`

- [ ] **Step 4: Update QA screenshot section**

Append the screenshot paths and the browser validation result to `docs/qa/2026-06-21-chan-multilevel-reversal-qa.md`.

- [ ] **Step 5: Stop the dev server**

Send Ctrl+C to the running `./scripts/run_app.sh` session. Confirm ports are no longer listening:

```bash
lsof -nP -iTCP:5173 -sTCP:LISTEN || true
lsof -nP -iTCP:8000 -sTCP:LISTEN || true
```

Expected: no listener output for both ports.

- [ ] **Step 6: Commit screenshot evidence**

```bash
git add docs/qa/2026-06-21-chan-multilevel-reversal-qa.md docs/qa/screenshots/2026-06-21-chan-multilevel-reversal*.png
git commit -m "docs: add chan multilevel reversal screenshots"
```

## Task 7: Final Verification And Close-Out

**Files:**
- Modify: `AGENTS.md` only if this work creates a future default rule beyond the existing strategy benchmark and screenshot rules.

- [ ] **Step 1: Run final verification**

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
test -s docs/qa/2026-06-21-chan-multilevel-reversal-qa.md
```

Expected: all commands pass.

- [ ] **Step 2: Run auto-sedimentation audit**

Read `docs/auto-sedimentation-skill.md` and `docs/rules/auto-sedimentation-closeout.md`. Confirm:

- Strategy benchmark evidence is in `docs/qa/`.
- Pending list moved the completed item and records exactly one next recommended feature.
- Screenshot evidence path is in QA and ready for final response.
- `AGENTS.md` remains unchanged unless a new future AI behavior rule was created.

- [ ] **Step 3: Final response checklist**

Final response must include:

- What strategy was added and how it uses daily, 30m, and 15m.
- Verification commands and pass counts.
- Benchmark summary with honest minute coverage caveats.
- Screenshot paths/images.
- Pending-list update and next recommended feature.
- `沉淀：已更新 ...`
