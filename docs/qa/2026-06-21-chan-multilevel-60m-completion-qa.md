# Chan Multilevel 60m Completion QA

## Scope

Completed the Chan multi-level reversal judgment pass by adding longer available `60m` confirmation support while keeping daily bars as the primary setup level:

- Daily Chan structure remains the only source of primary reversal setup.
- `confirm_timeframe` now supports `60m` and `30m`.
- `risk_timeframe` now supports `30m` and `15m`.
- Lower levels can confirm, block, reduce, or exit according to policy, but cannot independently open positions.
- Existing defaults remain backward compatible: `confirm_timeframe="30m"` and `risk_timeframe="15m"`.
- No synthetic older minute data was created.

## Implementation Evidence

Code and registry changes:

- `src/ai_trade_system/strategies/popular.py`: extended Chan multi-level timeframe allowlists, validation messages, and dynamic reason labels such as `CONFIRM_60M` and `RISK_30M`.
- `src/ai_trade_system/strategy_registry.py`: exposed `60m/30m` confirmation and `30m/15m` risk enum options in user-facing parameter metadata.
- `tests/test_chan_multilevel_reversal_strategy.py`: added 60m confirmation and 30m risk-block coverage.
- `tests/test_strategy_registry.py`: pinned the new registry options and guidance.

TDD checks recorded during implementation:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Red result before implementation: the new `60m` cases failed because `confirm_timeframe="60m"` was rejected.

Green result after implementation: `13 passed`.

```bash
python -m pytest tests/test_strategy_registry.py::test_chan_multilevel_reversal_strategy_is_registered_with_guidance -q
```

Red result before registry update: expected `60m` guidance was missing.

Green result after registry update: `1 passed`.

Combined targeted verification:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py tests/test_strategy_registry.py -q
```

Result: `26 passed`.

## 60m Fixture Preparation

Command path used: `ai_trade_system.data_manager.update_stock_data(...)` with `timeframe="60m"`, `start_date="20230619"`, `end_date="20260619"`, `adjust="qfq"`, and `if_stale=False`.

Result: all six fixed benchmark stocks returned `status=updated`, `fetched_rows=1970`, and `latest_rows=1970`.

AKShare public minute data still returns a 1970-row window, so wider bars provide longer calendar coverage:

- `15m`: starts `2025-12-11 14:45:00`
- `30m`: starts `2025-06-05 14:30:00` for `688981`, `2025-06-13 14:30:00` for the other five stocks
- `60m`: starts `2024-05-29 14:00:00` for `688981`, `2024-06-06 14:00:00` for the other five stocks

| Symbol | Name | Daily rows/range | 60m rows/range | 30m rows/range | 15m rows/range |
| --- | --- | --- | --- | --- | --- |
| `688981/SSE` | 中芯国际 | 720: `2023-06-19` to `2026-06-18` | 1970: `2024-05-29 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-05 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `000858/SZSE` | 五粮液 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `601318/SSE` | 中国平安 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `600901/SSE` | 江苏金租 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `600989/SSE` | 宝丰能源 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `603986/SSE` | 兆易创新 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |

Managed 60m files written:

- `data/market/a_share/SSE/688981/688981_SSE_60m_qfq_latest.csv`
- `data/market/a_share/SZSE/000858/000858_SZSE_60m_qfq_latest.csv`
- `data/market/a_share/SSE/601318/601318_SSE_60m_qfq_latest.csv`
- `data/market/a_share/SSE/600901/600901_SSE_60m_qfq_latest.csv`
- `data/market/a_share/SSE/600989/600989_SSE_60m_qfq_latest.csv`
- `data/market/a_share/SSE/603986/603986_SSE_60m_qfq_latest.csv`

## Benchmark Method

Benchmark window: `2023-06-19` to `2026-06-19`.

Engine: shared `run_backtest` and `calculate_backtest_metrics` with `BacktestConfig()` defaults:

- Initial cash: `100000`
- Commission rate: `0.0003`
- Slippage: `0.01`
- Max order cash: `50000`
- Adjustment: `qfq`

To keep the matrix repeatable, lower-level `ChanCoreV2Analyzer` output was precomputed per symbol and timeframe before replaying strategy variants.

## Aggregate Benchmark Results

