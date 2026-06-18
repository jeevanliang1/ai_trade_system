# Chan Structure Overlays Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Strategy Workshop K-line overlays for Chan fractals, strokes, pivots, and T2/T3 signals.

**Architecture:** Extend the existing research preview dataclass with optional chart-ready Chan structure data, then pass that payload through the React state to `priceOption`. Keep chart option changes backward-compatible by adding one optional argument instead of changing existing callers.

**Tech Stack:** Python 3 dataclasses, FastAPI serialization, pytest, React/TypeScript/Vitest, ECharts option objects.

---

## File Structure

- Modify `src/ai_trade_system/research/models.py`: add Chan overlay dataclasses and optional field on `ResearchSignalPreview`.
- Modify `src/ai_trade_system/research/service.py`: run `scan_chan_structure` and build overlay payload for empty, insufficient, and valid previews.
- Modify `tests/test_research_signals.py`: add failing tests for preview overlay payload.
- Modify `frontend/src/types.ts`: add structure overlay object types and `ResearchSignalPreview.chan_structure`.
- Modify `frontend/src/pages/chartOptions.ts`: add optional overlay series generation.
- Modify `frontend/src/pages/chartOptions.test.ts`: add failing tests for overlay series.
- Modify `frontend/src/pages/StrategyPage.tsx`: add `缠论结构` checkbox, pass overlay to chart, and render structure summary.
- Modify `frontend/src/pages/StrategyPage.test.tsx`: add failing tests for toggle and summary rendering.
- Modify `docs/context/pending-features.md`: remove completed B item and set C as the next recommendation.
- Create `docs/qa/2026-06-19-chan-structure-overlays-qa.md`: record tests, benchmark backtests, and browser screenshot evidence.

## Task 1: Backend RED Test

**Files:**
- Modify: `tests/test_research_signals.py`

- [ ] Add `test_preview_includes_chan_structure_overlay_payload` using the same buy-friendly bar shape already covered by Chan structure tests:

```python
def test_preview_includes_chan_structure_overlay_payload():
    closes = [10.0, 9.4, 10.4, 11.6, 10.8, 10.1, 11.5, 12.8, 12.6, 12.5, 12.3, 12.8] * 6

    preview = preview_research_signals(_bars(closes), min_bars=12, lookback=72)

    assert preview.chan_structure is not None
    assert preview.chan_structure.fractal_count > 0
    assert preview.chan_structure.stroke_count > 0
    assert preview.chan_structure.pivot_count > 0
    assert preview.chan_structure.fractals[0].kind in {"top", "bottom"}
    assert preview.chan_structure.strokes[0].start_day is not None
    assert preview.chan_structure.pivots[0].start_day is not None
    assert any(signal.kind.startswith("CHAN_STRUCT_") for signal in preview.chan_structure.signals)
```

- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_preview_includes_chan_structure_overlay_payload -q
```

Expected: fail because `ResearchSignalPreview` has no `chan_structure` attribute.

## Task 2: Backend Implementation

**Files:**
- Modify: `src/ai_trade_system/research/models.py`
- Modify: `src/ai_trade_system/research/service.py`
- Test: `tests/test_research_signals.py`

- [ ] Add frozen dataclasses:

```python
@dataclass(frozen=True)
class ChanFractalOverlay:
    index: int
    trading_day: date
    kind: str
    price: float
    high: float
    low: float


@dataclass(frozen=True)
class ChanStrokeOverlay:
    direction: str
    start_index: int
    end_index: int
    start_day: date
    end_day: date
    start_price: float
    end_price: float
    high: float
    low: float


@dataclass(frozen=True)
class ChanPivotOverlay:
    start_index: int
    end_index: int
    start_day: date
    end_day: date
    low: float
    high: float


@dataclass(frozen=True)
class ChanStructureOverlay:
    fractal_count: int
    stroke_count: int
    pivot_count: int
    latest_signal_kind: str | None
    latest_signal_title: str | None
    fractals: list[ChanFractalOverlay] = field(default_factory=list)
    strokes: list[ChanStrokeOverlay] = field(default_factory=list)
    pivots: list[ChanPivotOverlay] = field(default_factory=list)
    signals: list[ResearchSignal] = field(default_factory=list)
