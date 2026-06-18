# Chan Core Deepening Design

Date: 2026-06-19

## Goal

Deepen the existing daily-bar Chan structure analyzer toward a fuller Chan strategy by adding segment-level structure, first-cut recursive pivots, and divergence/confirmation signals that can flow through research preview, chart overlays, Signal Radar diagnostics, and `ChanStructureStrategy` backtests.

This is the C-slice after:

- A: Signal Radar `chan_structure` ranking.
- B: Strategy Workshop K-line overlays for fractals, strokes, pivots, and T2/T3 signals.
- C: Segment-level structure, recursive pivots, and divergence/confirmation signals.

This is still not a complete multi-timeframe Chan engine. It is a pure-Python, single-symbol, daily-bar step that makes the requested final state more true while keeping every addition testable.

## Scope

Backend analyzer:

- Extend `src/ai_trade_system/research/chan_structure.py`.
- Keep existing containment, fractal, stroke, pivot, and T2/T3 behavior compatible.
- Add `ChanSegment` derived from stroke triples.
- Add `ChanRecursivePivot` for both stroke-level and segment-level overlapping zones.
- Add `ChanDivergence` that compares same-direction segments by price extreme and normalized energy.
- Add new research signals:
  - `CHAN_STRUCT_BUY_T1_DIVERGENCE`
  - `CHAN_STRUCT_SELL_T1_DIVERGENCE`
  - `CHAN_STRUCT_BUY_CONFIRM`
  - `CHAN_STRUCT_SELL_CONFIRM`
- Keep signals deterministic, long-only compatible, and scored so confirmation ranks above T2/T3 when present.

API and frontend observability:

- Extend research preview `chan_structure` overlay payload with segment, recursive pivot, and divergence counts plus optional arrays.
- Extend Signal Radar diagnostics with those counts.
- Extend React types and K-line overlay rendering to include a `缠论线段` line series and `递归中枢` markArea series when present.
- Keep existing fractal/stroke/pivot overlay behavior intact.

Strategy behavior:

- `ChanStructureStrategy` continues to call `scan_chan_structure`.
- It can trade the new confirmation/divergence signals through the existing score filter and duplicate-emission guard.
- No threshold tuning in this slice.

Verification and sedimentation:

- TDD tests for segments, recursive pivots, divergence, confirmation signals, strategy emission, and chart option output.
- Full Python and frontend verification.
- Mandatory fixed-stock benchmark backtests for 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE`.
- Browser QA on the React Strategy Workshop when the overlay surface changes.
- QA evidence under `docs/qa/`.
- Pending list should keep the larger full-Chan objective active after this slice.

## First-Cut Rules

### Segment

Build segments from stroke triples:

- Use every three consecutive strokes.
- A valid segment exists when the first and third strokes share the same direction.
- Direction is that shared direction.
- Start is the first stroke start fractal.
- End is the third stroke end fractal.
- Range is the high/low over the three strokes.
- Energy is normalized movement: `abs(end.price - start.price) / max(1, end.index - start.index)`.
- A segment is marked broken when the next opposite segment violates its range:
  - Up segment broken if the next down segment falls below its low.
  - Down segment broken if the next up segment rises above its high.

This is a conservative implementation of the "line segment after stroke" layer, not the final full Chan segment-splitting algorithm.

### Recursive Pivot

Build recursive pivots from overlapping triples at two levels:

- Stroke-level: keep existing `pivots` as compatibility output.
- Segment-level: use every three consecutive segments whose ranges overlap.
- Add `level`, `component_count`, start/end indexes, start/end trading days, low, high, and direction.

This gives the analyzer a recursive structure channel while preserving old pivot contracts.

### Divergence

Compare the latest segment with the previous same-direction segment:

- Bottom divergence: latest down segment makes a lower low but has lower normalized energy than the previous down segment.
- Top divergence: latest up segment makes a higher high but has lower normalized energy than the previous up segment.
- Record reference/current energy and price extreme.

This first version uses price-derived energy rather than MACD area so it remains pure Python and does not introduce a new indicator dependency. MACD/volume divergence can be added later as a stronger confirmation source.

### Confirmation Signals

Generate confirmation signals after divergence:

- Buy divergence signal: `CHAN_STRUCT_BUY_T1_DIVERGENCE`, score `36`.
- Sell divergence signal: `CHAN_STRUCT_SELL_T1_DIVERGENCE`, score `-36`.
- Buy confirmation signal: `CHAN_STRUCT_BUY_CONFIRM`, score `52`, when a bottom divergence exists and the latest close rebounds above the divergent segment end by `min_rebound_pct`.
- Sell confirmation signal: `CHAN_STRUCT_SELL_CONFIRM`, score `-52`, when a top divergence exists and the latest close falls below the divergent segment end by `min_rebound_pct`.

Confirmation signals intentionally rank above T2/T3 in `ChanStructureStrategy`, while raw divergence remains below confirmation.

## Out Of Scope

- Intraday or multi-timeframe interval nesting.
- Exact original Chan segment splitting edge cases.
- MACD area/zero-axis based divergence.
- Strategy threshold optimization.
- Live trading.
- Claiming full Chan completion.

## Acceptance Criteria

- `scan_chan_structure` returns non-empty `segments`, `recursive_pivots`, and `divergences` for explicit synthetic structures.
- The analyzer emits T1 divergence and confirmation research signals on current-bar scenarios.
- `ChanStructureStrategy` can trade a confirmation signal through the existing backtest path.
- Research preview and Signal Radar diagnostics expose segment, recursive pivot, and divergence counts.
- Strategy Workshop chart option supports `缠论线段` and `递归中枢` overlay series.
- Full verification and fixed benchmark backtests are recorded in QA docs.
