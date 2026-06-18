# Chan Signal Mode Controls Design

## Goal

Expose `ChanStructureStrategy` signal-family controls so confirmation-style divergence signals, T2/T3 structure signals, and full exploratory structure signals can be benchmarked independently on the fixed 中芯国际 and 五粮液 fixtures.

## Background

The Chan core now emits several structural signal families from the same analyzer:

- T2/T3 structure signals from fractal, stroke, pivot, and rebound/rollback checks.
- Segment divergence and confirmation signals from line-segment energy, recursive pivots, MACD pressure, and volume participation evidence.

The previous default threshold tuning kept the strategy conservative by filtering lower-confidence 28-point T2/T3 churn. That made the default benchmark more stable, but it also made it hard to compare structure-only signals against confirmation-style signals without changing score thresholds manually.

## Decision

Add `signal_mode: str = "all"` to `ChanStructureStrategy`.

Supported modes:

- `confirmation`: trade only divergence/confirmation-family signals.
- `structure`: trade only T2/T3 second/third buy-sell structure signals.
- `all`: trade every Chan structure signal that passes the score threshold.

The default preserves the existing benchmark behavior by using `all` plus the existing `min_signal_score=30.0`. The score threshold remains the conservative filter for lower-confidence T2/T3 churn, while `confirmation` and `structure` allow explicit family-level research runs.

Unsupported modes should fail fast with `ValueError` so API/UI callers do not silently run a different strategy than requested.

## Scope

This slice changes only the built-in strategy wrapper and strategy metadata. It does not change core Chan detection, segment construction, recursive pivots, divergence scoring, backtest accounting, or live-trading behavior.

## Acceptance Criteria

- `ChanStructureStrategy("000001")` stores `signal_mode == "all"`.
- `signal_mode="confirmation"` suppresses T2/T3-only signals even when the score threshold is low enough to admit them.
- `signal_mode="structure"` admits T2/T3 signals and suppresses confirmation-style divergence signals.
- `signal_mode="all"` admits both families when they pass the score threshold.
- Unsupported modes raise `ValueError`.
- Strategy registry inspection exposes `signal_mode` with Chinese parameter guidance and default value `confirmation`.
- Fixed benchmark backtests are recorded for the default mode and at least one exploratory mode on 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE`.
