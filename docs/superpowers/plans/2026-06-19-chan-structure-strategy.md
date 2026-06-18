# Chan Structure Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-cut Chan structure analyzer and built-in `ChanStructureStrategy` that can be discovered, configured, backtested, and shown in the React workbench.

**Architecture:** Create a focused `chan_structure.py` research module that converts daily bars into normalized K-lines, fractals, strokes, pivots, and structure signals. Wrap that analyzer in a built-in strategy class under the existing `popular.py` strategy module, then register Chinese metadata and parameter guidance through `strategy_registry.py`.

**Tech Stack:** Python 3, dataclasses, pandas-backed existing research frame utilities, pytest, existing Strategy/Signal/ResearchSignal models.

---

## File Structure

- Create `src/ai_trade_system/research/chan_structure.py`: pure-Python Chan structure analyzer and signal generator.
- Modify `src/ai_trade_system/strategies/popular.py`: add `ChanStructureStrategy`.
- Modify `src/ai_trade_system/strategy_registry.py`: register the strategy and add parameter guidance for `min_stroke_bars` and `min_rebound_pct`.
- Modify `tests/test_research_signals.py`: add analyzer-level TDD coverage.
- Modify `tests/test_builtin_popular_strategies.py`: add strategy behavior coverage.
- Modify `tests/test_strategy_registry.py`: add registry metadata and parameter guidance checks.
- Modify `docs/context/pending-features.md`: record completed Chan structure strategy and next recommended feature.
- Create `docs/qa/2026-06-19-chan-structure-strategy-qa.md`: record verification and browser evidence.

## Task 1: Analyzer RED Tests

**Files:**
- Modify: `tests/test_research_signals.py`

- [ ] Add imports for the new module:

```python
from ai_trade_system.research.chan_structure import normalize_containment, scan_chan_structure
```

- [ ] Add `test_chan_structure_normalizes_contained_klines`:

```python
def test_chan_structure_normalizes_contained_klines():
    bars = [
        _bar(0, 10.0, high=10.0, low=9.0),
        _bar(1, 10.4, high=11.0, low=10.0),
        _bar(2, 10.5, high=10.8, low=10.2),
        _bar(3, 11.0, high=12.0, low=10.8),
    ]

    normalized = normalize_containment(bars_to_frame(bars))

    assert len(normalized) == 3
    assert normalized[1].high == 11.0
    assert normalized[1].low == 10.2
```

- [ ] Add `test_chan_structure_builds_fractals_strokes_and_pivots`:

```python
def test_chan_structure_builds_fractals_strokes_and_pivots():
    bars = [
        _bar(0, 10.0, high=10.4, low=9.8),
        _bar(1, 9.4, high=9.8, low=9.1),
        _bar(2, 10.2, high=10.7, low=9.9),
        _bar(3, 11.2, high=11.8, low=10.8),
        _bar(4, 10.4, high=10.9, low=10.0),
        _bar(5, 9.8, high=10.1, low=9.4),
        _bar(6, 10.8, high=11.2, low=10.2),
        _bar(7, 11.6, high=12.0, low=11.0),
        _bar(8, 10.8, high=11.2, low=10.2),
        _bar(9, 10.1, high=10.4, low=9.7),
        _bar(10, 11.1, high=11.5, low=10.7),
        _bar(11, 11.8, high=12.3, low=11.3),
    ]

    result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=2, min_rebound_pct=0.03)

    assert [fractal.kind for fractal in result.fractals] == ["bottom", "top", "bottom", "top", "bottom"]
    assert [stroke.direction for stroke in result.strokes[:4]] == ["up", "down", "up", "down"]
    assert result.pivots
```

- [ ] Add `test_chan_structure_marks_third_buy_and_sell_points`:

```python
def test_chan_structure_marks_third_buy_and_sell_points():
    buy_bars = [
        _bar(0, 10.0, high=10.4, low=9.8),
        _bar(1, 9.4, high=9.8, low=9.1),
        _bar(2, 10.4, high=10.9, low=10.0),
        _bar(3, 11.6, high=12.0, low=11.1),
        _bar(4, 10.8, high=11.0, low=10.2),
        _bar(5, 10.1, high=10.5, low=9.7),
        _bar(6, 11.5, high=12.0, low=11.0),
        _bar(7, 12.8, high=13.2, low=12.2),
        _bar(8, 12.2, high=12.4, low=11.8),
        _bar(9, 11.9, high=12.1, low=11.6),
        _bar(10, 12.6, high=12.9, low=12.1),
    ]
    sell_bars = [
        _bar(0, 12.0, high=12.4, low=11.7),
        _bar(1, 12.8, high=13.2, low=12.2),
        _bar(2, 11.8, high=12.1, low=11.4),
        _bar(3, 10.7, high=11.1, low=10.2),
        _bar(4, 11.3, high=11.7, low=10.9),
        _bar(5, 12.0, high=12.4, low=11.6),
        _bar(6, 10.9, high=11.3, low=10.5),
        _bar(7, 9.8, high=10.2, low=9.4),
        _bar(8, 10.4, high=10.8, low=10.0),
        _bar(9, 10.7, high=10.9, low=10.3),
        _bar(10, 10.1, high=10.5, low=9.8),
    ]

    buy_result = scan_chan_structure(bars_to_frame(buy_bars), min_stroke_bars=2, min_rebound_pct=0.03)
    sell_result = scan_chan_structure(bars_to_frame(sell_bars), min_stroke_bars=2, min_rebound_pct=0.03)

    assert any(signal.kind == "CHAN_STRUCT_BUY_T3" for signal in buy_result.signals)
    assert any(signal.kind == "CHAN_STRUCT_SELL_T3" for signal in sell_result.signals)
```

- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
```

Expected: fail with `ModuleNotFoundError` or missing symbol errors for `chan_structure`.

## Task 2: Analyzer Implementation

**Files:**
- Create: `src/ai_trade_system/research/chan_structure.py`
- Test: `tests/test_research_signals.py`

- [ ] Implement dataclasses and public functions:

```python
@dataclass(frozen=True)
class ChanKLine:
    index: int
    trading_day: date
    symbol: str
    exchange: str
    high: float
    low: float
    close: float

@dataclass(frozen=True)
class ChanFractal:
    index: int
    trading_day: date
    kind: str
    price: float
    high: float
    low: float

@dataclass(frozen=True)
class ChanStroke:
    start: ChanFractal
    end: ChanFractal
    direction: str
    high: float
    low: float

@dataclass(frozen=True)
class ChanPivot:
    start_index: int
    end_index: int
    low: float
    high: float

@dataclass(frozen=True)
class ChanStructureResult:
    klines: list[ChanKLine]
    fractals: list[ChanFractal]
    strokes: list[ChanStroke]
    pivots: list[ChanPivot]
    signals: list[ResearchSignal]
    chan_score: float
```

- [ ] Implement `normalize_containment(frame: pd.DataFrame) -> list[ChanKLine]`.
- [ ] Implement strict fractal detection and same-kind fractal cleanup.
- [ ] Implement stroke construction using `min_stroke_bars`.
- [ ] Implement pivot construction from three consecutive stroke ranges.
- [ ] Implement second and third buy/sell signal generation.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
```

Expected: all research-signal tests pass.

## Task 3: Strategy RED Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`

- [ ] Import `ChanStructureStrategy`.
- [ ] Add a structure-bar helper if needed:

```python
def make_chan_bar(index: int, close: float, high: float, low: float) -> Bar:
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=date(2024, 1, 1) + timedelta(days=index),
        open_price=close,
        high_price=high,
        low_price=low,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
    )
```

- [ ] Add `test_chan_structure_strategy_emits_buy_from_structural_buy_signal`.
- [ ] Add `test_chan_structure_strategy_emits_sell_after_structural_sell_signal`.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py -q
```

Expected: fail because `ChanStructureStrategy` is not implemented.

## Task 4: Strategy Implementation

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`

- [ ] Import `scan_chan_structure` and add `ChanStructureStrategy`.
- [ ] Use a rolling `deque[Bar]` with `maxlen=lookback`.
- [ ] On each current bar, call the analyzer after `min_bars` bars.
- [ ] Select current-bar candidate signals sorted by absolute score descending, with third-class signals naturally ranking higher.
- [ ] Emit long-only `Signal("buy", ...)` or `Signal("sell", ...)` and dedupe by `(trading_day, kind, action)`.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py -q
```

Expected: strategy tests pass.

## Task 5: Registry RED Tests And Metadata

**Files:**
- Modify: `tests/test_strategy_registry.py`
- Modify: `src/ai_trade_system/strategy_registry.py`

- [ ] Add a failing test asserting `ChanStructureStrategy` appears with display name `缠论结构策略`.
- [ ] Add assertions for parameter guidance on `min_stroke_bars` and `min_rebound_pct`.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py -q
```

Expected: fail before registry update.

- [ ] Add a `StrategySpec` for `ChanStructureStrategy` in `BUILTIN_STRATEGIES`.
- [ ] Add `PARAMETER_GUIDANCE` entries:
  - `min_stroke_bars`: controls stroke spacing strictness.
  - `min_rebound_pct`: controls second buy/sell rebound or breakdown confirmation.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py -q
```

Expected: registry tests pass.

## Task 6: Documentation, Verification, Browser QA

**Files:**
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-19-chan-structure-strategy-qa.md`

- [ ] Add completed baseline entry for `ChanStructureStrategy`.
- [ ] Add a new pending follow-up for visualizing Chan structure overlays or integrating the analyzer into Signal Radar.
- [ ] Keep exactly one next recommended feature.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test && npm run build
```

- [ ] Start `./scripts/run_app.sh`.
- [ ] Capture a browser screenshot of the React Strategy Workshop showing `缠论结构策略` in the strategy list or selected state.
- [ ] Record verification and screenshot path in QA docs.
- [ ] Run `git status --short`.
- [ ] Commit implementation:

```bash
git add src tests docs
git commit -m "feat: add chan structure strategy"
```
