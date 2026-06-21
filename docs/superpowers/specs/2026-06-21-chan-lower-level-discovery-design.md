# Chan Lower-Level Discovery Design

Date: 2026-06-21

## Goal

Add an offensive Chan multi-level entry mode that can discover lower-level reversal opportunities before a daily buy point appears, while preserving the existing conservative daily-confirmed mode for direct comparison.

## Problem

The existing `ChanMultiLevelReversalStrategy` behaves as a filter:

1. Daily level must first emit a buy point.
2. Lower level confirms or blocks that daily buy.
3. Lower level risk signals can reduce or exit existing positions.

This is useful for reducing noisy daily trades, but it cannot find opportunities that are visible on `60m` or `30m` before the daily chart confirms. The user wants a multi-level linkage mode where daily bars provide trend/background context and lower levels can initiate early exploratory entries.

## Scope

- Extend `ChanMultiLevelReversalStrategy`; do not create a separate strategy class.
- Add `entry_mode`:
  - `daily_confirmed`: existing behavior and default.
  - `lower_level_discovery`: new offensive behavior.
- Keep the strategy single-symbol, long-only, daily-loop compatible, and free of live-trading behavior.
- Use only lower-level bars available at or before the current daily session close.
- Keep lower-level exits controlled by existing `minute_sell_mode="reduce" | "exit"`.
- Expose `entry_mode` through registry metadata so React renders an enum select.
- Benchmark the fixed expanded universe: `688981/SSE`, `000858/SZSE`, `601318/SSE`, `600901/SSE`, `600989/SSE`, `603986/SSE`, `688733/SSE`, and `688072/SSE`.

## Behavior

### Existing Mode: `daily_confirmed`

The current mode remains unchanged:

1. Daily buy point is required.
2. Confirm timeframe must provide a same-direction buy signal unless daily fallback is configured and no lower-level data has been consumed.
3. Risk timeframe can block new buys or reduce/exit existing positions.

### New Mode: `lower_level_discovery`

The new mode uses daily bars as background and lower-level bars as discovery:

1. Existing-position risk handling still runs first. A high-confidence lower-level sell signal can reduce or exit before daily sell appears.
2. Daily sell or confirm-level sell still exits/reduces current positions.
3. If no daily buy exists, a confirm-timeframe buy signal can open or add to a position when daily background is not bearish.
4. Bearish daily background is defined as a daily sell signal at or above `min_daily_score` on the current bar.
5. Bearish risk-timeframe signal at or above `min_risk_score` blocks lower-level discovery buys.
6. Lower-level discovery uses confirm signal confidence to choose target units, then applies the same cap logic as daily buys.
7. Discovery reasons are labeled `chan_multilevel:DISCOVERY_<LEVEL>:<kind>:<reason>`.

This keeps the implementation conservative enough for the existing single-symbol daily backtest engine while allowing lower-level signals to increase opportunity discovery.

## Data And Benchmark Requirements

Use managed qfq fixtures under:

```text
data/market/a_share/{exchange}/{code}/{code}_{exchange}_{timeframe}_qfq_latest.csv
```

Required benchmark symbols:

- `688981/SSE`
- `000858/SZSE`
- `601318/SSE`
- `600901/SSE`
- `600989/SSE`
- `603986/SSE`
- `688733/SSE`
- `688072/SSE`

Benchmark variants:

- Daily `ChanStructureStrategy` baseline.
- Conservative `ChanMultiLevelReversalStrategy(entry_mode="daily_confirmed")`.
- Offensive `ChanMultiLevelReversalStrategy(entry_mode="lower_level_discovery")` using `60m` confirmation and `30m` risk.

Record row coverage, parameters, aggregate metrics, and per-symbol results under `docs/qa/`.

## Acceptance Criteria

- Tests prove unsupported `entry_mode` values are rejected.
- Tests prove lower-level discovery can buy without a daily buy when daily background is not bearish.
- Tests prove a current daily sell background blocks lower-level discovery buys.
- Tests prove lower-level risk signals still block discovery buys and can reduce/exit existing positions.
- Registry metadata exposes `entry_mode` options.
- Expanded 8-stock benchmark results are recorded.
- React platform screenshot acceptance is captured or the exact blocker is recorded.