```

- [ ] Add `chan_structure: ChanStructureOverlay | None = None` to `ResearchSignalPreview`.
- [ ] In `service.py`, import `scan_chan_structure` and overlay models.
- [ ] Add helper functions `_empty_chan_structure_overlay` and `_chan_structure_overlay(result)`.
- [ ] Include empty overlay data in `_empty_preview` and insufficient-bars previews.
- [ ] For valid bars, run `scan_chan_structure(frame, min_stroke_bars=5, min_rebound_pct=0.03, lookback=lookback)` and attach the overlay to the returned preview.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_preview_includes_chan_structure_overlay_payload -q
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
```

Expected: both commands pass.

## Task 3: Frontend RED Tests

**Files:**
- Modify: `frontend/src/pages/chartOptions.test.ts`
- Modify: `frontend/src/pages/StrategyPage.test.tsx`

- [ ] Add `priceOption renders Chan structure overlay series`:

```tsx
const chanStructure = {
  fractal_count: 2,
  stroke_count: 1,
  pivot_count: 1,
  latest_signal_kind: "CHAN_STRUCT_BUY_T3",
  latest_signal_title: "缠论三买",
  fractals: [
    { index: 0, trading_day: "2024-01-02", kind: "bottom", price: 9.8, high: 11.2, low: 9.8 },
    { index: 1, trading_day: "2024-01-03", kind: "top", price: 11.1, high: 11.1, low: 10.2 }
  ],
  strokes: [
    {
      direction: "up",
      start_index: 0,
      end_index: 1,
      start_day: "2024-01-02",
      end_day: "2024-01-03",
      start_price: 9.8,
      end_price: 11.1,
      high: 11.1,
      low: 9.8
    }
  ],
  pivots: [{ start_index: 0, end_index: 1, start_day: "2024-01-02", end_day: "2024-01-03", low: 10.1, high: 10.8 }],
  signals: [
    {
      trading_day: "2024-01-03",
      symbol: "000001",
      exchange: "SZSE",
      kind: "CHAN_STRUCT_BUY_T3",
      action: "buy",
      price: 10.8,
      strength: 0.78,
      score: 44,
      title: "缠论三买",
      reason: "向上离开中枢后的回抽未跌回中枢上沿",
      tags: ["chan", "structure"]
    }
  ]
};

const option = priceOption(bars, [], chanStructure);
const series = option.series as Array<Record<string, unknown>>;

expect(series.map((item) => item.name)).toEqual(expect.arrayContaining(["顶分型", "底分型", "缠论笔", "缠论中枢", "结构买点"]));
```

- [ ] Add StrategyPage test data with `researchSignals.chan_structure` and assert `显示缠论结构` is checked plus summary counts are rendered.
- [ ] Run:

```bash
cd frontend && npm test -- chartOptions.test.ts StrategyPage.test.tsx --run
```

Expected: fail because `priceOption` has no third argument and Strategy Workshop has no structure toggle/summary.

## Task 4: Frontend Implementation

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/chartOptions.ts`
- Modify: `frontend/src/pages/StrategyPage.tsx`
- Test: frontend tests

- [ ] Extend `ResearchSignalChanStructure` with arrays for `fractals`, `strokes`, `pivots`, and `signals`.
- [ ] Add optional `chan_structure?: ResearchSignalChanStructure | null` to `ResearchSignalPreview`.
- [ ] Update `priceOption(bars, signals = [], chanStructure = null)`.
- [ ] Add helper functions for top/bottom fractal scatter points, stroke line points, pivot markArea data, and structure signal markers.
- [ ] Add `showChanStructure` state in `StrategyPage`, default `true`.
- [ ] Render `显示缠论结构` checkbox in the chart toolbar.
- [ ] Reset view restores `showChanStructure` to `true`.
- [ ] Render structure counts in `ResearchSignalPanel`.
- [ ] Run:

```bash
cd frontend && npm test -- chartOptions.test.ts StrategyPage.test.tsx --run
```

Expected: pass.

## Task 5: Full Verification And Sedimentation

**Files:**
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-19-chan-structure-overlays-qa.md`

- [ ] Run:

```bash
PYTHONPATH=src python -m pytest
```

- [ ] Run:

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

- [ ] Run mandatory fixed-stock benchmark backtests for:

```text
data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv
data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv
```

- [ ] Start `./scripts/run_app.sh` if needed and browser-test the flow:

```text
http://localhost:5173 -> Strategy Workshop -> 缠论/RSI研判 -> K-line shows Chan structure overlay and toggle can hide/show it.
```

- [ ] Capture screenshot outside the repo and record its path in QA docs.
- [ ] Remove the completed B pending item and set the next recommended feature to the deeper Chan core analyzer.
- [ ] Commit implementation and docs.
