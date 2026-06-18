# Chan Core Deepening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add segment-level Chan structure, recursive pivots, and divergence/confirmation signals to the existing Chan analyzer and strategy path.

**Architecture:** Extend `research.chan_structure` in place so existing callers keep working while new fields become available. Keep API/frontend additions additive: old fractal/stroke/pivot contracts remain valid, new segment/recursive-pivot/divergence data is optional for React and diagnostic consumers.

**Tech Stack:** Python dataclasses, pandas-backed research frames, pytest, TypeScript/Vitest, ECharts option objects.

---

## File Structure

- Modify `src/ai_trade_system/research/chan_structure.py`: add `ChanSegment`, `ChanRecursivePivot`, `ChanDivergence`, builders, and new signals.
- Modify `src/ai_trade_system/research/models.py`: add overlay dataclasses and optional arrays/counts.
- Modify `src/ai_trade_system/research/service.py`: serialize new overlay fields.
- Modify `src/ai_trade_system/api/service.py`: add new Signal Radar diagnostics counts.
- Modify `src/ai_trade_system/strategies/popular.py`: keep parameters but allow new signals through existing strategy logic.
- Modify `tests/test_research_signals.py`: RED/GREEN analyzer and preview coverage.
- Modify `tests/test_builtin_popular_strategies.py`: RED/GREEN strategy emission coverage.
- Modify `frontend/src/types.ts`: add segment, recursive pivot, and divergence overlay types.
- Modify `frontend/src/pages/chartOptions.ts`: add `缠论线段` and `递归中枢` series.
- Modify `frontend/src/pages/chartOptions.test.ts`: RED/GREEN chart option coverage.
- Modify `docs/context/pending-features.md`: update completion state and keep full-Chan follow-up active.
- Create `docs/qa/2026-06-19-chan-core-deepening-qa.md`: record TDD, full verification, fixed benchmarks, and browser QA.

## Task 1: Analyzer RED Tests

**Files:**
- Modify: `tests/test_research_signals.py`

- [ ] Add helper:

```python
def _deep_chan_price_ranges() -> list[tuple[float, float]]:
    return [
        (11.0, 10.0), (9.5, 9.0), (10.0, 9.5), (10.5, 10.0), (11.0, 10.5), (11.5, 11.0), (12.0, 11.5), (13.0, 12.0),
        (12.4, 11.6), (12.0, 11.2), (11.6, 10.8), (11.2, 10.4), (10.8, 10.2), (10.5, 10.0), (11.0, 10.4), (11.6, 11.0),
        (12.2, 11.6), (12.8, 12.2), (13.3, 12.7), (14.0, 13.0), (13.5, 12.8), (13.2, 12.6), (12.9, 12.4), (12.7, 12.2),
        (12.6, 12.1), (12.5, 12.0), (13.2, 12.7), (13.6, 13.1), (13.9, 13.5), (14.2, 13.8), (13.9, 13.4), (13.5, 13.0),
        (13.0, 12.5), (12.5, 12.0), (12.1, 11.7), (11.8, 11.4), (12.0, 11.7), (12.3, 11.9), (12.7, 12.3), (13.0, 12.6),
        (12.8, 12.4), (12.4, 12.0), (12.0, 11.6), (11.6, 11.2), (11.3, 10.9), (11.1, 10.7), (11.5, 11.0), (12.0, 11.5),
    ]
```

- [ ] Add `test_chan_structure_builds_segments_recursive_pivots_and_divergence`:

```python
def test_chan_structure_builds_segments_recursive_pivots_and_divergence():
    bars = [_bar(index, (high + low) / 2, high=high, low=low) for index, (high, low) in enumerate(_deep_chan_price_ranges())]

    result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=5, min_rebound_pct=0.02)

    assert result.segments
    assert result.recursive_pivots
    assert any(pivot.level == "segment" for pivot in result.recursive_pivots)
    assert result.divergences
    assert any(signal.kind in {"CHAN_STRUCT_BUY_T1_DIVERGENCE", "CHAN_STRUCT_BUY_CONFIRM", "CHAN_STRUCT_SELL_T1_DIVERGENCE", "CHAN_STRUCT_SELL_CONFIRM"} for signal in result.signals)
```

- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_builds_segments_recursive_pivots_and_divergence -q
```

Expected: fail with `AttributeError` because `ChanStructureResult` has no `segments`.

## Task 2: Analyzer Implementation

**Files:**
- Modify: `src/ai_trade_system/research/chan_structure.py`
- Test: `tests/test_research_signals.py`

- [ ] Add dataclasses `ChanSegment`, `ChanRecursivePivot`, and `ChanDivergence`.
- [ ] Extend `ChanStructureResult` with `segments`, `recursive_pivots`, and `divergences`.
- [ ] Add `_build_segments(strokes)`.
- [ ] Add `_build_recursive_pivots(strokes, segments)`.
- [ ] Add `_detect_divergences(segments)`.
- [ ] Add `_divergence_signals(divergences, latest, symbol, exchange, min_rebound_pct)`.
- [ ] Add those signals before T2/T3 sorting in `_structure_signals`.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_builds_segments_recursive_pivots_and_divergence -q
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
```

Expected: pass.

## Task 3: Preview/API RED and GREEN

**Files:**
- Modify: `tests/test_research_signals.py`
- Modify: `src/ai_trade_system/research/models.py`
- Modify: `src/ai_trade_system/research/service.py`
- Modify: `src/ai_trade_system/api/service.py`

- [ ] Extend `test_preview_includes_chan_structure_overlay_payload` to assert:

```python
assert preview.chan_structure.segment_count > 0
assert preview.chan_structure.recursive_pivot_count > 0
assert preview.chan_structure.divergence_count > 0
assert preview.chan_structure.segments
assert preview.chan_structure.recursive_pivots
```

- [ ] Run the preview test and confirm RED.
- [ ] Add overlay dataclasses for segment, recursive pivot, and divergence.
- [ ] Serialize analyzer fields into preview overlay.
- [ ] Extend API batch diagnostics with `segment_count`, `recursive_pivot_count`, and `divergence_count`.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
PYTHONPATH=src python -m pytest tests/test_api_routes.py -q
```

Expected: pass.

## Task 4: Strategy RED and GREEN

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`
- Modify: `src/ai_trade_system/strategies/popular.py` only if required by the tests

- [ ] Add `test_chan_structure_strategy_can_trade_confirmation_signal` using `_deep_chan_price_ranges` copied into this test file.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_can_trade_confirmation_signal -q
```

Expected: fail before analyzer implementation, then pass after new confirmation signals flow through the existing score filter.

## Task 5: Frontend RED and GREEN

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/chartOptions.ts`
- Modify: `frontend/src/pages/chartOptions.test.ts`

- [ ] Extend chart test to include `segments` and `recursive_pivots` in `chanStructure`.
- [ ] Assert series names include `缠论线段` and `递归中枢`.
- [ ] Run:

```bash
cd frontend && npm test -- chartOptions.test.ts --run
```

Expected: fail before chart option implementation, pass after adding additive series.

## Task 6: Verification, QA, and Commit

**Files:**
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-19-chan-core-deepening-qa.md`

- [ ] Run:

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

- [ ] Run fixed benchmark backtests on:

```text
data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv
data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv
```

- [ ] Run Browser QA on Strategy Workshop if the React chart overlay changed.
- [ ] Update QA and pending docs.
- [ ] Commit with:

```bash
git add <changed files>
git commit -m "feat: deepen chan structure analyzer"
```
