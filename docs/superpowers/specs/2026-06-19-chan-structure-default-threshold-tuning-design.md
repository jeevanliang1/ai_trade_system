# Chan Structure Default Threshold Tuning Design

## Goal

Tune the default `ChanStructureStrategy` signal threshold after indicator-backed divergence scoring, using the fixed 中芯国际 and 五粮液 benchmark fixtures as the comparison standard.

## Scope

This slice only changes the built-in strategy default threshold. It does not change Chan structure detection, segment construction, divergence scoring, or live-trading behavior.

## Benchmark Findings

Fixed fixtures:

- 中芯国际 `688981/SSE`: `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
- 五粮液 `000858/SZSE`: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`

Current default:

- `lookback=160`
- `min_stroke_bars=5`
- `min_rebound_pct=0.03`
- `min_signal_score=24.0`

Current benchmark result:

- 中芯国际 return `4.4157%`, max drawdown `-5.1712%`, trades `59`
- 五粮液 return `-6.6814%`, max drawdown `-6.7334%`, trades `62`
- Average return `-1.1329%`

Candidate threshold sweep with other defaults unchanged:

- `min_signal_score=30.0` through `44.0` all produced the same benchmark trades because they filter 28-point T2/T3 signals while retaining stronger divergence/confirmation signals.
- Result: 中芯国际 return `4.7162%`, max drawdown `-4.6198%`, trades `1`; 五粮液 return `-0.8148%`, max drawdown `-3.4008%`, trades `2`; average return `1.9507%`.
- `min_signal_score>=46.0` produced zero trades on both fixtures, which is too restrictive for a default research strategy.

## Decision

Set the default `min_signal_score` from `24.0` to `30.0`.

Rationale:

- It is the least restrictive threshold that removes current low-confidence 28-point T2/T3 churn.
- It keeps the strategy active on both fixed fixtures.
- It improves average return and reduces drawdown on the fixed benchmark pair.
- It leaves users free to lower the threshold when they explicitly want more exploratory T2/T3 signals.

## Acceptance Criteria

- Instantiating `ChanStructureStrategy("000001")` uses `min_signal_score == 30.0`.
- The strategy registry reports the default `min_signal_score` for `ChanStructureStrategy` as `30.0`.
- A deterministic weak T2/T3-only fixture is filtered by the new default but still trades when `min_signal_score=24.0`.
- Existing explicit-threshold Chan strategy tests continue to pass.
- Full Python tests, frontend tests/build, fixed benchmark backtests, and browser QA are run before delivery.
