# Chan Multi-Level Reversal Design

Date: 2026-06-21

## Goal

Build a first version of multi-level Chan reversal validation that uses `daily` as the major structure level, `30m` as the primary confirmation level, and `15m` as the execution or early-risk level. The goal is to test whether minute-level confirmation improves the inaccurate daily-only Chan backtest cases without changing existing Chan strategy defaults.

## Scope

- Add a new built-in strategy rather than changing the default behavior of `ChanStructureStrategy` or `ChanVolumeFusionStrategy`.
- Use the existing AKShare managed-data layout for `daily`, `30m`, and `15m` CSV files.
- Keep the strategy single-symbol and long-only, matching the current backtest and paper trading engine.
- Do not add live trading behavior, broker integration, database storage, or cross-symbol portfolio logic.
- Do not let a `15m` signal open a position by itself in the first version; it can only confirm execution after a `30m` setup or reduce risk after entry.

## Proposed Strategy

Create `ChanMultiLevelReversalStrategy` in `src/ai_trade_system/strategies/popular.py`.

The strategy will keep a daily bar buffer plus separate `30m` and `15m` lower-level context objects built from externally loaded minute bars. It will evaluate decisions on the daily backtest loop so benchmark comparisons stay compatible with the current engine, while lower-level contexts are filtered to bars whose `timestamp` is at or before the current daily bar's session close.

### Level Responsibilities

Daily level:

- Defines the major structure background.
- Allows long setups only when the daily Chan context is not clearly bearish, or when a daily bottom-divergence watch / second-buy / third-buy context is present.
- Blocks new buys when the daily context is downtrend and no bullish reversal context exists.

30m level:

- Acts as the required trade confirmation level.
- Confirms buy setups through bottom divergence confirmation, second-buy, third-buy, or a Chan Core V2 trend state improving from `down/range` toward `transition/up`.
- Confirms sell or risk-off setups through top divergence confirmation, second-sell, third-sell, or clear lower-level bearish trend context.

15m level:

- Acts as execution timing and early risk control.
- Can strengthen a buy confirmed by `30m`, but cannot open a long position on its own.
- Can reduce or exit an existing position when it shows top divergence confirmation, third-sell, or bearish trend breakdown before the daily sell structure appears.

## Data Inputs

The daily bars should continue to come from the normal backtest CSV selected in Data Center or Backtest Center. The first implementation should accept explicit CSV paths for the lower levels:

- `confirm_csv_path`
- `risk_csv_path`

Defaults should be derived from the managed-data convention when the caller provides `symbol`, `exchange`, and `adjust`:

```text
data/market/a_share/{exchange}/{code}/{code}_{exchange}_30m_qfq_latest.csv
data/market/a_share/{exchange}/{code}/{code}_{exchange}_15m_qfq_latest.csv
```

The implementation should read lower-level CSVs through existing CSV readers so timestamp parsing, timeframe metadata, and legacy compatibility stay centralized.

## Time Alignment

The backtest loop remains daily for the first slice. On each daily bar:

1. Append the daily bar to the daily Chan analyzer.
2. Select `30m` bars whose timestamp is less than or equal to that daily session close.
3. Select `15m` bars whose timestamp is less than or equal to that daily session close.
4. Analyze only newly available lower-level bars to avoid future leakage.
5. Make one position decision for that daily bar from the latest confirmed daily, `30m`, and `15m` contexts.

If a lower-level CSV is missing or has no bars up to the current daily date, the strategy should skip lower-level confirmation rather than silently treating missing data as bullish.

## Signal Rules

First-version buy rule:

- Daily context must be bullish reversal capable: bottom divergence watch/confirm, second-buy, third-buy, or non-bearish trend context.
- `30m` must provide same-direction confirmation.
- `15m` may improve target units only when it is bullish or neutral; bearish `15m` blocks the immediate entry.

First-version sell rule:

- Any daily sell confirmation exits or reduces according to existing Chan target-unit semantics.
- `30m` bearish confirmation can reduce or exit before the daily signal.
- `15m` bearish confirmation can reduce one unit or exit when configured to `exit`.

