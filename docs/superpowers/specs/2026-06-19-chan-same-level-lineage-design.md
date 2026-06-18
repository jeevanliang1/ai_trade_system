# Chan Same-Level Lineage Design

## Goal

Deepen `research.chan_structure` so Chan structure outputs carry explicit same-level decomposition, pivot relationship, and buy/sell point lineage that `ChanStructureStrategy`, API overlays, and React diagnostics can inspect without re-parsing free-form Chinese reason text.

## Context

The analyzer already builds contained K-lines, fractals, strokes, strict segments, recursive pivots, indicator-backed divergence, T1 watch/confirm signals, T2/T3 signals, and strategy-side watch arming. The remaining gap is traceability: downstream consumers can see a signal kind and reason, but not a stable structure identity or hierarchy for first/second/third buy-sell points.

## Behavioral Contract

1. `ResearchSignal` gets an optional `metadata` mapping with JSON-safe primitive values.
2. Chan structure signals populate metadata keys:
   - `level`: the structure level used for the signal, such as `segment`, `stroke`, or `fractal`.
   - `point_type`: `first-buy`, `first-sell`, `second-buy`, `second-sell`, `third-buy`, or `third-sell`.
   - `pivot_relation`: a stable English relation token such as `inside-segment-pivot`, `higher-low-repair`, or `pullback-above-pivot-high`.
   - `lineage`: a compact deterministic chain, for example `segment:0-4->segment:5-9` or `pivot:1-7:leave-retest`.
3. `ChanSegment` carries same-level identity:
   - `level="segment"`
   - `sequence_index`
   - `lineage_id`, derived from the source stroke indexes.
4. `ChanSegmentOverlay` and frontend `ChanSegmentOverlay` expose the same-level fields.
5. Human-readable signal reasons include a short hierarchy/lineage suffix so existing UI surfaces become more explainable without a separate UI redesign.
6. Existing signal kinds, default strategy parameters, and trading behavior remain compatible unless richer analyzer metadata naturally changes sort ties or reason text.

## Non-Goals

- No strategy threshold tuning in this slice.
- No new frontend controls or layout redesign.
- No live trading integration.
- No full formal Chan parser; this remains a practical daily-bar approximation that is testable through the current research/backtest pipeline.

## Verification

- TDD tests must first fail because metadata and segment identity do not exist.
- Python tests must cover:
  - segment same-level sequence and lineage IDs;
  - T1 divergence/confirmation metadata;
  - T2/T3 point metadata and reason suffix;
  - overlay payload exposing segment identity fields.
- Fixed 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE` benchmark backtests must be rerun and recorded because analyzer signal output changes.
- Full verification before delivery:
  - `PYTHONPATH=src python -m pytest`
  - `cd frontend && npm test -- --run`
  - `cd frontend && npm run build`
  - `git diff --check`
  - React browser QA screenshot from `./scripts/run_app.sh`
