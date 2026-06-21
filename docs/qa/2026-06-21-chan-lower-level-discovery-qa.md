# Chan Lower-Level Discovery QA

## Scope

Implemented offensive multi-level discovery for `ChanMultiLevelReversalStrategy`.

New parameter:

```python
entry_mode="daily_confirmed"        # existing default, daily buy point first
entry_mode="lower_level_discovery"  # new offensive mode, lower-level buy can discover early entries
```

The existing default remains `daily_confirmed`. The new mode lets a confirm-level buy signal open or add to a position when:

- the current daily bar has no high-score sell signal,
- the risk timeframe has no high-score sell signal,
- the lower-level signal is available at or before the current daily session close.

Lower-level risk exits still run before daily exits and can reduce or clear existing positions according to `minute_sell_mode`.

## TDD Evidence

Red checks before implementation:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Result: `4 failed, 12 passed`; failures were expected because `entry_mode` was not accepted.

```bash
python -m pytest tests/test_strategy_registry.py::test_chan_multilevel_reversal_strategy_is_registered_with_guidance -q
```

Result: `1 failed`; `entry_mode` was absent from registry metadata.

Green checks after implementation:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Result: `16 passed`.

```bash
python -m pytest tests/test_strategy_registry.py::test_chan_multilevel_reversal_strategy_is_registered_with_guidance -q
```

Result: `1 passed`.

Combined targeted verification:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py tests/test_strategy_registry.py -q
```

Result: `29 passed`.

## Fixture Preparation

Expanded benchmark universe:

- `688981/SSE` 中芯国际
- `000858/SZSE` 五粮液
- `601318/SSE` 中国平安
- `600901/SSE` 江苏金租
- `600989/SSE` 宝丰能源
- `603986/SSE` 兆易创新
- `688733/SSE` 壹石通
- `688072/SSE` 拓荆科技

Data update for the two new symbols:

- `688733/SSE daily`: existing local data used; incremental AKShare daily refresh failed, so the local CSV was retained.
- `688733/SSE 60m/30m/15m`: updated, `1970` rows each.
- `688072/SSE daily`: existing local data used; incremental AKShare daily refresh failed, so the local CSV was retained.
- `688072/SSE 60m/30m/15m`: updated, `1970` rows each.

Coverage uses actual CSV rows, not manifest-only metadata.

| Symbol | Name | Daily rows/range | 60m rows/range | 30m rows/range | 15m rows/range |
| --- | --- | --- | --- | --- | --- |
| `688981/SSE` | 中芯国际 | 720: `2023-06-19` to `2026-06-18` | 1970: `2024-05-29 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-05 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `000858/SZSE` | 五粮液 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `601318/SSE` | 中国平安 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `600901/SSE` | 江苏金租 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `600989/SSE` | 宝丰能源 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `603986/SSE` | 兆易创新 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `688733/SSE` | 壹石通 | 483: `2024-06-21` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |
| `688072/SSE` | 拓荆科技 | 726: `2023-06-19` to `2026-06-18` | 1970: `2024-06-06 14:00:00` to `2026-06-18 15:00:00` | 1970: `2025-06-13 14:30:00` to `2026-06-18 15:00:00` | 1970: `2025-12-11 14:45:00` to `2026-06-18 15:00:00` |

## Benchmark Method

Window: `2023-06-19` to `2026-06-19`.

`688733/SSE` uses its available daily CSV range, `2024-06-21` to `2026-06-18`, because the local CSV does not contain earlier daily rows.

Engine: shared `run_backtest` and `calculate_backtest_metrics` with `BacktestConfig()` defaults:

- Initial cash: `100000`
- Commission rate: `0.0003`
- Slippage: `0.01`
- Max order cash: `50000`
- Adjustment: `qfq`

To avoid repeated Chan analysis cost, the benchmark precomputed daily, `60m`, and `30m` `ChanCoreV2Analyzer` results once per symbol and replayed those exact results through the strategy variants.

## Aggregate Results

