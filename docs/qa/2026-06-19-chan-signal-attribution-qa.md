# Chan Signal Attribution QA

Date: 2026-06-19

## Scope

Implemented signal attribution for backtest results so Chan strategy tuning can compare trade count, PnL, win rate, and realized drawdown by signal family.

This is an observability and analysis change. It does not change `ChanStructureStrategy` signal generation, sizing, broker execution, or equity math.

## Attribution Families

| Family | Label | Source |
| --- | --- | --- |
| `t1_divergence` | T1背驰 | `T1_DIVERGENCE` signal reasons |
| `t2` | T2二买二卖 | `_T2` or second-buy/second-sell reasons |
| `t3` | T3三买三卖 | `_T3` or third-buy/third-sell reasons |
| `divergence_confirm` | 背驰确认 | `BUY_CONFIRM` / `SELL_CONFIRM` / `ARMED_CONFIRM` reasons |
| `time_exit` | 时间退出 | `TIME_EXIT` or `time_exit` reasons |
| `other` | 其他信号 | fallback for non-Chan reasons |

`signal_attribution` reports both:

- Entry perspective: realized PnL, win rate, profit factor, and realized drawdown credited to the buy signal family.
- Exit perspective: the same metrics credited to the sell signal family.

Realized drawdown is calculated from each family's cumulative realized PnL curve divided by initial cash. It is not a full causal mark-to-market attribution model.

## Fixed Six-Stock Benchmark

Parameter set is unchanged from the C dynamic position cap default:

```text
ChanStructureStrategy(symbol=<fixture symbol>)
position_cap_mode=risk
risk_drawdown_cap_pct=8.0
trend_cap_units=2
low_confidence_gate=divergence_or_trend
max_holding_bars=15
trade_size=100
```

Backtest assumptions:

- Initial cash: `100000`
- Commission rate: `0.0003`
- Slippage: `0.01`
- Max order cash: `50000`
- Adjustment: `qfq`
- Requested source range: `20230619` to `20260619`
- Local fixture range observed: `2023-06-19` to `2026-06-18`

Raw artifacts:

- `/tmp/chan_signal_attribution_benchmark.csv`
- `/tmp/chan_signal_attribution_rows.csv`
- `/tmp/chan_signal_attribution_benchmark.json`

| Stock | Return % | Max DD % | Trades | Attributed Trades | Win % | Profit Factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | 4.7808 | -4.6154 | 68 | 68 | 45.4545 | 1.3370 |
| 五粮液 `000858/SZSE` | -2.7280 | -4.4337 | 56 | 56 | 25.0000 | 0.6017 |
| 中国平安 `601318/SSE` | -1.9764 | -2.8425 | 68 | 68 | 38.2353 | 0.6924 |
| 江苏金租 `600901/SSE` | -0.0927 | -0.3171 | 79 | 79 | 35.8974 | 1.1002 |
| 宝丰能源 `600989/SSE` | 0.8928 | -1.0470 | 50 | 50 | 50.0000 | 1.9958 |
| 兆易创新 `603986/SSE` | 57.3020 | -6.7301 | 105 | 105 | 51.0204 | 3.1668 |

Aggregate:

- Positive strategy returns: 3 of 6 fixtures.
- Average strategy return: `9.6964%`.
- Median strategy return: `0.4001%`.
- Total trades: 426.
- Attributed trades: 426.

These return and trade totals match `docs/qa/2026-06-19-chan-dynamic-position-cap-qa.md`, confirming attribution did not alter trading behavior.

## Six-Stock Family Rollup

| Family | Label | Trades | Entry PnL | Exit PnL |
| --- | --- | ---: | ---: | ---: |
| `t2` | T2二买二卖 | 261 | 19708.89 | -18290.22 |
| `t3` | T3三买三卖 | 98 | 23823.57 | -545.15 |
| `time_exit` | 时间退出 | 67 | 0.00 | 62367.85 |

Interpretation:

- T3 entries had the strongest entry-family realized PnL in this six-stock fixture run.
- T2 entries were positive overall but had materially negative exit-family PnL, making them a useful next tuning target.
- Time exits dominated exit-family realized PnL because many profitable positions were closed by the max-holding exit.

## Per-Stock Attribution Snapshot

| Stock | Family | Trades | Entry PnL | Exit PnL | Entry DD % | Exit DD % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `688981` | T2二买二卖 | 42 | 1208.05 | -8053.79 | -3.6849 | -9.3443 |
| `688981` | T3三买三卖 | 15 | 2559.70 | 0.00 | -2.4761 | 0.0000 |
| `688981` | 时间退出 | 11 | 0.00 | 11821.54 | 0.0000 | -0.8418 |
| `000858` | T2二买二卖 | 33 | -6239.65 | -3731.20 | -6.2396 | -3.7312 |
| `000858` | T3三买三卖 | 18 | 3511.69 | -545.15 | 0.0000 | -0.9289 |
| `000858` | 时间退出 | 5 | 0.00 | 1548.39 | 0.0000 | -1.9025 |
| `601318` | T2二买二卖 | 43 | -476.88 | -3824.62 | -1.4398 | -3.9313 |
| `601318` | T3三买三卖 | 13 | -1499.56 | 0.00 | -1.7608 | 0.0000 |
| `601318` | 时间退出 | 12 | 0.00 | 1848.18 | 0.0000 | -0.3027 |
| `600901` | T2二买二卖 | 48 | 116.45 | -289.87 | -0.0734 | -0.2899 |
| `600901` | T3三买三卖 | 17 | -180.97 | 0.00 | -0.2316 | 0.0000 |
| `600901` | 时间退出 | 14 | 0.00 | 225.36 | 0.0000 | -0.0328 |
| `600989` | T2二买二卖 | 34 | 1057.28 | -222.97 | -0.4543 | -0.2813 |
| `600989` | 时间退出 | 13 | 0.00 | 1115.80 | 0.0000 | -0.3398 |
| `600989` | T3三买三卖 | 3 | -164.45 | 0.00 | -0.2290 | 0.0000 |
| `603986` | T2二买二卖 | 61 | 24043.64 | -2167.77 | -5.1062 | -6.1269 |
| `603986` | T3三买三卖 | 32 | 19597.16 | 0.00 | -6.1269 | 0.0000 |
| `603986` | 时间退出 | 12 | 0.00 | 45808.58 | 0.0000 | -5.1062 |

## Verification

Completed for this QA record:

- `PYTHONPATH=src python -m pytest tests/test_backtest_and_paper.py tests/test_analytics.py tests/test_api_routes.py -q` -> `28 passed`
- `cd frontend && npm test -- --run BacktestPage.test.tsx` -> `9 passed`
- Six-stock benchmark command -> completed and wrote `/tmp/chan_signal_attribution_benchmark.csv`
- `PYTHONPATH=src python -m pytest` -> `162 passed`
- `cd frontend && npm test -- --run` -> `18 files / 89 tests passed`
- `cd frontend && npm run build` -> passed
- Browser acceptance on `http://127.0.0.1:5173/`:
  - Opened React platform, entered Backtest Center, ran the demo backtest, and verified the new `信号归因` panel rendered with attribution rows.
  - Console health: no browser console logs were observed during the desktop acceptance run.
  - Desktop screenshot: `/tmp/ai_trade_system_signal_attribution_desktop_table_coord.png`
  - Mobile screenshot: `/tmp/ai_trade_system_signal_attribution_mobile.png`
