# Chan Core V2 Design

Date: 2026-06-19

## Goal

Add a second-generation Chan core that models multi-level trend types, pivot lifecycle state, and incremental cache behavior while preserving the existing `scan_chan_structure` and `ChanStructureStrategy` trading semantics.

## Context

The current Chan structure analyzer already handles contained K-lines, fractals, strokes, simplified pivots, non-overlapping line segments, recursive stroke/segment pivots, divergence evidence, watch/confirmation signals, lineage metadata, and strategy-level filters.

Two limits now block further iteration:

- The analyzer returns structural lists but does not expose a dedicated "走势类型" layer for each level.
- Pivots are static ranges, so downstream logic cannot directly reason about lifecycle states such as forming, confirmed, extended, broken, or completed.
- `ChanStructureStrategy.on_bar` rebuilds the complete Chan structure from the retained bar window on every bar.

This slice creates V2 as an additive core layer. It must not retune defaults or intentionally change benchmark trades.

## Scope

Backend core:

- Create `src/ai_trade_system/research/chan_core_v2.py`.
- Add V2 dataclasses for:
  - multi-level trend type records;
  - pivot lifecycle records;
  - core snapshots;
  - incremental analyzer cache metadata.
- Build V2 snapshots from the existing normalized structures: strokes, segments, recursive pivots, divergences, and signals.
- Support the current two internal levels:
  - `stroke`
  - `segment`
- Classify trend type per level as:
  - `up`
  - `down`
  - `range`
  - `transition`

Analyzer integration:

- Extend `ChanStructureResult` with an additive `core_v2` field.
- Keep the existing `scan_chan_structure(...)` signature and all current fields.
- Build V2 from existing structures inside `scan_chan_structure`.
- Do not change signal names, default thresholds, strategy filters, or buy/sell rules in this slice.

Strategy cache:

- Add a reusable incremental analyzer object for strategy use.
- `ChanStructureStrategy` should append bars to the analyzer and receive the latest `ChanStructureResult`.
- First implementation can use dirty-window recomputation rather than true O(1) structural mutation.
- Cache behavior must be observable through metadata:
  - total bars received;
  - effective bars scanned after lookback;
  - update count;
  - recompute count;
  - dirty start index.

Serialization and preview:

- Add optional V2 overlay fields to `ChanStructureOverlay`.
- Expose compact summaries rather than dumping the full object graph:
  - `core_v2_trend_count`
  - `core_v2_pivot_lifecycle_count`
  - `core_v2_cache`
  - `core_v2_latest_trend`
  - `core_v2_pivot_states`

Tests and benchmark:

- Add direct unit tests for V2 trend classification and pivot lifecycle transitions.
- Add cache equivalence tests: incremental analyzer snapshots must match full `scan_chan_structure` outputs for the fields used by the strategy.
- Add a strategy test proving `ChanStructureStrategy` no longer calls full scan once per eligible bar.
- Run the fixed 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE` benchmark fixtures and record results.

## V2 Trend Type Rules

V2 trend records are derived from same-level components.

### Component Level

- `stroke` level uses `ChanStroke` components.
- `segment` level uses `ChanSegment` components.

### Direction

- If the latest confirmed component direction is `up` and the component makes a higher high or higher ending price versus the previous same-level component, classify as `up`.
- If the latest confirmed component direction is `down` and the component makes a lower low or lower ending price versus the previous same-level component, classify as `down`.
- If there is a lifecycle pivot still active and price remains inside its range, classify as `range`.
- If there are not enough components for a directional judgement, classify as `transition`.

### Phase

- `forming`: the level has fewer than three components.
- `confirmed`: a level has at least one lifecycle pivot or one non-broken segment.
- `extended`: the latest component continues the current direction beyond the previous extreme.
- `broken`: the latest component breaks the latest active pivot in the opposite direction.

## Pivot Lifecycle Rules

V2 lifecycle pivots are derived from existing recursive pivots, then enriched with state.

### Identity

Lifecycle pivots use stable lineage:

```text
core-v2:{level}:{start_index}-{end_index}
```

### State

- `forming`: fewer than three same-level components overlap. This state is represented only in snapshots when a latest partial component window exists.
- `confirmed`: at least three components overlap and produce a recursive pivot.
- `extended`: more than three components continue overlapping inside the same pivot range.
- `broken`: a later same-level component exits above or below the pivot range.
- `completed`: a broken pivot is no longer the latest active pivot for that level.

### Break Direction

- A component with `low > pivot.high` breaks a pivot upward.
- A component with `high < pivot.low` breaks a pivot downward.
- A component that still overlaps the pivot range keeps it active.

## Incremental Cache Rules

The first cache implementation is intentionally conservative:

- Store the latest bars in a bounded deque with `lookback`.
- On each update, rebuild the same window as the full scanner.
- Track cache metadata so later true incremental recompute can be added without changing callers.
- Reset the cache when the symbol or exchange changes.
- Preserve equality with `scan_chan_structure(bars_to_frame(window), ...)`.

This gives immediate strategy integration and observability while avoiding a risky partial-recompute algorithm before the lifecycle model is pinned by tests.

## Compatibility

Existing public contracts must remain valid:

- Existing tests that read `klines`, `fractals`, `strokes`, `pivots`, `segments`, `recursive_pivots`, `divergences`, `signals`, and `chan_score` should continue to pass.
- Existing `ResearchSignal.metadata` keys should not be renamed.
- Existing frontend overlay fields should remain present.
- Strategy defaults and parameter guidance should not change.

## Out Of Scope

- Full minute/day external multi-timeframe aggregation.
- Strategy parameter tuning.
- New buy/sell signal family enabled by default.
- Full original Chan recursive decomposition edge cases.
- Live trading, broker gateway behavior, or vn.py integration.

## Acceptance Criteria

- V2 trend records exist for `stroke` and `segment` levels on deep Chan samples.
- V2 pivot lifecycle records include confirmed, extended, broken, and completed states on deterministic synthetic samples.
- Incremental analyzer outputs match full scan for signal kinds, segment lineage, recursive pivot count, divergence count, and score on representative bars.
- `ChanStructureStrategy` uses the analyzer cache instead of direct per-bar full scan.
- Fixed 中芯国际 and 五粮液 benchmarks are recorded under `docs/qa/`.
- Existing backend tests pass.
- Browser QA captures the React platform if startup is available.