## Parameters

Expose these parameters with Chinese guidance through the existing registry metadata path:

- `confirm_timeframe`: default `30m`, options `30m`.
- `risk_timeframe`: default `15m`, options `15m`.
- `exchange`: default `SZSE`.
- `adjust`: default `qfq`.
- `confirm_csv_path`: default empty string, derived from managed data when empty.
- `risk_csv_path`: default empty string, derived from managed data when empty.
- `lower_level_policy`: default `confirm_then_risk`, options `confirm_then_risk`, `confirm_only`.
- `minute_missing_policy`: default `skip_entry`, options `skip_entry`, `daily_only`.
- `minute_sell_mode`: default `reduce`, options `reduce`, `exit`.
- `min_daily_score`: default `28.0`.
- `min_confirm_score`: default `28.0`.
- `min_risk_score`: default `24.0`.
- `max_holding_bars`: default `15`.
- Existing position-unit parameters should mirror `ChanStructureStrategy` defaults where possible.

## API And UI Surface

The new strategy should appear in the built-in strategy registry with:

- Chinese display name: `缠论多级别反转`
- Description explaining daily structure, `30m` confirmation, and `15m` risk timing.
- Parameter guidance that makes it clear `15m` is not a standalone entry trigger.

No new React page is required for the first slice. The existing Strategy Workshop parameter form and Backtest Center should be sufficient once registry metadata exposes the new strategy and parameters.

## Benchmark And QA

Because this changes strategy behavior, benchmark evidence is required.

Required comparison rows:

- Existing `ChanStructureStrategy` on daily fixtures.
- Existing `ChanVolumeFusionStrategy` on daily fixtures.
- New `ChanMultiLevelReversalStrategy` with `daily + 30m`.
- New `ChanMultiLevelReversalStrategy` with `daily + 30m + 15m`.

Use the fixed six-stock qfq benchmark universe when local fixture coverage exists:

- `688981/SSE`
- `000858/SZSE`
- `601318/SSE`
- `600901/SSE`
- `600989/SSE`
- `603986/SSE`

If minute fixtures cannot cover the full fixed range, record each symbol's actual row count, start timestamp, and end timestamp. Do not hide partial coverage.

## Testing

Use TDD before implementation.

Backend tests:

- Multi-level strategy rejects unknown level policies and invalid score thresholds.
- Missing minute data with `skip_entry` blocks new entries.
- Missing minute data with `daily_only` preserves daily-only fallback behavior.
- Daily bullish setup plus `30m` bullish confirmation emits a buy.
- Daily bullish setup plus bearish `15m` blocks immediate entry.
- Existing position plus `15m` bearish confirmation reduces or exits according to `minute_sell_mode`.
- No lower-level bar newer than the current daily session close is used.

Registry tests:

- Strategy discovery includes `ChanMultiLevelReversalStrategy`.
- Parameter guidance includes Chinese labels, descriptions, options, and tuning impact.

QA:

- Record fixed benchmark metrics under `docs/qa/`.
- Capture React screenshots showing the strategy is visible and parameters render in Strategy Workshop.

## Risks

- AKShare minute history may be shorter than the fixed three-year daily fixtures. The QA document must separate data-coverage limitations from strategy-quality conclusions.
- Daily-loop execution cannot model exact intraday fill timing. This first slice is for confirmation quality, not precise intraday execution.
- `15m` noise can over-filter valid reversals. The first version intentionally prevents `15m` standalone entries and limits it to execution gating or risk reduction.

## Acceptance Criteria

- The new strategy can be discovered, configured, and backtested through the existing platform.
- It does not change existing strategy defaults or daily-only benchmark behavior.
- It avoids future leakage when aligning daily, `30m`, and `15m` data.
- Tests cover the approved multi-level entry and exit semantics.
- QA records daily-only, `daily + 30m`, and `daily + 30m + 15m` comparisons with explicit minute-data coverage.
