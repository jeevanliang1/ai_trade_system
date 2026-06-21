# Chan Multi-Level Reversal Calibration QA

Date: 2026-06-21

## Scope

This QA record covers option B for `ChanMultiLevelReversalStrategy`: fix partial minute-coverage fallback semantics, then run a bounded fixed six-stock calibration sweep using daily qfq fixtures plus available `30m` and `15m` minute fixtures.

## Code Change

`minute_missing_policy="daily_only"` now treats minute data as missing at the current daily cutoff until the `30m` context has consumed at least one lower-level bar. This fixes the case where a managed `30m` CSV exists but starts after the current daily backtest date.

Default behavior is unchanged for `minute_missing_policy="skip_entry"`.

## TDD Evidence

RED command:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected failure before implementation:

```text
FAILED tests/test_chan_multilevel_reversal_strategy.py::test_chan_multilevel_daily_only_fallback_when_minute_fixture_starts_later
1 failed, 10 passed
```

GREEN command:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Result after implementation:

```text
11 passed
```

## Fixture Coverage

Backtest window requested: `20230619` to `20260619`. Available daily fixtures end on `2026-06-18`; public AKShare minute fixtures are partial and start later.

| Symbol | Exchange | Daily Rows | Daily Range | 30m Rows | 30m Range | 15m Rows | 15m Range |
|---|---|---:|---|---:|---|---:|---|
| 688981 | SSE | 720 | 2023-06-19 to 2026-06-18 | 1970 | 2025-06-05 14:30:00 to 2026-06-18 15:00:00 | 1970 | 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| 000858 | SZSE | 726 | 2023-06-19 to 2026-06-18 | 1970 | 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | 1970 | 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| 601318 | SSE | 726 | 2023-06-19 to 2026-06-18 | 1970 | 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | 1970 | 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| 600901 | SSE | 726 | 2023-06-19 to 2026-06-18 | 1970 | 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | 1970 | 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| 600989 | SSE | 726 | 2023-06-19 to 2026-06-18 | 1970 | 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | 1970 | 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| 603986 | SSE | 726 | 2023-06-19 to 2026-06-18 | 1970 | 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | 1970 | 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |

## Calibration Method

The sweep used `BacktestConfig(initial_cash=100000)` and the existing `run_backtest()` plus `calculate_backtest_metrics()` path. To avoid repeating identical lower-level Chan scans for each threshold variant, each symbol's `30m` and `15m` `ChanCoreV2Analyzer` result sequence was precomputed once and replayed inside each strategy instance. Daily analyzers still ran normally for each benchmark run.

Parameter grid:

- `minute_missing_policy`: `skip_entry`, `daily_only`
- `lower_level_policy`: `confirm_only`, `confirm_then_risk`
- `min_confirm_score`: `20`, `24`, `28`, `32`
- `min_risk_score`: `20`, `24`, `28`, `32`
- `minute_sell_mode`: `reduce`, `exit`

## Aggregate Results

| Variant | Avg Return % | Avg Max DD % | Total Trades | Avg Win Rate % | Avg Profit Factor | Notes |
|---|---:|---:|---:|---:|---:|---|
| `ChanStructureStrategy` daily default | 9.6964 | -3.3310 | 426 | 40.9346 | 1.4823 | Existing daily-only benchmark |
| `skip_entry + confirm_then_risk c28/r24 reduce` | 2.2745 | -2.4155 | 81 | 27.9100 | 1.0160 | Current default, strict minute confirmation |
| `daily_only + confirm_then_risk c28/r24 reduce` | 2.3894 | -3.3353 | 360 | 37.0958 | 1.1277 | Corrected fallback restores early daily trades |
| `daily_only + confirm_only c20/c24/c28` | 3.6993 | -3.3350 | 358 | 37.4034 | 1.2267 | Best multilevel preset in this sweep |
| `daily_only + confirm_only c32` | 2.2758 | -2.9390 | 308 | 37.4495 | 1.4443 | Lower drawdown, lower return |
| `daily_only + confirm_then_risk c20/c24/c28 r32 reduce` | 3.6842 | -3.3353 | 360 | 37.0958 | 1.2215 | 15m risk only helps when threshold is stricter |
| `daily_only + confirm_then_risk c20/c24/c28 r32 exit` | 3.6700 | -3.3427 | 359 | 37.0958 | 1.2215 | `exit` did not improve `reduce` |
| `daily_only + confirm_then_risk c32 r20/r24/r28` | 1.4172 | -2.9390 | 308 | 37.4495 | 1.3327 | Confirm threshold too strict with current coverage |