| Variant | Avg return % | Median return % | Avg benchmark return % | Avg excess % | Avg max DD % | Total trades | Avg win rate % | Avg profit factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `daily_chan_structure_default` | 6.7631 | 0.4001 | 152.7850 | -146.0219 | -5.4286 | 581 | 38.8215 | 1.2930 |
| `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | 1.2157 | 0.0645 | 152.7850 | -151.5694 | -4.3366 | 339 | 44.0651 | 1.1636 |
| `ml_lower_discovery_60_30_skip_c28_r24_reduce` | 2.3259 | 0.2530 | 152.7850 | -150.4591 | -5.1180 | 553 | 45.3255 | 1.4383 |
| `ml_lower_discovery_60_30_skip_c32_r28_exit` | 0.9023 | -0.1630 | 152.7850 | -151.8827 | -3.4981 | 179 | 46.8155 | 3.2402 |

## Per-Symbol Results

| Symbol | Variant | Return % | Benchmark return % | Excess % | Max DD % | Trades | Win rate % | Profit factor |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `688981/SSE` | `daily_chan_structure_default` | 4.7808 | 155.5394 | -150.7586 | -4.6154 | 68 | 45.4545 | 1.3370 |
| `688981/SSE` | `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | 0.1123 | 155.5394 | -155.4271 | -5.6900 | 48 | 50.0000 | 0.8297 |
| `688981/SSE` | `ml_lower_discovery_60_30_skip_c28_r24_reduce` | 0.7925 | 155.5394 | -154.7469 | -6.7701 | 73 | 51.7241 | 1.5917 |
| `688981/SSE` | `ml_lower_discovery_60_30_skip_c32_r28_exit` | -4.8409 | 155.5394 | -160.3803 | -4.9158 | 15 | 20.0000 | 0.0032 |
| `000858/SZSE` | `daily_chan_structure_default` | -2.7280 | -52.8208 | 50.0928 | -4.4337 | 56 | 25.0000 | 0.6017 |
| `000858/SZSE` | `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | -0.4802 | -52.8208 | 52.3406 | -1.0669 | 14 | 28.5714 | 0.3443 |
| `000858/SZSE` | `ml_lower_discovery_60_30_skip_c28_r24_reduce` | -1.9833 | -52.8208 | 50.8375 | -5.0354 | 34 | 31.2500 | 0.9712 |
| `000858/SZSE` | `ml_lower_discovery_60_30_skip_c32_r28_exit` | -0.4755 | -52.8208 | 52.3453 | -4.2468 | 14 | 40.0000 | 2.2724 |
| `601318/SSE` | `daily_chan_structure_default` | -1.9764 | 23.8525 | -25.8289 | -2.8425 | 68 | 38.2353 | 0.6924 |
| `601318/SSE` | `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | -2.7343 | 23.8525 | -26.5868 | -2.8098 | 28 | 30.7692 | 0.3597 |
| `601318/SSE` | `ml_lower_discovery_60_30_skip_c28_r24_reduce` | 0.3771 | 23.8525 | -23.4754 | -2.8373 | 48 | 38.0952 | 1.4578 |
| `601318/SSE` | `ml_lower_discovery_60_30_skip_c32_r28_exit` | 1.9478 | 23.8525 | -21.9047 | -2.4375 | 22 | 55.5556 | 5.1438 |
| `600901/SSE` | `daily_chan_structure_default` | -0.0927 | 85.0153 | -85.1080 | -0.3171 | 79 | 35.8974 | 1.1002 |
| `600901/SSE` | `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | 0.0412 | 85.0153 | -84.9741 | -0.1036 | 25 | 66.6667 | 1.7771 |
| `600901/SSE` | `ml_lower_discovery_60_30_skip_c28_r24_reduce` | 0.1288 | 85.0153 | -84.8865 | -0.1078 | 38 | 58.8235 | 1.5660 |
| `600901/SSE` | `ml_lower_discovery_60_30_skip_c32_r28_exit` | 0.1494 | 85.0153 | -84.8659 | -0.1065 | 21 | 77.7778 | 8.4526 |
| `600989/SSE` | `daily_chan_structure_default` | 0.8928 | 87.6963 | -86.8035 | -1.0470 | 50 | 50.0000 | 1.9958 |
| `600989/SSE` | `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | 0.0879 | 87.6963 | -87.6084 | -0.5868 | 36 | 52.9412 | 1.2470 |
| `600989/SSE` | `ml_lower_discovery_60_30_skip_c28_r24_reduce` | -0.6762 | 87.6963 | -88.3725 | -1.0812 | 80 | 44.4444 | 0.7791 |
| `600989/SSE` | `ml_lower_discovery_60_30_skip_c32_r28_exit` | -1.2007 | 87.6963 | -88.8970 | -1.3030 | 26 | 30.0000 | 0.2604 |
| `603986/SSE` | `daily_chan_structure_default` | 57.3020 | 459.7579 | -402.4559 | -6.7301 | 105 | 51.0204 | 3.1668 |
| `603986/SSE` | `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | 25.1519 | 459.7579 | -434.6060 | -6.5990 | 54 | 62.5000 | 3.4006 |
| `603986/SSE` | `ml_lower_discovery_60_30_skip_c28_r24_reduce` | 23.7535 | 459.7579 | -436.0044 | -6.6779 | 81 | 58.3333 | 2.9354 |
| `603986/SSE` | `ml_lower_discovery_60_30_skip_c32_r28_exit` | 14.1110 | 459.7579 | -445.6469 | -5.0494 | 30 | 50.0000 | 6.3709 |
| `688733/SSE` | `daily_chan_structure_default` | 1.7260 | 177.6747 | -175.9487 | -1.8659 | 61 | 26.6667 | 0.5310 |
| `688733/SSE` | `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | 1.0147 | 177.6747 | -176.6600 | -1.9934 | 56 | 30.7692 | 0.7555 |
| `688733/SSE` | `ml_lower_discovery_60_30_skip_c28_r24_reduce` | 1.6991 | 177.6747 | -175.9756 | -2.5421 | 96 | 39.0244 | 1.1492 |
| `688733/SSE` | `ml_lower_discovery_60_30_skip_c32_r28_exit` | 2.7626 | 177.6747 | -174.9121 | -2.6753 | 33 | 58.3333 | 1.2691 |
| `688072/SSE` | `daily_chan_structure_default` | -5.7994 | 285.5650 | -291.3644 | -21.5769 | 94 | 38.2979 | 0.9193 |
| `688072/SSE` | `ml_daily_confirmed_60_30_skip_c28_r24_reduce` | -13.4682 | 285.5650 | -299.0332 | -15.8431 | 78 | 30.3030 | 0.5950 |
| `688072/SSE` | `ml_lower_discovery_60_30_skip_c28_r24_reduce` | -5.4840 | 285.5650 | -291.0490 | -15.8921 | 103 | 40.9091 | 1.0558 |
| `688072/SSE` | `ml_lower_discovery_60_30_skip_c32_r28_exit` | -5.2353 | 285.5650 | -290.8003 | -7.2505 | 18 | 42.8571 | 2.1490 |

