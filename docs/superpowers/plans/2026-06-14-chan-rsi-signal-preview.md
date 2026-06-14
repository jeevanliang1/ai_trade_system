# Chan RSI Signal Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first market_analysis strategy-fusion slice: a current-symbol research signal preview that combines lightweight Chan timing patterns with enhanced RSI context, visible in the existing React Strategy Workshop.

**Architecture:** Keep the feature in a pure research layer. Convert existing `list[Bar]` data into a normalized pandas frame, run deterministic Chan and enhanced RSI detectors, score the combined context, expose it through `POST /api/research/signals/preview`, then render the result in Strategy Workshop without changing execution, backtest, paper trading, broker, or live-trading behavior.

**Tech Stack:** Python 3.10+, pandas, FastAPI, Pydantic, pytest; React, TypeScript, Vitest, Testing Library, existing ECharts chart helpers.

---

## Boundaries

- Reimplement the relevant behavior in this repository. Do not copy large code blocks from `MambaWoW/market_analysis` because the inspected commit has no visible license file.
- Do not add ClickHouse, `chan-py`, `czsc`, full-market scanning, batch jobs, or live trading.
- Treat this as a research/timing preview. It may inform a human, but it must not place orders or bypass risk controls.
- Keep the response deterministic for tests and screenshots.

## File Structure

- Create `src/ai_trade_system/research/__init__.py`: public exports for the research signal preview package.
- Create `src/ai_trade_system/research/models.py`: dataclasses for signals, blockers, score, and preview payload.
- Create `src/ai_trade_system/research/dataframe.py`: `Bar` to pandas frame conversion and validation helpers.
- Create `src/ai_trade_system/research/enhanced_rsi.py`: RSI series, threshold, recovery, and divergence scanning.
- Create `src/ai_trade_system/research/chan.py`: lightweight pivot and Chan-style second/third buy/sell scanning.
- Create `src/ai_trade_system/research/service.py`: orchestration, blockers, scoring, and payload creation.
- Modify `src/ai_trade_system/api/schemas.py`: add `ResearchSignalsRequest`.
- Modify `src/ai_trade_system/api/service.py`: add `preview_research_signals`.
- Modify `src/ai_trade_system/api/app.py`: add `POST /api/research/signals/preview`.
- Modify `frontend/src/types.ts`: add research signal preview types.
- Modify `frontend/src/api/client.ts`: add `previewResearchSignals`.
- Modify `frontend/src/pages/pageTypes.ts`: add `researchSignals` state and `previewResearchSignals` action.
- Modify `frontend/src/shell/AppShell.tsx`: wire state clearing and async action.
- Modify `frontend/src/pages/StrategyPage.tsx`: add the Chan/RSI preview action, summary metrics, blockers, and signal table.
- Modify `frontend/src/styles.css`: add compact Strategy Workshop research panel styles.
- Modify `docs/context/pending-features.md`: remove the completed first-slice pending item and record the next recommended feature.
- Add or extend tests:
  - `tests/test_research_signals.py`
  - `tests/test_api_routes.py`
  - `frontend/src/api/client.test.ts`
  - `frontend/src/pages/StrategyPage.test.tsx`
  - `frontend/src/shell/AppShell.tasks.test.tsx`

## Task 1: Research Models And Bar Frame Conversion

**Files:**

- Create `src/ai_trade_system/research/__init__.py`
- Create `src/ai_trade_system/research/models.py`
- Create `src/ai_trade_system/research/dataframe.py`
- Create `tests/test_research_signals.py`

- [ ] **Step 1: Write failing tests**

Add the test module with shared helpers and the first conversion tests:

```python
from __future__ import annotations

from datetime import date, timedelta

import pytest

from ai_trade_system.market import Bar
from ai_trade_system.research.dataframe import bars_to_frame
from ai_trade_system.research.service import preview_research_signals


def _bar(index: int, close: float, *, high: float | None = None, low: float | None = None, volume: float = 1000.0) -> Bar:
    trading_day = date(2024, 1, 1) + timedelta(days=index)
    high_price = high if high is not None else close + 0.4
    low_price = low if low is not None else close - 0.4
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=trading_day,
        open_price=close - 0.1,
        high_price=high_price,
        low_price=low_price,
        close_price=close,
        volume=volume,
        turnover=round(volume * close, 2),
    )


def _bars(closes: list[float]) -> list[Bar]:
    return [_bar(index, close) for index, close in enumerate(closes)]


def test_bars_to_frame_sorts_and_maps_market_bars():
    frame = bars_to_frame([_bar(2, 12.0), _bar(0, 10.0), _bar(1, 11.0)])

    assert list(frame.columns) == ["trading_day", "symbol", "exchange", "open", "high", "low", "close", "volume", "turnover"]
    assert [value.isoformat() for value in frame["trading_day"].tolist()] == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert frame.iloc[-1]["close"] == 12.0


def test_preview_returns_no_bars_blocker_for_empty_input():
    preview = preview_research_signals([])

    assert preview.symbol == ""
    assert preview.score.direction == "neutral"
    assert preview.blockers[0].code == "NO_BARS"
    assert preview.signals == []
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_research_signals.py -v
```