## Per-Symbol Best Multilevel Preset

Best multilevel preset from the sweep: `minute_missing_policy=daily_only`, `lower_level_policy=confirm_only`, `min_confirm_score=28`.

| Symbol | Return % | Benchmark % | Excess % | Max DD % | Trades | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|
| 688981/SSE | 2.2734 | 155.5394 | -153.2660 | -4.1914 | 59 | 32.0000 | 1.2059 |
| 000858/SZSE | -4.6882 | -52.8208 | 48.1326 | -4.9283 | 40 | 31.5789 | 0.2540 |
| 601318/SSE | -2.9172 | 23.8525 | -26.7697 | -3.0715 | 48 | 27.2727 | 0.2759 |
| 600901/SSE | 0.0355 | 85.0153 | -84.9798 | -0.1316 | 52 | 41.6667 | 1.3224 |
| 600989/SSE | -0.7265 | 87.6963 | -88.4228 | -1.2230 | 53 | 48.0000 | 0.8241 |
| 603986/SSE | 28.2186 | 459.7579 | -431.5393 | -6.4644 | 106 | 43.9024 | 3.4780 |

## Decision

Do not change `ChanMultiLevelReversalStrategy` defaults in this pass.

Reasoning:

- The corrected `daily_only` fallback improves the strict default's average return from `2.2745%` to `2.3894%` under `confirm_then_risk`, but it also raises drawdown toward the daily-only profile.
- The best multilevel preset, `daily_only + confirm_only c28`, reaches `3.6993%`, still far below the daily Chan baseline `9.6964%`.
- `15m` risk filtering is useful only at a stricter `min_risk_score=32`; lower risk thresholds over-filter strong trends.
- Current `30m/15m` public fixture coverage starts in 2025 or later, so changing defaults from this partial minute sample would be overfitting.

Recommended experimental preset for further manual comparison:

```text
minute_missing_policy=daily_only
lower_level_policy=confirm_only
min_confirm_score=28
minute_sell_mode=reduce
```

If 15m risk control is required:

```text
minute_missing_policy=daily_only
lower_level_policy=confirm_then_risk
min_confirm_score=28
min_risk_score=32
minute_sell_mode=reduce
```

## Full Verification

Backend:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
```

Result:

```text
275 passed
```

Frontend tests:

```bash
npm --prefix frontend test
```

Result:

```text
Test Files 21 passed (21)
Tests 101 passed (101)
```

Frontend production build:

```bash
npm --prefix frontend run build
```

Result:

```text
vite build completed successfully
```

## Browser Acceptance

Target: React platform at `http://localhost:5173`.

Browser plugin attempt failed with:

```text
Mcp error: -32602: js: codex/sandbox-state-meta: missing field `sandboxPolicy`
```

Fallback: started `./scripts/run_app.sh` and used the project headless Chrome screenshot script.

```bash
node scripts/capture_app_screenshots.mjs --url http://localhost:5173 --out-dir docs/qa/screenshots --prefix 2026-06-21-chan-multilevel-calibration
```

Screenshots:

- `docs/qa/screenshots/2026-06-21-chan-multilevel-calibration_desktop_1440.png` (`1440x1024`)
- `docs/qa/screenshots/2026-06-21-chan-multilevel-calibration_mobile_390.png` (`390x844`)

Visual check: both screenshots render the React platform with real `AI量化平台` content and no framework error overlay.
