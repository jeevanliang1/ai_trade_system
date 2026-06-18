# Chan Structure Overlays Design

Date: 2026-06-19

## Goal

Add Chan structure overlays to the Strategy Workshop K-line chart so a single symbol can be inspected with visible fractals, strokes, pivots, and T2/T3 signals after running the existing `缠论/RSI研判` preview.

This is the B-slice of the Chan roadmap:

- A: Signal Radar `chan_structure` scoring mode.
- B: Strategy Workshop K-line overlays for fractals, strokes, pivots, and T2/T3 signals.
- C: Deeper Chan analyzer with segment-level structure, recursive pivots, and divergence-style confirmation.

Only B is in scope for this implementation.

## Scope

Backend:

- Extend `ResearchSignalPreview` with optional `chan_structure` overlay data.
- Reuse `scan_chan_structure` from `src/ai_trade_system/research/chan_structure.py`.
- Serialize analyzer output into chart-ready data:
  - `fractals`: index, trading day, kind, price, high, low.
  - `strokes`: direction, start/end indexes, start/end trading days, start/end prices, high, low.
  - `pivots`: start/end indexes, start/end trading days, low, high.
  - `signals`: existing research signal objects for T2/T3 structure signals.
  - counts and latest signal summary.
- Keep `/api/research/signals/preview` as the only Strategy Workshop research preview endpoint.

Frontend:

- Extend `ResearchSignalPreview` typing with a `chan_structure` payload.
- Extend `priceOption` with a third optional overlay argument while preserving current callers.
- Render overlays as ECharts series:
  - top fractals and bottom fractals as separate scatter series.
  - strokes as a line series connecting stroke endpoints.
  - pivots as translucent markArea boxes.
  - structure buy/sell signals as separate scatter markers.
- Add a Strategy Workshop toolbar checkbox labeled `缠论结构`.
- Pass overlays only when the checkbox is enabled and research preview data has structure details.
- Reset view should restore both strategy signal markers and Chan structure overlays.
- Show compact structure counts in the research preview panel.

Verification and sedimentation:

- Add backend tests for preview payload structure.
- Add frontend chart option tests for overlay series.
- Add Strategy Workshop render tests for the overlay toggle and structure summary.
- Run the mandatory fixed-stock benchmark backtests for 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE`, because this changes a strategy research/inspection workflow.
- Record QA evidence under `docs/qa/`.
- Remove the B item from `docs/context/pending-features.md` after completion and keep C as the next recommended feature.

## Behavior

When Strategy Workshop calls `缠论/RSI研判`:

1. The backend loads the selected CSV through the existing settings path.
2. `preview_research_signals` continues to run lightweight Chan and enhanced RSI preview exactly as before.
3. For valid input with enough bars, the same preview also runs `scan_chan_structure`.
4. The response includes `chan_structure` with structural objects and a human-readable summary.
5. The frontend stores the preview in existing platform state.
6. `StrategyPage` passes `state.researchSignals.chan_structure` to `priceOption` only when `缠论结构` is enabled.
7. The K-line chart legend exposes the overlay series names so users can inspect or hide them from ECharts if needed.

For insufficient or empty input, `chan_structure` should still be present with empty arrays and zero counts. This keeps the frontend simple and makes blockers visible without null checks throughout the chart code.

## Out Of Scope

- No changes to `ChanStructureStrategy` trading behavior or default parameters.
- No strategy threshold tuning.
- No recursive Chan segment implementation.
- No new standalone research preview endpoint.
- No live trading behavior.
- No changes to Signal Radar ranking behavior from A.

## Acceptance Criteria

- `/api/research/signals/preview` returns `chan_structure` with non-empty fractals, strokes, pivots, and T2/T3 signals for a Chan-structure-friendly bar sequence.
- Existing research preview score and signal behavior remains compatible with current tests.
- `priceOption` returns overlay series for fractals, strokes, pivots, and structure buy/sell signals when a Chan overlay is supplied.
- Strategy Workshop exposes a `缠论结构` checkbox, passes overlay data to the chart, and renders structure counts in the research panel.
- Fixed benchmark backtests for 中芯国际 and 五粮液 are run and recorded for final delivery.