Expected: import failure for `ai_trade_system.research`.

- [ ] **Step 3: Implement models**

Create `src/ai_trade_system/research/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ResearchSignal:
    trading_day: date
    symbol: str
    exchange: str
    kind: str
    action: str
    price: float
    strength: float
    score: float
    title: str
    reason: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResearchSignalBlocker:
    code: str
    message: str


@dataclass(frozen=True)
class ResearchSignalScore:
    total_score: float
    direction: str
    confidence: float
    chan_score: float
    rsi_score: float
    summary: str


@dataclass(frozen=True)
class ResearchSignalPreview:
    symbol: str
    exchange: str
    start: date | None
    end: date | None
    bars: int
    signals: list[ResearchSignal]
    score: ResearchSignalScore
    blockers: list[ResearchSignalBlocker] = field(default_factory=list)
```

- [ ] **Step 4: Implement frame conversion**

Create `src/ai_trade_system/research/dataframe.py`:

```python
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from ai_trade_system.market import Bar


FRAME_COLUMNS = ["trading_day", "symbol", "exchange", "open", "high", "low", "close", "volume", "turnover"]


def bars_to_frame(bars: Sequence[Bar]) -> pd.DataFrame:
    rows = [
        {
            "trading_day": bar.trading_day,
            "symbol": bar.symbol,
            "exchange": bar.exchange,
            "open": float(bar.open_price),
            "high": float(bar.high_price),
            "low": float(bar.low_price),
            "close": float(bar.close_price),
            "volume": float(bar.volume),
            "turnover": float(bar.turnover),
        }
        for bar in bars
    ]
    frame = pd.DataFrame(rows, columns=FRAME_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values("trading_day").reset_index(drop=True)
```

Create `src/ai_trade_system/research/__init__.py`:

```python
from ai_trade_system.research.service import preview_research_signals

__all__ = ["preview_research_signals"]
```

For `src/ai_trade_system/research/service.py`, add a minimal implementation that returns the empty-input blocker. Later tasks replace it with full signal scanning:

```python
from __future__ import annotations

from collections.abc import Sequence

from ai_trade_system.market import Bar
from ai_trade_system.research.models import ResearchSignalBlocker, ResearchSignalPreview, ResearchSignalScore


def preview_research_signals(bars: Sequence[Bar], *, min_bars: int = 60, lookback: int = 120) -> ResearchSignalPreview:
    if not bars:
        return ResearchSignalPreview(
            symbol="",
            exchange="",
            start=None,
            end=None,
            bars=0,
            signals=[],
            score=ResearchSignalScore(0.0, "neutral", 0.0, 0.0, 0.0, "暂无行情数据"),
            blockers=[ResearchSignalBlocker("NO_BARS", "没有可分析的行情数据")],
        )
    raise NotImplementedError("research signal preview requires detector implementation")
```

- [ ] **Step 5: Verify tests pass**

Run:

```bash
python -m pytest tests/test_research_signals.py -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/ai_trade_system/research tests/test_research_signals.py
git commit -m "feat: add research signal preview models"
```

## Task 2: Enhanced RSI Scanner

**Files:**

- Modify `src/ai_trade_system/research/models.py`
- Create `src/ai_trade_system/research/enhanced_rsi.py`
- Modify `tests/test_research_signals.py`

- [ ] **Step 1: Add failing RSI tests**

Append tests:

```python
from ai_trade_system.research.enhanced_rsi import relative_strength_index, scan_enhanced_rsi


def test_relative_strength_index_handles_rising_and_falling_windows():
    rising = relative_strength_index([10, 11, 12, 13, 14, 15, 16], period=3)
    falling = relative_strength_index([16, 15, 14, 13, 12, 11, 10], period=3)

    assert rising[-1] == 100.0
    assert falling[-1] == 0.0


def test_enhanced_rsi_marks_oversold_recovery_and_bearish_divergence():
    closes = [12, 11.5, 11, 10.4, 9.8, 9.5, 9.7, 10.1, 10.8, 11.4, 11.9, 12.3, 12.6, 12.9, 13.1, 13.0, 13.2]
    frame = bars_to_frame(_bars(closes))

    result = scan_enhanced_rsi(frame, period=3, lookback=30)
    kinds = {signal.kind for signal in result.signals}

    assert "RSI_OVERSOLD" in kinds
    assert "RSI_BULLISH_RECOVERY" in kinds
    assert result.rsi_score > 0
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_research_signals.py -v
```

Expected: import failure for `ai_trade_system.research.enhanced_rsi`.

- [ ] **Step 3: Add RSI result model**

Add to `src/ai_trade_system/research/models.py`:

