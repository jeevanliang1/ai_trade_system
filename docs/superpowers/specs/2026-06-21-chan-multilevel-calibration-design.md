# Chan Multi-Level Calibration Design

Date: 2026-06-21

## Goal

Calibrate `ChanMultiLevelReversalStrategy` after the first fixed six-stock benchmark showed lower turnover and drawdown but weaker returns. The first calibration pass keeps the approved daily -> `30m` -> `15m` hierarchy and fixes one data-semantics issue before comparing parameters.

## Approved Approach

Use option B: correct minute coverage semantics first, then run a bounded parameter sweep.

The current `daily_only` fallback treats any existing `30m` CSV as lower-level data availability, even when all bars in that CSV start after the current daily backtest date. That is too strict for partial public minute fixtures. A daily bar before the first consumed `30m` bar should be considered lower-level missing at that cutoff, while dates after lower-level bars have been consumed should still require real `30m` confirmation.

## Behavior Rules

- Keep the default `minute_missing_policy="skip_entry"` unchanged.
- With `skip_entry`, a daily buy is skipped when no qualifying `30m` buy confirmation exists, even if minute coverage has not started yet.
- With `daily_only`, a daily buy may fall back to daily-only only when the `30m` context has not consumed any bar by the current daily session close.
- Once at least one `30m` bar has been consumed, `daily_only` no longer falls back just because the latest `30m` result has no buy signal.
- No lower-level bar newer than the current daily session close may be consumed.

## Calibration Scope

After the semantic fix, run fixed six-stock benchmarks over `20230619` to `20260619` using local qfq daily fixtures and available `30m`/`15m` minute fixtures:

- `688981/SSE`
- `000858/SZSE`
- `601318/SSE`
- `600901/SSE`
- `600989/SSE`
- `603986/SSE`

Compare at minimum:

- Current default multilevel parameters.
- `daily_only` fallback with the corrected missing-at-cutoff behavior.
- `confirm_only` versus `confirm_then_risk`.
- `minute_sell_mode=reduce` versus `exit` on the strongest candidate settings.
- A bounded score grid around `min_confirm_score` and `min_risk_score`.

## Acceptance Criteria

- Tests demonstrate the partial-minute-coverage fallback behavior before implementation.
- Existing future-leakage protection and default `skip_entry` behavior remain covered.
- Benchmark QA records coverage, parameters, and comparable metrics for the fixed six-stock universe.
- If benchmark evidence does not justify changing defaults, keep defaults unchanged and document the recommended preset instead of forcing an overfit default.