## Interpretation

- The offensive discovery mode does what it was intended to do: it restores trade frequency close to daily-only (`553` trades versus daily `581`) and far above conservative multi-level (`339` trades).
- Offensive discovery improves over conservative multi-level on average return: `2.3259%` versus `1.2157%`.
- Offensive discovery also improves win rate and profit factor versus both daily and conservative multi-level in this 8-stock matrix.
- Raw average return is still below the daily baseline: `2.3259%` versus `6.7631%`.
- The trade-off is drawdown: offensive discovery average max drawdown is `-5.1180%`, closer to daily `-5.4286%` and worse than conservative multi-level `-4.3366%`.
- The stricter `exit` variant has the best drawdown and profit factor but too few trades and weaker average return; it is defensive, not the requested discovery posture.

## Decision

Keep `entry_mode="daily_confirmed"` as the default for backward compatibility.

Use this as the current offensive experimental preset:

```python
ChanMultiLevelReversalStrategy(
    entry_mode="lower_level_discovery",
    confirm_timeframe="60m",
    risk_timeframe="30m",
    minute_missing_policy="skip_entry",
    lower_level_policy="confirm_then_risk",
    min_confirm_score=28,
    min_risk_score=24,
    minute_sell_mode="reduce",
)
```

This matches the user's requested direction better than the old conservative mode because it can find lower-level opportunities before a daily buy point appears and materially increases trades.

## Remaining Risk

- `688733/SSE` daily fixture starts on `2024-06-21`, so it has a shorter daily benchmark span than the other stocks.
- AKShare public minute fixtures still begin around 2024-05/06 for `60m`, 2025-06 for `30m`, and 2025-12 for `15m`; they do not fully cover the three-year daily window.
- Offensive discovery increases drawdown relative to conservative multi-level. It should remain an explicit preset until more minute-history coverage and more parameter sweeps are available.

## Full Verification

Targeted strategy and registry verification:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py tests/test_strategy_registry.py -q
```

Result: `29 passed`.

Full Python test suite:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
```

Result: `280 passed in 6.47s`.

Frontend test suite:

```bash
npm --prefix frontend test
```

Result: `21 passed`, `101 passed`, duration `4.18s`.

Frontend production build:

```bash
npm --prefix frontend run build
```

Result: succeeded.

Local validation server was stopped after screenshot capture. Ports `5173` and `8000` had no remaining listening process.

## Screenshot Acceptance

The Browser plugin attempt was blocked before navigation with:

```text
Mcp error: -32602: js: codex/sandbox-state-meta: missing field sandboxPolicy
```

Fallback used local headless Chrome/Playwright against the real React + FastAPI surface from `./scripts/run_app.sh`.

Captured nonblank acceptance screenshots:

- `docs/qa/screenshots/2026-06-21-chan-lower-level-discovery_desktop_1440.png` (`1440x1024`)
- `docs/qa/screenshots/2026-06-21-chan-lower-level-discovery_mobile_390.png` (`390x844`)
- `docs/qa/screenshots/2026-06-21-chan-lower-level-discovery_strategy-entry-mode_desktop_1440.png` (`1440x1024`)

Interactive strategy-parameter validation confirmed the new entry mode is visible and selectable:

```json
{
  "value": "lower_level_discovery",
  "options": ["daily_confirmed", "lower_level_discovery"],
  "text": true
}
```

Browser console events during the interactive check: `[]`.