```python
@dataclass(frozen=True)
class EnhancedRsiResult:
    signals: list[ResearchSignal]
    latest_rsi: float | None
    rsi_score: float
```

- [ ] **Step 4: Implement enhanced RSI**

Create `src/ai_trade_system/research/enhanced_rsi.py`:

```python
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from ai_trade_system.research.models import EnhancedRsiResult, ResearchSignal


def relative_strength_index(values: Sequence[float], period: int = 14) -> list[float | None]:
    series = pd.Series([float(value) for value in values], dtype="float64")
    if series.empty:
        return []
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0.0)
    rsi = rsi.mask((avg_gain == 0) & (avg_loss == 0), 50.0)
    return [None if pd.isna(value) else round(float(value), 2) for value in rsi.tolist()]


def scan_enhanced_rsi(frame: pd.DataFrame, *, period: int = 14, lookback: int = 120) -> EnhancedRsiResult:
    if frame.empty:
        return EnhancedRsiResult([], None, 0.0)

    working = frame.tail(lookback).copy()
    working["rsi"] = relative_strength_index(working["close"].tolist(), period)
    signals: list[ResearchSignal] = []
    symbol = str(working.iloc[-1]["symbol"])
    exchange = str(working.iloc[-1]["exchange"])

    for index, row in working.iterrows():
        rsi = row["rsi"]
        if pd.isna(rsi):
            continue
        if rsi <= 30:
            signals.append(_signal(row, symbol, exchange, "RSI_OVERSOLD", "buy", 0.35, 18.0, f"RSI {rsi:.2f} 进入超卖区", ("rsi", "oversold")))
        elif rsi >= 70:
            signals.append(_signal(row, symbol, exchange, "RSI_OVERBOUGHT", "sell", 0.35, -18.0, f"RSI {rsi:.2f} 进入超买区", ("rsi", "overbought")))

    signals.extend(_recovery_signals(working, symbol, exchange))
    latest_rsi = working["rsi"].dropna().iloc[-1] if not working["rsi"].dropna().empty else None
    rsi_score = _score_from_signals(signals)
    return EnhancedRsiResult(signals, None if latest_rsi is None else round(float(latest_rsi), 2), rsi_score)


def _recovery_signals(frame: pd.DataFrame, symbol: str, exchange: str) -> list[ResearchSignal]:
    signals: list[ResearchSignal] = []
    previous_rsi = None
    saw_oversold = False
    for _, row in frame.iterrows():
        rsi = row["rsi"]
        if pd.isna(rsi):
            continue
        if rsi <= 30:
            saw_oversold = True
        if saw_oversold and previous_rsi is not None and previous_rsi < 35 <= rsi:
            signals.append(_signal(row, symbol, exchange, "RSI_BULLISH_RECOVERY", "buy", 0.55, 24.0, f"RSI 从弱势区修复至 {rsi:.2f}", ("rsi", "recovery")))
            saw_oversold = False
        previous_rsi = rsi
    return signals


def _signal(row: pd.Series, symbol: str, exchange: str, kind: str, action: str, strength: float, score: float, reason: str, tags: tuple[str, ...]) -> ResearchSignal:
    return ResearchSignal(
        trading_day=row["trading_day"],
        symbol=symbol,
        exchange=exchange,
        kind=kind,
        action=action,
        price=round(float(row["close"]), 3),
        strength=strength,
        score=score,
        title=kind.replace("_", " "),
        reason=reason,
        tags=tags,
    )


def _score_from_signals(signals: list[ResearchSignal]) -> float:
    if not signals:
        return 0.0
    recent = signals[-6:]
    return round(max(-50.0, min(50.0, sum(signal.score for signal in recent))), 2)
```

- [ ] **Step 5: Verify tests pass**

Run:

```bash
python -m pytest tests/test_research_signals.py -v
```

Expected: all research signal tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/ai_trade_system/research tests/test_research_signals.py
git commit -m "feat: add enhanced rsi research signals"
```

## Task 3: Lightweight Chan Scanner

**Files:**

- Modify `src/ai_trade_system/research/models.py`
- Create `src/ai_trade_system/research/chan.py`
- Modify `tests/test_research_signals.py`

- [ ] **Step 1: Add failing Chan tests**

Append tests:

```python
from ai_trade_system.research.chan import scan_chan_patterns


def test_chan_scanner_marks_second_buy_after_higher_low_reversal():
    closes = [12.0, 11.4, 10.8, 10.1, 9.8, 10.4, 11.1, 11.6, 10.9, 10.4, 10.8, 11.5, 12.0, 12.4]
    frame = bars_to_frame(_bars(closes))

    result = scan_chan_patterns(frame, lookback=40, order=1)

    assert any(signal.kind == "CHAN_BUY_T2" for signal in result.signals)
    assert result.chan_score > 0


