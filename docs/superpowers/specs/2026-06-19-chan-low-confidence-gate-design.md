# Chan Low-Confidence Gate Design

## Goal

Add a conservative gate for low-confidence Chan structure signals in `ChanStructureStrategy` so 二买/二卖 do not trade by default unless the surrounding structure supports them.

This is the B variant selected after the A position-sizing change.

## Context

The A variant changed `ChanStructureStrategy` from binary position state to target position units:

- 二买/二卖 adjust one low-confidence unit.
- 背驰确认 targets two units or reduces to one retained unit.
- 三买/三卖 add to high-confidence units or clear.

The first six-stock benchmark showed that broader participation improves some trend fixtures but creates churn and losses on weaker or range-bound fixtures. The next change should reduce low-confidence churn without weakening high-confidence 三买/三卖 semantics.

## Approved Scope

Implement low-confidence gating only.

In scope:

- Gate `CHAN_STRUCT_BUY_T2` and `CHAN_STRUCT_SELL_T2`.
- Keep `CHAN_STRUCT_BUY_T3`, `CHAN_STRUCT_SELL_T3`, `CHAN_STRUCT_BUY_CONFIRM`, `CHAN_STRUCT_SELL_CONFIRM`, and armed T1 confirmations eligible under existing score/mode/point/level filters.
- Keep the A variant target-unit sizing model.
- Expose user-facing parameters with Chinese labels and tuning guidance.
- Run the fixed six-stock benchmark after implementation.

Out of scope:

- Rewriting Chan structure signal generation.
- Changing Chan Core V2 trend/pivot lifecycle construction.
- Optimizing final parameter values through a broad grid search.
- Adding live trading behavior.

## Trading Semantics

Low-confidence signals are:

- `CHAN_STRUCT_BUY_T2`
- `CHAN_STRUCT_SELL_T2`

By default, a low-confidence signal can trade only when at least one gate condition passes:

1. **Armed divergence confirmation:** there is an active same-direction T1 watch and the current T2 confirms it through the existing `ARMED_CONFIRM` path.
2. **Trend-compatible context:** the latest Chan Core V2 trend context for the signal level is not hostile to the action.
3. **High low-confidence score:** the T2 score is strong enough to override the gate.

三买/三卖 remain high-confidence signals and do not require the low-confidence gate.

## Default Parameters

Add constructor parameters to `ChanStructureStrategy`:

- `low_confidence_gate: str = "divergence_or_trend"`
- `low_confidence_min_score: float = 32.0`
- `range_max_units: int = 1`

Allowed `low_confidence_gate` values:

- `off`: keep A behavior; T2 trades after the existing filters only.
- `divergence`: T2 trades only as an armed T1 confirmation.
- `trend`: T2 trades only when trend context is compatible or score override passes.
- `divergence_or_trend`: default; T2 trades when armed T1 confirmation, compatible trend, or score override passes.

Validation:

- `low_confidence_gate` must be one of the allowed values.
- `low_confidence_min_score` must be non-negative.
- `range_max_units` must be non-negative and no greater than `high_confidence_units`.

## Trend Compatibility

Use the existing incremental Chan Core V2 snapshot already held by `ChanStructureStrategy`.

For a low-confidence buy:

- Compatible when the latest trend for the signal level is `up` or `transition`.
- Compatible when there is no trend object for the signal level.
- Not compatible when the trend is `down`.
- If the trend is `range`, allow only if current `position_units < range_max_units`.

For a low-confidence sell:

- Compatible when the latest trend for the signal level is `down`, `transition`, or `range`.
- Compatible when there is no trend object for the signal level.
- Not compatible when the trend is `up` unless the score override passes.

If a signal does not include `metadata["level"]`, or the level is not represented in Chan Core V2 trend summaries such as `fractal`, use the latest stroke trend first, then segment trend as fallback.

## Score Override

If `abs(signal.score) >= low_confidence_min_score`, the signal can pass the low-confidence gate even without armed divergence or compatible trend.

This keeps the gate conservative for ordinary 28-point T2 churn while allowing stronger T2 evidence to trade.

## Armed T1 Confirmation

The existing armed watch confirmation path should bypass the normal low-confidence gate when the current signal confirms an active same-direction T1 divergence.

Example:

- T1 bottom divergence watch arms.
- A subsequent `CHAN_STRUCT_BUY_T2` arrives within `watch_confirm_bars`.
- Existing filters allow it.
- It trades through `ARMED_CONFIRM`, targeting `divergence_confirm_units`.

This path should continue to use the A variant armed-confirm target-unit behavior.

## User-Facing Metadata

Add Chinese strategy parameter guidance:

- `low_confidence_gate`: `低确定性门控`
- `low_confidence_min_score`: `低确定性放行分`
- `range_max_units`: `震荡区最大仓位`

The React parameter form should pick these up through existing registry metadata. No custom frontend code is expected unless tests reveal a generic rendering issue.

## Tests

Add focused tests for:

- Default gate blocks a plain T2 buy in a hostile down-trend context.
- Score override allows a strong T2 buy.
- `low_confidence_gate="off"` preserves A behavior.
- Armed T1 + T2 confirmation bypasses the low-confidence gate and targets `divergence_confirm_units`.
- Range context caps low-confidence adds when `position_units >= range_max_units`.
- T3 buy/sell remains unaffected by the low-confidence gate.
- Invalid gate values and invalid unit caps raise `ValueError`.
- Registry metadata exposes Chinese guidance and enum options.

Use the existing fake `ChanCoreV2Analyzer` test pattern in `tests/test_builtin_popular_strategies.py` so tests remain deterministic and do not depend on fragile synthetic K-line shapes.

## Backtest Acceptance

Before final delivery:

- Run focused Python tests for strategy behavior and registry metadata.
- Run `PYTHONPATH=src python -m pytest`.
- Run the fixed six-stock qfq benchmark:
  - 中芯国际 `688981/SSE`
  - 五粮液 `000858/SZSE`
  - 中国平安 `601318/SSE`
  - 江苏金租 `600901/SSE`
  - 宝丰能源 `600989/SSE`
  - 兆易创新 `603986/SSE`
- Record comparable results under `docs/qa/`.
- If visible strategy parameter metadata changes in React, capture browser evidence or state the exact blocker.

## Success Criteria

The implementation succeeds when:

- Low-confidence T2 signals are no longer default-unconditional.
- High-confidence T3 and divergence confirmation behavior remains intact.
- The strategy remains configurable enough to reproduce A behavior with `low_confidence_gate="off"`.
- The fixed six-stock benchmark is recorded for comparison against the A variant QA.