| Variant | Avg return % | Avg benchmark return % | Avg excess % | Avg max DD % | Total trades | Avg win rate % | Avg profit factor | Interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `daily_chan_structure_default` | 9.6964 | 126.5068 | -116.8103 | -3.3310 | 426 | 40.9346 | 1.4823 | Daily baseline remains the return benchmark. |
| `ml_30_15_daily_only_confirm_only_c28` | 3.6993 | 126.5068 | -122.8075 | -3.3350 | 358 | 37.4034 | 1.2267 | Previous 30m/15m calibration reference. |
| `ml_60_30_skip_c28_r24_reduce` | 3.6965 | 126.5068 | -122.8103 | -2.8094 | 205 | 48.5748 | 1.3264 | Best complete 60m+30m preset in this pass. |
| `ml_60_30_daily_only_confirm_only_c32` | 3.2106 | 126.5068 | -123.2962 | -1.9440 | 153 | 40.7109 | 2.4395 | Defensive 60m confirm-only preset. |
| `ml_60_30_daily_only_c28_r24_reduce` | 2.9437 | 126.5068 | -123.5631 | -3.2845 | 292 | 44.7416 | 1.1778 | Daily fallback with 60m/30m risk was less selective. |
| `ml_30_15_skip_default_c28_r24_reduce` | 2.2745 | 126.5068 | -124.2323 | -2.4155 | 81 | 27.9100 | 1.0160 | Original strict 30m+15m default reference. |
| `ml_60_30_daily_only_confirm_only_c28` | 2.1422 | 126.5068 | -124.3646 | -3.5806 | 289 | 42.6852 | 1.1364 | Lower threshold admitted more weak trades. |
| `ml_60_30_daily_only_risk_c28_r32_exit` | 1.7748 | 126.5068 | -124.7320 | -3.5923 | 287 | 42.6852 | 1.1017 | Risk exits were too punitive in this fixture set. |
| `ml_60_30_daily_only_risk_c28_r32_reduce` | 1.7571 | 126.5068 | -124.7497 | -3.5923 | 289 | 42.6852 | 1.0957 | Higher risk score did not improve aggregate return. |

## Selected Per-Symbol Results

| Symbol | Variant | Return % | Benchmark return % | Excess % | Max DD % | Trades | Win rate % | Profit factor |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `688981/SSE` | `daily_chan_structure_default` | 4.7808 | 155.5394 | -150.7586 | -4.6154 | 68 | 45.4545 | 1.3370 |
| `000858/SZSE` | `daily_chan_structure_default` | -2.7280 | -52.8208 | 50.0928 | -4.4337 | 56 | 25.0000 | 0.6017 |
| `601318/SSE` | `daily_chan_structure_default` | -1.9764 | 23.8525 | -25.8289 | -2.8425 | 68 | 38.2353 | 0.6924 |
| `600901/SSE` | `daily_chan_structure_default` | -0.0927 | 85.0153 | -85.1080 | -0.3171 | 79 | 35.8974 | 1.1002 |
| `600989/SSE` | `daily_chan_structure_default` | 0.8928 | 87.6963 | -86.8035 | -1.0470 | 50 | 50.0000 | 1.9958 |
| `603986/SSE` | `daily_chan_structure_default` | 57.3020 | 459.7579 | -402.4559 | -6.7301 | 105 | 51.0204 | 3.1668 |
| `688981/SSE` | `ml_30_15_skip_default_c28_r24_reduce` | -1.0686 | 155.5394 | -156.6080 | -3.7125 | 18 | 28.5714 | 0.6338 |
| `000858/SZSE` | `ml_30_15_skip_default_c28_r24_reduce` | -0.3565 | -52.8208 | 52.4643 | -0.5813 | 2 | 0.0000 | 0.0000 |
| `601318/SSE` | `ml_30_15_skip_default_c28_r24_reduce` | -1.9144 | 23.8525 | -25.7669 | -2.2588 | 6 | 0.0000 | 0.0000 |
| `600901/SSE` | `ml_30_15_skip_default_c28_r24_reduce` | -0.1223 | 85.0153 | -85.1376 | -0.1223 | 11 | 25.0000 | 0.3766 |
| `600989/SSE` | `ml_30_15_skip_default_c28_r24_reduce` | -0.5255 | 87.6963 | -88.2218 | -1.2212 | 20 | 55.5556 | 1.1430 |
| `603986/SSE` | `ml_30_15_skip_default_c28_r24_reduce` | 17.6341 | 459.7579 | -442.1238 | -6.5968 | 24 | 58.3333 | 3.9428 |
| `688981/SSE` | `ml_60_30_skip_c28_r24_reduce` | 0.1123 | 155.5394 | -155.4271 | -5.6900 | 48 | 50.0000 | 0.8297 |
| `000858/SZSE` | `ml_60_30_skip_c28_r24_reduce` | -0.4802 | -52.8208 | 52.3406 | -1.0669 | 14 | 28.5714 | 0.3443 |
| `601318/SSE` | `ml_60_30_skip_c28_r24_reduce` | -2.7343 | 23.8525 | -26.5868 | -2.8098 | 28 | 30.7692 | 0.3597 |
| `600901/SSE` | `ml_60_30_skip_c28_r24_reduce` | 0.0412 | 85.0153 | -84.9741 | -0.1036 | 25 | 66.6667 | 1.7771 |
| `600989/SSE` | `ml_60_30_skip_c28_r24_reduce` | 0.0879 | 87.6963 | -87.6084 | -0.5868 | 36 | 52.9412 | 1.2470 |
| `603986/SSE` | `ml_60_30_skip_c28_r24_reduce` | 25.1519 | 459.7579 | -434.6060 | -6.5990 | 54 | 62.5000 | 3.4006 |
| `688981/SSE` | `ml_60_30_daily_only_confirm_only_c32` | -0.2735 | 155.5394 | -155.8129 | -5.2195 | 61 | 40.0000 | 0.7102 |
| `000858/SZSE` | `ml_60_30_daily_only_confirm_only_c32` | -3.2144 | -52.8208 | 49.6064 | -3.3334 | 30 | 40.0000 | 0.3286 |
| `601318/SSE` | `ml_60_30_daily_only_confirm_only_c32` | -3.1559 | 23.8525 | -27.0084 | -3.2314 | 38 | 27.7778 | 0.3704 |
| `600901/SSE` | `ml_60_30_daily_only_confirm_only_c32` | 0.0477 | 85.0153 | -84.9676 | -0.1590 | 43 | 60.0000 | 1.7638 |
| `600989/SSE` | `ml_60_30_daily_only_confirm_only_c32` | 0.1071 | 87.6963 | -87.5892 | -0.7501 | 51 | 41.6667 | 1.4758 |
| `603986/SSE` | `ml_60_30_daily_only_confirm_only_c32` | 19.3422 | 459.7579 | -440.4157 | -8.7902 | 66 | 46.6667 | 2.1699 |