def test_chan_scanner_marks_second_sell_after_lower_high_breakdown():
    closes = [9.0, 9.8, 10.6, 11.4, 12.0, 11.5, 10.9, 10.2, 10.8, 11.3, 10.7, 10.0, 9.4, 9.0]
    frame = bars_to_frame(_bars(closes))

    result = scan_chan_patterns(frame, lookback=40, order=1)

    assert any(signal.kind == "CHAN_SELL_T2" for signal in result.signals)
    assert result.chan_score < 0
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_research_signals.py -v
```

Expected: import failure for `ai_trade_system.research.chan`.

- [ ] **Step 3: Add Chan result model**

Add to `src/ai_trade_system/research/models.py`:

```python
@dataclass(frozen=True)
class ChanPatternResult:
    signals: list[ResearchSignal]
    chan_score: float
```

- [ ] **Step 4: Implement lightweight Chan patterns**

Create `src/ai_trade_system/research/chan.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_trade_system.research.models import ChanPatternResult, ResearchSignal


@dataclass(frozen=True)
class SwingPoint:
    index: int
    kind: str
    price: float


def scan_chan_patterns(frame: pd.DataFrame, *, lookback: int = 120, order: int = 2) -> ChanPatternResult:
    if frame.empty or len(frame) < (order * 2 + 6):
        return ChanPatternResult([], 0.0)

    working = frame.tail(lookback).reset_index(drop=True)
    swings = _swing_points(working, order=order)
    symbol = str(working.iloc[-1]["symbol"])
    exchange = str(working.iloc[-1]["exchange"])
    signals: list[ResearchSignal] = []

    buy = _second_buy(working, swings, symbol, exchange)
    if buy is not None:
        signals.append(buy)
    sell = _second_sell(working, swings, symbol, exchange)
    if sell is not None:
        signals.append(sell)

    chan_score = round(max(-50.0, min(50.0, sum(signal.score for signal in signals[-4:]))), 2)
    return ChanPatternResult(signals, chan_score)


def _swing_points(frame: pd.DataFrame, *, order: int) -> list[SwingPoint]:
    swings: list[SwingPoint] = []
    for index in range(order, len(frame) - order):
        window = frame.iloc[index - order : index + order + 1]
        row = frame.iloc[index]
        high = float(row["high"])
        low = float(row["low"])
        if high >= float(window["high"].max()):
            swings.append(SwingPoint(index, "high", high))
        if low <= float(window["low"].min()):
            swings.append(SwingPoint(index, "low", low))
    return swings


def _second_buy(frame: pd.DataFrame, swings: list[SwingPoint], symbol: str, exchange: str) -> ResearchSignal | None:
    lows = [point for point in swings if point.kind == "low"]
    if len(lows) < 2:
        return None
    prior, latest = lows[-2], lows[-1]
    last_close = float(frame.iloc[-1]["close"])
    if latest.price <= prior.price or last_close <= latest.price * 1.05:
        return None
    row = frame.iloc[-1]
    return ResearchSignal(
        trading_day=row["trading_day"],
        symbol=symbol,
        exchange=exchange,
        kind="CHAN_BUY_T2",
        action="buy",
        price=round(last_close, 3),
        strength=0.62,
        score=32.0,
        title="缠论二买",
        reason="回落低点抬高后向上修复，符合轻量二买观察条件",
        tags=("chan", "second-buy"),
    )


def _second_sell(frame: pd.DataFrame, swings: list[SwingPoint], symbol: str, exchange: str) -> ResearchSignal | None:
    highs = [point for point in swings if point.kind == "high"]
    if len(highs) < 2:
        return None
    prior, latest = highs[-2], highs[-1]
    last_close = float(frame.iloc[-1]["close"])
    if latest.price >= prior.price or last_close >= latest.price * 0.95:
        return None
    row = frame.iloc[-1]
    return ResearchSignal(
        trading_day=row["trading_day"],
        symbol=symbol,
        exchange=exchange,
        kind="CHAN_SELL_T2",
        action="sell",
        price=round(last_close, 3),
        strength=0.62,
        score=-32.0,
        title="缠论二卖",
        reason="反弹高点降低后向下破位，符合轻量二卖观察条件",
        tags=("chan", "second-sell"),
    )
```

- [ ] **Step 5: Verify tests pass**

Run:

```bash
python -m pytest tests/test_research_signals.py -v
```

Expected: all research signal tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/ai_trade_system/research tests/test_research_signals.py
git commit -m "feat: add lightweight chan research signals"
```

## Task 4: Research Signal Orchestration And Scoring

**Files:**

- Modify `src/ai_trade_system/research/service.py`
- Modify `tests/test_research_signals.py`

- [ ] **Step 1: Add failing orchestration tests**

Append tests:

