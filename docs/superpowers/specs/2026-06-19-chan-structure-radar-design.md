# Chan Structure Radar Design

Date: 2026-06-19

## Goal

Add a Signal Radar scoring mode that ranks local CSV-backed candidates with the existing `research.chan_structure` analyzer, so `ChanStructureStrategy` can be inspected beyond single-symbol backtests.

This is the A-slice of the Chan roadmap:

- A: Signal Radar `chan_structure` scoring mode.
- B: Strategy Workshop K-line overlays for fractals, strokes, pivots, and T2/T3 signals.
- C: Deeper Chan analyzer with segment-level structure, recursive pivots, and divergence-style confirmation.

Only A is in scope for this implementation.

## Scope

Backend:

- Extend `/api/research/signals/batch` to accept `score_mode="chan_structure"`.
- Reuse `scan_chan_structure` from `src/ai_trade_system/research/chan_structure.py`.
- Return the same batch row shape already used by `research` and `volume_momentum`, with `score`, `latest_signal`, `preview`, `blockers`, and `status`.
- Add a small `chan_structure` diagnostic payload to the score so the frontend can show structure counts without reading internal analyzer classes.

Frontend:

- Add `缠论结构` as a Signal Radar scoring-mode option.
- Render a `缠论结构排行` title when selected.
- Show structure diagnostics in result cards and table rows, such as fractal count, stroke count, pivot count, and latest structure signal title.
- Include structure diagnostics in CSV export columns.

Verification and sedimentation:

- Add API route tests for `chan_structure` scoring.
- Add React Signal Radar tests for selecting and rendering the new scoring mode.
- Run the mandatory fixed-stock strategy benchmark for 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE`, because this work extends a shared strategy/research signal module used to inspect strategy output.
- Record QA evidence under `docs/qa/`.
- Keep B and C as pending follow-up features.

## Behavior

For each scanned candidate with a local managed CSV:

1. Load bars through the existing managed CSV path.
2. Run `scan_chan_structure(bars_to_frame(bars), min_stroke_bars=5, min_rebound_pct=0.03, lookback=request.lookback)`.
3. Produce a score payload:
   - `total_score`: analyzer `chan_score`.
   - `direction`: `bullish` if score is positive, `bearish` if negative, otherwise `neutral`.
   - `confidence`: scaled from absolute score, capped at `1.0`.
   - `chan_score`: analyzer `chan_score`.
   - `rsi_score`: `0`.
   - `summary`: Chinese summary of fractal/stroke/pivot counts and latest signal state.
   - `chan_structure`: diagnostic payload.
4. Use the latest analyzer signal, if present, as `latest_signal`.
5. If no signal is present, return a blocker-style reason such as `NO_CHAN_STRUCTURE_SIGNAL` while keeping the row `scanned`.

Ranking should follow existing research behavior: scanned rows first, then sort by absolute `total_score` descending.

## Out Of Scope

- No chart overlay rendering.
- No changes to `ChanStructureStrategy` trading behavior or default parameters.
- No strategy tuning.
- No full recursive Chan implementation.
- No live trading behavior.

## Acceptance Criteria

- API accepts `score_mode="chan_structure"` and returns ranked rows from local CSV candidates.
- The response includes `score.chan_structure` diagnostics and latest structure signal data when available.
- React Signal Radar can select the new mode and sends `score_mode: "chan_structure"`.
- React renders the `缠论结构排行` title and visible structure diagnostics.
- Fixed benchmark backtests for 中芯国际 and 五粮液 are run and recorded for final delivery.
