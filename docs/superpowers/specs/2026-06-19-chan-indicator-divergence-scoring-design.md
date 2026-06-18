# Chan Indicator Divergence Scoring Design

## Goal

Deepen the Chan structure analyzer by adding indicator-backed divergence strength to existing segment-level divergence and confirmation signals.

## Scope

This slice keeps the existing Chan segment, recursive pivot, and signal kinds. It adds MACD and volume evidence to divergence records, signal reasons, signal strength, and score calculation. It does not tune strategy parameters or add live-trading behavior.

## Current State

`scan_chan_structure` already normalizes contained K-lines, detects fractals and strokes, builds strict non-overlapping segments, links recursive pivots, detects segment energy divergence, and emits divergence plus confirmation signals. Current divergence detection only compares segment price-extreme progress with unit segment energy. Confirmation only checks price rebound or breakdown against `min_rebound_pct`.

## Design

Each segment divergence will continue to require the existing Chan condition:

- Bottom divergence: a down segment makes a lower low while segment energy is lower than the previous down segment.
- Top divergence: an up segment makes a higher high while segment energy is lower than the previous up segment.

After that structural condition is met, the analyzer will calculate three bounded evidence components:

- `macd_strength`: compares absolute MACD histogram pressure in the current segment with the reference segment. Weaker downside/upside MACD pressure strengthens the divergence.
- `volume_strength`: compares average volume in the current segment with the reference segment. Lower participation on the new extreme strengthens the divergence.
- `confirmation_score`: combines price repair/breakdown progress, MACD support, volume support, and whether the segment was confirmed by a break/rebuild stroke.

The divergence dataclass and API overlay will expose these fields. Signal scores will become dynamic instead of fixed constants:

- Divergence watch signal score starts from the structural direction and is adjusted by MACD and volume evidence.
- Confirmation signal score adds the confirmation component and keeps the same buy/sell direction semantics.
- Strength is derived from absolute score, capped to `0.95`.

## Data Flow

`scan_chan_structure(frame)` will compute a compact indicator context from the same frame used for K-line analysis, keyed by normalized K-line index. `_detect_divergences` will receive that context and attach indicator evidence to each `ChanDivergence`. `_divergence_signals` will use the enriched divergence to generate reason text and dynamic scores.

Existing consumers remain unchanged at the call site:

- `ChanStructureStrategy` continues to read `result.signals`.
- `preview_research_signals` serializes the expanded overlay.
- Signal Radar `chan_structure` mode continues to rank by `result.chan_score`.

## Acceptance Criteria

- A lower-low down-segment divergence with weaker MACD histogram pressure and lower volume exposes positive `macd_strength`, positive `volume_strength`, and a stronger buy confirmation score than the base divergence score.
- A higher-high up-segment divergence with weaker MACD histogram pressure and lower volume exposes the same evidence fields with sell polarity.
- API overlay serializes the new divergence evidence fields.
- Frontend TypeScript types match the Python overlay contract, including segment stroke indexes on `ChanSegmentOverlay`.
- Full Python tests, frontend tests, frontend build, fixed 中芯国际 and 五粮液 benchmark backtests, and React browser QA are run before delivery.

## Non-Goals

- No parameter tuning for `ChanStructureStrategy`.
- No new live-trading or broker gateway behavior.
- No UI redesign beyond type/fixture compatibility.