```python
def test_preview_returns_insufficient_bars_blocker_before_running_detectors():
    preview = preview_research_signals(_bars([10, 10.2, 10.1]), min_bars=10)

    assert preview.blockers[0].code == "INSUFFICIENT_BARS"
    assert preview.signals == []
    assert preview.score.direction == "neutral"


def test_preview_combines_chan_and_rsi_scores_for_valid_bars():
    closes = [12, 11.4, 10.8, 10.1, 9.8, 10.4, 11.1, 11.6, 10.9, 10.4, 10.8, 11.5, 12.0, 12.4, 12.8, 13.0]
    preview = preview_research_signals(_bars(closes), min_bars=12, lookback=40)

    assert preview.symbol == "000001"
    assert preview.exchange == "SZSE"
    assert preview.start.isoformat() == "2024-01-01"
    assert preview.end.isoformat() == "2024-01-16"
    assert preview.blockers == []
    assert preview.score.direction in {"bullish", "bearish", "neutral"}
    assert preview.signals
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_research_signals.py -v
```

Expected: `NotImplementedError` from `preview_research_signals`.

- [ ] **Step 3: Implement service orchestration**

Replace `src/ai_trade_system/research/service.py` with:

```python
from __future__ import annotations

from collections.abc import Sequence

from ai_trade_system.market import Bar
from ai_trade_system.research.chan import scan_chan_patterns
from ai_trade_system.research.dataframe import bars_to_frame
from ai_trade_system.research.enhanced_rsi import scan_enhanced_rsi
from ai_trade_system.research.models import ResearchSignal, ResearchSignalBlocker, ResearchSignalPreview, ResearchSignalScore


def preview_research_signals(bars: Sequence[Bar], *, min_bars: int = 60, lookback: int = 120) -> ResearchSignalPreview:
    if not bars:
        return _empty_preview("NO_BARS", "没有可分析的行情数据")

    frame = bars_to_frame(bars)
    symbol = str(frame.iloc[-1]["symbol"])
    exchange = str(frame.iloc[-1]["exchange"])
    if len(frame) < min_bars:
        return ResearchSignalPreview(
            symbol=symbol,
            exchange=exchange,
            start=frame.iloc[0]["trading_day"],
            end=frame.iloc[-1]["trading_day"],
            bars=len(frame),
            signals=[],
            score=ResearchSignalScore(0.0, "neutral", 0.0, 0.0, 0.0, "K线数量不足，暂不生成缠论和增强 RSI 信号"),
            blockers=[ResearchSignalBlocker("INSUFFICIENT_BARS", f"至少需要 {min_bars} 根K线，当前 {len(frame)} 根")],
        )

    chan = scan_chan_patterns(frame, lookback=lookback)
    rsi = scan_enhanced_rsi(frame, lookback=lookback)
    signals = sorted([*chan.signals, *rsi.signals], key=lambda signal: (signal.trading_day, signal.kind))
    score = _score(chan.chan_score, rsi.rsi_score, signals)
    return ResearchSignalPreview(
        symbol=symbol,
        exchange=exchange,
        start=frame.iloc[0]["trading_day"],
        end=frame.iloc[-1]["trading_day"],
        bars=len(frame),
        signals=signals,
        score=score,
        blockers=[],
    )


def _empty_preview(code: str, message: str) -> ResearchSignalPreview:
    return ResearchSignalPreview(
        symbol="",
        exchange="",
        start=None,
        end=None,
        bars=0,
        signals=[],
        score=ResearchSignalScore(0.0, "neutral", 0.0, 0.0, 0.0, message),
        blockers=[ResearchSignalBlocker(code, message)],
    )


def _score(chan_score: float, rsi_score: float, signals: list[ResearchSignal]) -> ResearchSignalScore:
    total = round(max(-100.0, min(100.0, chan_score + rsi_score)), 2)
    if total >= 20:
        direction = "bullish"
    elif total <= -20:
        direction = "bearish"
    else:
        direction = "neutral"
    confidence = round(min(1.0, abs(total) / 100.0 + min(len(signals), 6) * 0.04), 2)
    if not signals:
        summary = "未发现缠论或增强 RSI 触发信号"
    else:
        summary = f"发现 {len(signals)} 个研究信号，综合方向为 {direction}"
    return ResearchSignalScore(total, direction, confidence, round(chan_score, 2), round(rsi_score, 2), summary)
```

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python -m pytest tests/test_research_signals.py -v
```

Expected: all research signal tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/ai_trade_system/research tests/test_research_signals.py
git commit -m "feat: score chan rsi research preview"
```

## Task 5: FastAPI Contract

**Files:**

- Modify `src/ai_trade_system/api/schemas.py`
- Modify `src/ai_trade_system/api/service.py`
- Modify `src/ai_trade_system/api/app.py`
- Modify `tests/test_api_routes.py`

- [ ] **Step 1: Add failing API tests**

Append to `tests/test_api_routes.py`:

```python
def test_research_signals_preview_route_returns_blocker_for_short_demo_data(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 20})
    assert demo_response.status_code == 200

    response = client.post("/api/research/signals/preview", json={"settings": settings, "min_bars": 60, "lookback": 120})

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "000001"
    assert payload["blockers"][0]["code"] == "INSUFFICIENT_BARS"
    assert payload["score"]["direction"] == "neutral"


def test_research_signals_preview_route_returns_signals_for_demo_data(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 120})
    assert demo_response.status_code == 200

    response = client.post("/api/research/signals/preview", json={"settings": settings, "min_bars": 40, "lookback": 120})

    assert response.status_code == 200
    payload = response.json()
    assert payload["bars"] == 120
    assert "total_score" in payload["score"]
    assert isinstance(payload["signals"], list)
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_api_routes.py -k research_signals -v
```

Expected: `404 Not Found` for `/api/research/signals/preview`.

- [ ] **Step 3: Add request schema**

In `src/ai_trade_system/api/schemas.py`, add after `AIResearchRequest`:

```python
class ResearchSignalsRequest(DataRequest):
    min_bars: int = Field(default=60, ge=20, le=500)
    lookback: int = Field(default=120, ge=20, le=500)
```

- [ ] **Step 4: Add API service function**

In `src/ai_trade_system/api/service.py`, import the research service:

```python
from ai_trade_system.research import preview_research_signals as build_research_signal_preview
```

Add the request type import:

```python
ResearchSignalsRequest,
```

Add the service function after `research_ai`:

```python
def preview_research_signals(request: ResearchSignalsRequest) -> dict[str, Any]:
    bars = _load_bars(request.settings)
    preview = build_research_signal_preview(bars, min_bars=request.min_bars, lookback=request.lookback)
    return _serialize(preview)
```

- [ ] **Step 5: Add route**

In `src/ai_trade_system/api/app.py`, import `ResearchSignalsRequest` and add after `/api/ai/research`:

```python
    @app.post("/api/research/signals/preview")
    def research_signals_preview(request: ResearchSignalsRequest) -> dict[str, Any]:
        return _handle(lambda: service.preview_research_signals(request))
```

- [ ] **Step 6: Verify API tests pass**

Run:

```bash
python -m pytest tests/test_api_routes.py -k "research_signals or demo_data" -v
```

Expected: selected tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/ai_trade_system/api tests/test_api_routes.py
git commit -m "feat: expose research signal preview api"
```

## Task 6: Frontend Types, Client, And App State

**Files:**

- Modify `frontend/src/types.ts`
- Modify `frontend/src/api/client.ts`
- Modify `frontend/src/api/client.test.ts`
- Modify `frontend/src/pages/pageTypes.ts`
- Modify `frontend/src/shell/AppShell.tsx`
- Modify `frontend/src/shell/AppShell.tasks.test.tsx`

- [ ] **Step 1: Add failing client and shell tests**

In `frontend/src/api/client.test.ts`, add a test that mocks `fetch` and asserts:

```typescript
await api.previewResearchSignals(settings);

expect(fetch).toHaveBeenCalledWith(
  "/api/research/signals/preview",
  expect.objectContaining({
    method: "POST",
    body: JSON.stringify({ settings, min_bars: 60, lookback: 120 })
  })
);
```

In `frontend/src/shell/AppShell.tasks.test.tsx`, add a test that mocks `api.previewResearchSignals`, clicks the Strategy Workshop research button after render, and expects the API result to appear in state-driven UI text.

- [ ] **Step 2: Verify frontend tests fail**

Run:

```bash
npm --prefix frontend test -- client.test.ts AppShell.tasks.test.tsx
```

Expected: missing `previewResearchSignals` client/action or missing UI trigger.

- [ ] **Step 3: Add TypeScript contracts**

Add to `frontend/src/types.ts` near the signal types:

```typescript
export type ResearchSignal = {
  trading_day: string;
  symbol: string;
  exchange: string;
  kind: string;
  action: "buy" | "sell" | "watch" | string;
  price: number;
  strength: number;
  score: number;
  title: string;
  reason: string;
  tags: string[];
};

export type ResearchSignalBlocker = {
  code: "NO_BARS" | "INSUFFICIENT_BARS" | "UNSUPPORTED_DATA" | "OPTIONAL_ENGINE_UNAVAILABLE" | string;
  message: string;
};

export type ResearchSignalScore = {
  total_score: number;
  direction: "bullish" | "bearish" | "neutral" | string;
  confidence: number;
  chan_score: number;
  rsi_score: number;
  summary: string;
};

export type ResearchSignalPreview = {
  symbol: string;
  exchange: string;
  start: string | null;
  end: string | null;
  bars: number;
  signals: ResearchSignal[];
  score: ResearchSignalScore;
  blockers: ResearchSignalBlocker[];
};
```

- [ ] **Step 4: Add API client method**

Import `ResearchSignalPreview` in `frontend/src/api/client.ts` and add:

```typescript
  previewResearchSignals: (settings: PlatformSettings, min_bars = 60, lookback = 120) =>
    apiRequest<ResearchSignalPreview>("/api/research/signals/preview", {
      method: "POST",
      body: JSON.stringify({ settings, min_bars, lookback })
    }),
