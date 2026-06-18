# Chan Strict Segment Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace overlapping sliding-window Chan segments with a stricter non-overlapping split/break/rebuild model.

**Architecture:** Keep the public analyzer entrypoint `scan_chan_structure` unchanged. Add segment metadata to the existing dataclasses and overlay payloads, then replace `_build_segments` with stateful construction that extends active segments and restarts from break strokes.

**Tech Stack:** Python dataclasses, pytest, TypeScript/Vitest, existing React/ECharts overlay types.

---

## File Structure

- Modify `src/ai_trade_system/research/chan_structure.py`: add segment metadata and stateful `_build_segments`.
- Modify `src/ai_trade_system/research/models.py`: add metadata fields to `ChanSegmentOverlay`.
- Modify `src/ai_trade_system/research/service.py`: serialize the new segment metadata.
- Modify `frontend/src/types.ts`: add the new segment metadata to `ChanSegmentOverlay`.
- Modify `frontend/src/pages/chartOptions.test.ts`: assert the new fields are accepted in chart overlay fixtures.
- Modify `tests/test_research_signals.py`: add RED tests for non-overlap, break metadata, segment-level recursive pivots, and overlay metadata.
- Create `docs/qa/2026-06-19-chan-strict-segment-rules-qa.md`: record TDD, verification, fixed benchmarks, and browser QA.
- Modify `docs/context/pending-features.md`: move this slice to baseline and keep the next full-Chan item active.

## Task 1: Analyzer RED Tests

**Files:**
- Modify: `tests/test_research_signals.py`

- [ ] **Step 1: Add strict segment assertions**

Add a test after `test_chan_structure_builds_segments_recursive_pivots_and_divergence`:

```python
def test_chan_structure_builds_non_overlapping_segments_from_breaks():
    bars = [_bar(index, (high + low) / 2, high=high, low=low) for index, (high, low) in enumerate(_deep_chan_price_ranges())]

    result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=4, min_rebound_pct=0.02)

    segment_spans = [(segment.start.index, segment.end.index) for segment in result.segments]
    assert len(segment_spans) >= 3
    assert all(left_end <= right_start for (_, left_end), (right_start, _) in zip(segment_spans, segment_spans[1:]))
    assert any(segment.broken_by_next and segment.break_stroke_index is not None for segment in result.segments)
    assert all(segment.start_stroke_index <= segment.end_stroke_index for segment in result.segments)
    assert any(pivot.level == "segment" for pivot in result.recursive_pivots)
```

- [ ] **Step 2: Add overlay metadata assertion**

Extend `test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences`:

```python
assert overlay.segments[0].start_stroke_index == result.segments[0].start_stroke_index
assert any(segment.break_stroke_index is not None for segment in overlay.segments)
```

- [ ] **Step 3: Verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_builds_non_overlapping_segments_from_breaks tests/test_research_signals.py::test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences -q
```

Expected: fail with `AttributeError` for missing `start_stroke_index` or `break_stroke_index`, and/or fail because current segments overlap.

## Task 2: Stateful Segment Builder

**Files:**
- Modify: `src/ai_trade_system/research/chan_structure.py`
- Test: `tests/test_research_signals.py`

- [ ] **Step 1: Extend `ChanSegment`**

Add fields:

```python
start_stroke_index: int = 0
end_stroke_index: int = 0
break_stroke_index: int | None = None
```

- [ ] **Step 2: Replace `_build_segments` with stateful construction**

Implement helpers:

```python
def _candidate_segment(strokes: list[ChanStroke], start_index: int) -> ChanSegment | None:
    window = strokes[start_index : start_index + 3]
    if len(window) < 3:
        return None
    first, second, third = window
    if first.direction != third.direction:
        return None
    return _segment_from_strokes(window, start_index, start_index + 2)


