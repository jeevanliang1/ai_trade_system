# Chan Multi-Level 60m Completion Design

Date: 2026-06-21

## Goal

Complete the Chan multi-level reversal work instead of only adding partial minute data. The next implementation must use the longer available `60m` minute coverage as the primary lower level for daily Chan reversals, keep shorter minute levels for risk/execution, and prove the behavior with fixed six-stock benchmark evidence.

## Problem

The first `30m + 15m` implementation reduced turnover and drawdown but used public minute fixtures that only covered late 2025 onward for `15m` and mid-2025 onward for most `30m` data. A read-only AKShare probe on 2026-06-21 showed `60m` returns the same 1970-row public limit but covers about one more year because the bar interval is wider:

- `15m`: starts around `2025-12-11`
- `30m`: starts around `2025-06-05` or `2025-06-13`
- `60m`: starts around `2024-05-29` or `2024-06-06`

This makes `60m` the best available public-data candidate for the daily chart's next lower level.

## Scope

- Download and persist `60m` qfq fixtures for the fixed six-stock benchmark universe using the existing managed-data layout.
- Extend `ChanMultiLevelReversalStrategy` to support `confirm_timeframe="60m"` in addition to `30m`.
- Extend risk-level support so `risk_timeframe` can be `30m` or `15m`.
- Preserve existing defaults unless benchmark evidence supports changing them.
- Keep the strategy single-symbol, long-only, daily-loop compatible, and free of live-trading behavior.
- Do not create synthetic old minute data or hide public data coverage limits.

## Complete Multi-Level Judgment

The complete judgment chain is:

1. Daily level identifies the major reversal candidate and remains the only source of primary setup.
2. Confirm level, preferably `60m`, must provide same-direction confirmation before a new buy when lower-level data exists at the daily cutoff.
3. Risk level, either `30m` or `15m`, can block immediate entry when bearish and can reduce or exit an existing position, but it cannot open a long position by itself.
4. Missing lower-level data is evaluated at the daily cutoff using consumed lower-level bars, not by CSV existence alone.
5. No lower-level bar later than the current daily session close may influence the decision.

## Data Requirements

Use the current managed paths:

```text
data/market/a_share/{exchange}/{code}/{code}_{exchange}_60m_qfq_latest.csv
data/market/a_share/{exchange}/{code}/{code}_{exchange}_30m_qfq_latest.csv
data/market/a_share/{exchange}/{code}/{code}_{exchange}_15m_qfq_latest.csv
```

Required benchmark symbols:

- `688981/SSE`
- `000858/SZSE`
- `601318/SSE`
- `600901/SSE`
- `600989/SSE`
- `603986/SSE`

The QA output must record row counts, start/end timestamps, and whether each file was updated, skipped, or limited by upstream coverage.

## Strategy Parameters

Allow these new combinations:

- `confirm_timeframe`: `60m`, `30m`
- `risk_timeframe`: `30m`, `15m`

Existing parameters remain:

- `lower_level_policy`: `confirm_then_risk`, `confirm_only`
- `minute_missing_policy`: `skip_entry`, `daily_only`
- `minute_sell_mode`: `reduce`, `exit`
- `min_confirm_score`
- `min_risk_score`

The registry metadata must expose the new enum options so React renders them as proper controls.

## Benchmark Matrix

At minimum compare:

- Existing daily `ChanStructureStrategy` baseline.
- Current `30m + 15m` multilevel default.
- `60m + 30m` with strict `skip_entry`.
- `60m + 30m` with `daily_only`.
- `60m` confirm-only.
- Best `60m + 30m` risk threshold variants, including `minute_sell_mode=reduce` and `exit`.

## Acceptance Criteria

- Tests prove `confirm_timeframe="60m"` and `risk_timeframe="30m"` are accepted and consumed without future leakage.
- Tests prove unsupported lower levels are still rejected.
- Tests prove a daily buy can be confirmed by `60m`, while bearish `30m` risk can block or reduce according to policy.
- Fixed six-stock `60m` data exists locally or the QA document records the exact upstream blocker.
- Fixed six-stock benchmark evidence is recorded under `docs/qa/`.
- Browser screenshot evidence is captured for the React platform.
- If the best `60m` preset still underperforms the daily baseline, defaults remain unchanged and the recommendation is documented as experimental.