## Decision

Do not change the strategy defaults in this pass.

The best complete `60m+30m` preset improves over the strict `30m+15m` reference on aggregate return, turnover, win rate, and profit factor:

```python
ChanMultiLevelReversalStrategy(
    confirm_timeframe="60m",
    risk_timeframe="30m",
    minute_missing_policy="skip_entry",
    lower_level_policy="confirm_then_risk",
    min_confirm_score=28,
    min_risk_score=24,
    minute_sell_mode="reduce",
)
```

However, it still underperforms the daily Chan baseline on average return, and `688981/SSE` shows a larger drawdown than the old strict multilevel reference. Treat it as an experimental complete multi-level preset, not the new default.

A lower-drawdown defensive preset is:

```python
ChanMultiLevelReversalStrategy(
    confirm_timeframe="60m",
    risk_timeframe="30m",
    minute_missing_policy="daily_only",
    lower_level_policy="confirm_only",
    min_confirm_score=32,
)
```

This preset had `3.2106%` average return, `-1.9440%` average max drawdown, `153` trades, and `2.4395` average profit factor in the fixed six-stock run.

## Remaining Risk

- Public AKShare minute data still does not cover the full three-year benchmark window. `60m` improves usable history but starts around late May or early June 2024, while daily fixtures start on 2023-06-19.
- A real default replacement should wait for a durable longer historical intraday source or a benchmark window aligned to verified minute-data availability.
- The daily Chan baseline remains stronger on raw average return in this fixture set.

## Full Verification

Fresh verification at close-out:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py tests/test_strategy_registry.py -q
```

Result: `26 passed in 0.47s`.

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
```

Result: `277 passed in 5.09s`.

```bash
npm --prefix frontend test
```

Result: `21 passed`, `101 passed`.

```bash
npm --prefix frontend run build
```

Result: TypeScript plus Vite production build succeeded.

## Screenshot Acceptance

Browser plugin path was attempted first, but the in-app Browser runtime failed before navigation with:

```text
Mcp error: -32602: js: codex/sandbox-state-meta: missing field `sandboxPolicy`
```

Per `docs/qa/headless-chrome-screenshots.md`, validation fell back to the repository headless Chrome/CDP path.

Standard React platform screenshots:

```bash
node scripts/capture_app_screenshots.mjs \
  --url http://localhost:5173 \
  --out-dir docs/qa/screenshots \
  --prefix 2026-06-21-chan-multilevel-60m-completion
```

Result:

- `docs/qa/screenshots/2026-06-21-chan-multilevel-60m-completion_desktop_1440.png` (`1440x1024`)
- `docs/qa/screenshots/2026-06-21-chan-multilevel-60m-completion_mobile_390.png` (`390x844`)

Interactive strategy-workshop check:

- Loaded `http://localhost:5173`.
- Entered `策略工坊`.
- Filtered and selected `缠论多级别反转` / `ChanMultiLevelReversalStrategy`.
- Verified DOM controls:
  - `确认级别`: options `60m`, `30m`; selected value `60m`.
  - `风控级别`: options `30m`, `15m`; selected value `30m`.
- Verified no relevant console `error`/`warn` entries from the interaction capture.
- Visually inspected screenshots and confirmed real rendered content, not a blank shell or framework overlay.

Result:

- `docs/qa/screenshots/2026-06-21-chan-multilevel-60m-completion_strategy-params-60m_desktop_1440.png` (`1440x1024`)