def _segment_from_strokes(strokes: list[ChanStroke], start_index: int, end_index: int, *, broken_by_next: bool = False, break_stroke_index: int | None = None) -> ChanSegment:
    start = strokes[0].start
    end = strokes[-1].end
    index_span = max(1, end.index - start.index)
    return ChanSegment(
        start=start,
        end=end,
        direction=strokes[0].direction,
        high=max(stroke.high for stroke in strokes),
        low=min(stroke.low for stroke in strokes),
        stroke_count=len(strokes),
        energy=round(abs(end.price - start.price) / index_span, 6),
        broken_by_next=broken_by_next,
        start_stroke_index=start_index,
        end_stroke_index=end_index,
        break_stroke_index=break_stroke_index,
    )
```

Update `_build_segments` so it:

- searches for the next candidate from `cursor`;
- extends the candidate while same-direction strokes make progress;
- locks the segment with `break_stroke_index` when an opposite stroke violates the protected extreme;
- appends the locked/open segment;
- resumes at the break stroke index when broken, otherwise at `end_stroke_index + 1`.

- [ ] **Step 3: Run GREEN checks**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_builds_non_overlapping_segments_from_breaks tests/test_research_signals.py::test_chan_structure_builds_segments_recursive_pivots_and_divergence -q
```

Expected: both pass.

## Task 3: Overlay Metadata

**Files:**
- Modify: `src/ai_trade_system/research/models.py`
- Modify: `src/ai_trade_system/research/service.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/chartOptions.test.ts`
- Test: `tests/test_research_signals.py`, `frontend/src/pages/chartOptions.test.ts`

- [ ] **Step 1: Add fields to `ChanSegmentOverlay`**

Python fields:

```python
start_stroke_index: int
end_stroke_index: int
break_stroke_index: int | None
```

TypeScript fields:

```typescript
start_stroke_index: number;
end_stroke_index: number;
break_stroke_index: number | null;
```

- [ ] **Step 2: Serialize fields**

In `_chan_structure_overlay`, pass:

```python
start_stroke_index=segment.start_stroke_index,
end_stroke_index=segment.end_stroke_index,
break_stroke_index=segment.break_stroke_index,
```

- [ ] **Step 3: Update frontend test fixture**

Add the three fields to the sample `segments` object in `frontend/src/pages/chartOptions.test.ts`.

- [ ] **Step 4: Run checks**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
cd frontend && npm test -- --run src/pages/chartOptions.test.ts
```

Expected: pass.

## Task 4: Verification, Benchmark, QA, Commit

**Files:**
- Create: `docs/qa/2026-06-19-chan-strict-segment-rules-qa.md`
- Modify: `docs/context/pending-features.md`

- [ ] **Step 1: Run full verification**

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

- [ ] **Step 2: Run fixed benchmark backtests**

Run `ChanStructureStrategy` with default parameters on:

```text
data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv
data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv
```

Record rows, dates, final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor.

- [ ] **Step 3: Browser QA**

Run:

```bash
./scripts/run_app.sh
```

Open `http://127.0.0.1:5173/`, click `缠论/RSI研判`, verify chart canvases render, `显示缠论结构` can toggle, console warn/error logs are empty, and save screenshot to:

```text
/tmp/ai_trade_system_chan_strict_segment_rules.png
```

- [ ] **Step 4: Update sedimentation**

Update `docs/context/pending-features.md`:

- add this strict segment slice to the implemented baseline;
- remove the corresponding pending item;
- keep MACD/volume divergence as the next recommended feature.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-06-19-chan-strict-segment-rules-design.md docs/superpowers/plans/2026-06-19-chan-strict-segment-rules.md src/ai_trade_system/research/chan_structure.py src/ai_trade_system/research/models.py src/ai_trade_system/research/service.py frontend/src/types.ts frontend/src/pages/chartOptions.test.ts tests/test_research_signals.py docs/qa/2026-06-19-chan-strict-segment-rules-qa.md docs/context/pending-features.md
git commit -m "feat: refine chan segment rules"
```