```

- [ ] **Step 5: Add platform state and action**

In `frontend/src/pages/pageTypes.ts`, import `ResearchSignalPreview`, add:

```typescript
  researchSignals: ResearchSignalPreview | null;
```

Add action:

```typescript
  previewResearchSignals: () => Promise<void>;
```

In `frontend/src/shell/AppShell.tsx`, initialize:

```typescript
    researchSignals: null,
```

When data target changes, clear it with `researchSignals: null`.

Add action:

```typescript
      previewResearchSignals: () =>
        runTask(setState, "生成缠论/RSI研判", async (current) => ({
          researchSignals: await api.previewResearchSignals(current.settings)
        })),
```

- [ ] **Step 6: Verify targeted frontend tests**

Run:

```bash
npm --prefix frontend test -- client.test.ts AppShell.tasks.test.tsx
```

Expected: selected tests pass after the UI task adds the button.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/client.ts frontend/src/api/client.test.ts frontend/src/pages/pageTypes.ts frontend/src/shell/AppShell.tsx frontend/src/shell/AppShell.tasks.test.tsx
git commit -m "feat: wire research signal preview state"
```

## Task 7: Strategy Workshop Research Panel

**Files:**

- Modify `frontend/src/pages/StrategyPage.tsx`
- Modify `frontend/src/pages/StrategyPage.test.tsx`
- Modify `frontend/src/styles.css`

- [ ] **Step 1: Add failing StrategyPage tests**

Extend `makeProps` in `frontend/src/pages/StrategyPage.test.tsx` with `researchSignals: null` and `previewResearchSignals: vi.fn()`.

Add tests:

```typescript
test("StrategyPage can request Chan RSI research preview", async () => {
  const user = userEvent.setup();
  const previewResearchSignals = vi.fn().mockResolvedValue(undefined);

  render(<StrategyPage {...makeProps({}, { previewResearchSignals })} />);

  await user.click(screen.getByRole("button", { name: "缠论/RSI研判" }));

  expect(previewResearchSignals).toHaveBeenCalled();
});

test("StrategyPage renders research blockers and populated signal rows", () => {
  render(
    <StrategyPage
      {...makeProps({
        researchSignals: {
          symbol: "000001",
          exchange: "SZSE",
          start: "2024-01-01",
          end: "2024-04-01",
          bars: 80,
          score: { total_score: 32, direction: "bullish", confidence: 0.58, chan_score: 32, rsi_score: 0, summary: "发现 1 个研究信号，综合方向为 bullish" },
          blockers: [],
          signals: [
            {
              trading_day: "2024-03-29",
              symbol: "000001",
              exchange: "SZSE",
              kind: "CHAN_BUY_T2",
              action: "buy",
              price: 12.4,
              strength: 0.62,
              score: 32,
              title: "缠论二买",
              reason: "回落低点抬高后向上修复",
              tags: ["chan", "second-buy"]
            }
          ]
        }
      })}
    />
  );

  expect(screen.getByText("缠论/RSI研判")).toBeInTheDocument();
  expect(screen.getByText("CHAN_BUY_T2")).toBeInTheDocument();
  expect(screen.getByText("回落低点抬高后向上修复")).toBeInTheDocument();
});
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
npm --prefix frontend test -- StrategyPage.test.tsx
```

Expected: missing button and missing research panel rendering.

- [ ] **Step 3: Add UI action and panel**

In `frontend/src/pages/StrategyPage.tsx`:

- Import `Activity` from `lucide-react`.
- Import `ResearchSignalPreview` from `../types`.
- Add a `researchRows` memo:

```typescript
  const researchRows = useMemo(() => researchSignalRows(state.researchSignals), [state.researchSignals]);
```

- Add a toolbar button near `预览信号`:

```tsx
        <ToolbarButton icon={<Activity size={16} />} onClick={actions.previewResearchSignals}>
          缠论/RSI研判
        </ToolbarButton>
```

- Add a compact panel below the chart or result tabs:

```tsx
        <ResearchSignalPanel preview={state.researchSignals} rows={researchRows} />
```

Add helper components at the bottom of the file:

```tsx
function ResearchSignalPanel({ preview, rows }: { preview: ResearchSignalPreview | null; rows: Record<string, unknown>[] }) {
  if (!preview) {
    return (
      <section className="panel research-signal-panel">
        <div className="panel-title between">
          <span>缠论/RSI研判</span>
          <span className="caption">未生成</span>
        </div>
        <div className="empty-table">暂无研判结果</div>
      </section>
    );
  }

  return (
    <section className="panel research-signal-panel">
      <div className="panel-title between">
        <span>缠论/RSI研判</span>
        <span className={`status-pill ${preview.score.direction}`}>{preview.score.direction}</span>
      </div>
      <MetricStrip
        metrics={[
          { label: "综合分", value: preview.score.total_score.toFixed(1), tone: preview.score.total_score >= 0 ? "positive" : "negative" },
          { label: "置信度", value: `${Math.round(preview.score.confidence * 100)}%` },
          { label: "缠论", value: preview.score.chan_score.toFixed(1) },
          { label: "RSI", value: preview.score.rsi_score.toFixed(1) }
        ]}
      />
      {preview.blockers.length ? (
        <div className="parameter-errors" role="alert">
          {preview.blockers.map((blocker) => (
            <span key={blocker.code}>{blocker.message}</span>
          ))}
        </div>
      ) : null}
      <p className="caption">{preview.score.summary}</p>
      <DataTable rows={rows} columns={["日期", "类型", "方向", "价格", "分数", "原因"]} emptyText="暂无缠论/RSI触发信号" />
    </section>
  );
}

function researchSignalRows(preview: ResearchSignalPreview | null): Record<string, unknown>[] {
  return (preview?.signals ?? []).map((signal) => ({
    日期: signal.trading_day,
    类型: signal.kind,
    方向: signal.action,
    价格: signal.price,
    分数: signal.score,
    原因: signal.reason
  }));
}
```

- [ ] **Step 4: Add compact styles**

In `frontend/src/styles.css`, add:

```css
.research-signal-panel {
  display: grid;
  gap: 10px;
}

.status-pill {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: #eef2ff;
  color: #3730a3;
}

.status-pill.bullish {
  background: #ecfdf3;
  color: #027a48;
}

.status-pill.bearish {
  background: #fef3f2;
  color: #b42318;
}
```

- [ ] **Step 5: Verify StrategyPage tests**

Run:

```bash
npm --prefix frontend test -- StrategyPage.test.tsx
```

Expected: all StrategyPage tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/StrategyPage.tsx frontend/src/pages/StrategyPage.test.tsx frontend/src/styles.css
git commit -m "feat: show chan rsi preview in strategy workshop"
```

## Task 8: Full Verification, Browser QA, And Sedimentation

**Files:**

- Modify `docs/context/pending-features.md`
- Optionally modify `docs/architecture.md` if the implementation adds durable module details not already covered by code.

- [ ] **Step 1: Run backend tests**

```bash
python -m pytest
```

Expected: all Python tests pass.

- [ ] **Step 2: Run frontend tests and build**

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

Expected: all Vitest tests pass and the Vite build completes.

- [ ] **Step 3: Browser screenshot acceptance**

Start the React + FastAPI surface:

```bash
./scripts/run_app.sh
```

In another shell, capture the standard screenshots:

```bash
node scripts/capture_app_screenshots.mjs
```

Acceptance checks:

- Desktop screenshot shows Strategy Workshop.
- `缠论/RSI研判` button is visible.
- After clicking the button, the research panel shows either blockers or a populated signal table.
- No horizontal overflow at the narrow viewport.

- [ ] **Step 4: Update pending feature handoff**

In `docs/context/pending-features.md`:

- Move `Add current-symbol Chan plus enhanced RSI signal preview...` from `Pending` to `Already Implemented Baseline`.
- Keep `Wrap the confirmed Chan plus enhanced RSI preview as a backtestable Strategy after the preview semantics are validated` as the next pending item.
- Keep exactly one `Next Recommended Feature` and set it to the backtestable Strategy wrapper.
- Update `Last updated` to the implementation completion date.

- [ ] **Step 5: Closeout audit**

Run lightweight documentation checks:

```bash
test -s docs/context/pending-features.md
test -s docs/superpowers/plans/2026-06-14-chan-rsi-signal-preview.md
```

Then review whether `docs/architecture.md` needs one new bullet for the `ai_trade_system.research` package. Add it only if the final code introduces a durable module boundary that is not obvious from existing docs.

- [ ] **Step 6: Final commit**

```bash
git add docs/context/pending-features.md docs/architecture.md
git commit -m "docs: record chan rsi preview completion"
```

Skip `docs/architecture.md` from the `git add` command if it was not changed.

## Final Verification Matrix

- `python -m pytest`
- `npm --prefix frontend test`
- `npm --prefix frontend run build`
- `node scripts/capture_app_screenshots.mjs`
- Manual browser interaction: click `缠论/RSI研判` in Strategy Workshop and confirm the panel updates.

## Self-Review Checklist

- [ ] The implementation only adds research preview behavior and does not alter live trading, paper execution semantics, or broker gateway behavior.
- [ ] Every new Python module has focused pytest coverage.
- [ ] API response fields serialize dates as ISO strings through the existing `_serialize` helper.
- [ ] Frontend state clears stale research results when the data target changes.
- [ ] UI copy does not promise automated orders or production trading signals.
- [ ] The pending feature list records the completed slice and exactly one next recommended feature.
- [ ] The plan and docs contain no unfinished markers.
