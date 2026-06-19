# Chan STAR Market Top-20 Backtest

Date: 2026-06-19

## Scope

Expanded the current `ChanStructureStrategy` observation set from the fixed six-stock benchmark to a STAR Market sample, after the latest fixed benchmark suggested the strategy may behave better on 科创板 names.

This is a data and analysis run only. No strategy logic, sizing logic, or API/UI code changed.

## Selection Method

Hot-stock definition used for this run:

1. Pull the current STAR Market snapshot with AKShare `stock_zh_kcb_spot`.
2. Rank by spot `成交额` descending.
3. Persist qfq daily bars under `data/market/a_share/SSE/{code}/`.
4. Keep the highest-ranked 20 stocks with at least 600 daily bars in the local qfq fixture.

The first 20 by turnover included `688820` 盛合晶微, but it only had 40 bars from `2026-04-21` to `2026-06-18`, so it was excluded for near-three-year comparability. The next eligible turnover-ranked stock, `688110` 东芯股份, was included.

Source references used for the selection/data route:

- Shanghai Stock Exchange STAR active-stock page: https://www.sse.com.cn/market/stockdata/activity/star/
- AKShare stock data documentation: https://akshare.akfamily.xyz/data/stock/stock.html
- CSI STAR 50 factsheet for representative STAR Market context: https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000688factsheet.pdf

## Data Persistence

- Requested range: `20230619` to `20260619`
- Effective latest available qfq bar: `2026-06-18`
- Reason: the public daily-bar sources did not return a completed `2026-06-19` bar during this run.
- Update result: 20 selected stocks available locally, 15 newly updated in the first pass, 5 already fresh, 0 failed.
- Canonical path pattern: `data/market/a_share/SSE/{code}/{code}_SSE_daily_qfq_latest.csv`

Raw local run artifacts:

- `/tmp/kechuang_top20_eligible_selection.csv`
- `/tmp/kechuang_top20_candidate_updates.csv`
- `/tmp/kechuang_top20_chan_backtest.csv`
- `/tmp/kechuang_top20_chan_signal_attribution.csv`
- `/tmp/kechuang_top20_chan_family_rollup.csv`
- `/tmp/kechuang_top20_chan_summary.json`

## Strategy Parameters

Used the current default `ChanStructureStrategy(symbol=<code>)` settings:

```text
min_signal_score=28.0
allowed_point_types=all
allowed_levels=all
max_holding_bars=15
watch_confirm_bars=20
low_confidence_gate=divergence_or_trend
low_confidence_min_score=32.0
position_cap_mode=risk
risk_drawdown_cap_pct=8.0
trend_cap_units=2
low_confidence_units=1
divergence_confirm_units=2
high_confidence_units=3
sell_confirm_units=1
trade_size=100
```

Backtest assumptions:

- Initial cash: `100000`
- Commission rate: `0.0003`
- Slippage: `0.01`
- Max order cash: `50000`
- Adjustment: `qfq`

## Summary

| Metric | STAR Top-20 |
| --- | ---: |
| Positive strategy returns | 17 / 20 |
| Positive excess returns vs buy-and-hold | 0 / 20 |
| Average strategy return | 17.4156% |
| Median strategy return | 13.0903% |
| Average benchmark return | 448.9798% |
| Median benchmark return | 327.4103% |
| Average excess return | -431.5641% |
| Median excess return | -311.4483% |
| Average max drawdown | -8.0902% |
| Worst max drawdown | -21.5769% |
| Total trades | 1515 |
| Attributed trades | 1515 |

Comparison to the fixed six-stock benchmark recorded in `docs/qa/2026-06-19-chan-signal-attribution-qa.md`:

- Absolute return improved: STAR Top-20 average `17.4156%` vs fixed six-stock average `9.6964%`.
- Hit rate improved: STAR Top-20 positive returns `17/20` vs fixed six-stock `3/6`.
- Median return improved: STAR Top-20 `13.0903%` vs fixed six-stock `0.4001%`.
- Relative performance did not improve: all 20 STAR names underperformed simple buy-and-hold over this high-beta window.

## Stock-Level Results

| Rank | Stock | Bars | Range | Strategy Return % | Benchmark % | Excess % | Max DD % | Trades | Win % | Profit Factor |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 寒武纪 `688256` | 726 | 2023-06-19..2026-06-18 | 27.3864 | 845.3531 | -817.9667 | -9.5949 | 46 | 59.0909 | 3.8775 |
| 2 | 澜起科技 `688008` | 726 | 2023-06-19..2026-06-18 | 15.8283 | 342.9673 | -327.1390 | -5.9345 | 71 | 32.3529 | 3.4935 |
| 3 | 佰维存储 `688525` | 726 | 2023-06-19..2026-06-18 | 42.4420 | 286.9739 | -244.5319 | -8.5720 | 76 | 56.7568 | 4.8062 |
| 4 | 海光信息 `688041` | 716 | 2023-06-19..2026-06-18 | 27.6290 | 311.8533 | -284.2243 | -6.7172 | 91 | 43.1818 | 1.9836 |
| 5 | 中芯国际 `688981` | 720 | 2023-06-19..2026-06-18 | 4.7808 | 155.5394 | -150.7586 | -4.6154 | 68 | 45.4545 | 1.3370 |
| 6 | 中微公司 `688012` | 717 | 2023-06-19..2026-06-18 | 7.6426 | 219.9431 | -212.3005 | -10.2118 | 98 | 37.7778 | 1.9528 |
| 7 | 芯原股份 `688521` | 716 | 2023-06-19..2026-06-18 | -0.2308 | 212.0018 | -212.2326 | -11.2859 | 80 | 35.8974 | 1.0507 |
| 8 | 绿的谐波 `688017` | 726 | 2023-06-19..2026-06-18 | 11.3557 | 161.7126 | -150.3569 | -13.0628 | 96 | 38.6364 | 1.8065 |
| 9 | 源杰科技 `688498` | 726 | 2023-06-19..2026-06-18 | 4.3079 | 637.4554 | -633.1475 | -7.5533 | 78 | 41.0256 | 1.2795 |
| 10 | 华虹宏力 `688347` | 683 | 2023-08-07..2026-06-18 | 10.0759 | 425.0614 | -414.9855 | -4.6235 | 57 | 46.4286 | 1.7528 |
| 11 | 拓荆科技 `688072` | 726 | 2023-06-19..2026-06-18 | -5.7994 | 285.5650 | -291.3644 | -21.5769 | 94 | 38.2979 | 0.9193 |
| 12 | 长光华芯 `688048` | 726 | 2023-06-19..2026-06-18 | 62.5121 | 234.2764 | -171.7643 | -8.4412 | 97 | 45.6522 | 3.8936 |
| 13 | 沪硅产业 `688126` | 716 | 2023-06-19..2026-06-18 | -1.5582 | 48.6611 | -50.2193 | -2.3114 | 52 | 20.8333 | 0.6898 |
| 14 | 普冉股份 `688766` | 716 | 2023-06-19..2026-06-18 | 31.0620 | 860.1302 | -829.0682 | -8.8538 | 59 | 48.2759 | 1.9188 |
| 15 | 仕佳光子 `688313` | 717 | 2023-06-19..2026-06-18 | 1.0497 | 756.2225 | -755.1728 | -7.9154 | 60 | 32.1429 | 1.1941 |
| 16 | 中船特气 `688146` | 726 | 2023-06-19..2026-06-18 | 28.7059 | 736.3971 | -707.6912 | -3.7415 | 62 | 40.0000 | 10.9652 |
| 17 | 生益电子 `688183` | 726 | 2023-06-19..2026-06-18 | 23.4832 | 1061.9128 | -1038.4296 | -2.7768 | 81 | 43.5897 | 2.6690 |
| 18 | 盛科通信 `688702` | 665 | 2023-09-14..2026-06-18 | 8.9891 | 439.2000 | -430.2109 | -7.8952 | 76 | 48.6486 | 1.3776 |
| 19 | 精智达 `688627` | 707 | 2023-07-18..2026-06-18 | 33.8258 | 647.7870 | -613.9612 | -11.3692 | 91 | 52.3810 | 1.7247 |
| 20 | 东芯股份 `688110` | 723 | 2023-06-19..2026-06-18 | 14.8248 | 310.5823 | -295.7575 | -4.7504 | 82 | 46.1538 | 2.2870 |

## Signal Family Rollup

| Family | Label | Trades | Buy | Sell | Entry Closed | Entry PnL | Exit Closed | Exit PnL |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `t2` | T2二买二卖 | 1096 | 590 | 506 | 573 | 213947.58 | 506 | -139548.02 |
| `t3` | T3三买三卖 | 219 | 155 | 64 | 223 | 66397.25 | 64 | 5831.33 |
| `time_exit` | 时间退出 | 199 | 0 | 199 | 0 | 0.00 | 227 | 417419.05 |
| `divergence_confirm` | 背驰确认 | 1 | 1 | 0 | 1 | 3357.51 | 0 | 0.00 |

## Interpretation

The user hypothesis is partly supported:

- On absolute returns, the current Chan strategy looks more suitable for these high-volatility STAR Market names than for the mixed six-stock fixture set.
- The strategy avoided catastrophic drawdowns while participating in many rallies; average drawdown was about `-8.09%`.
- It is still too defensive for a strong 科创板 bull window. The buy-and-hold benchmark was extremely strong across the sample, and the strategy produced negative excess return for every selected stock.

Implication for the next strategy iteration:

- If the goal is absolute-return robustness, the STAR Market universe is a useful target universe for this strategy.
- If the goal is beating high-beta 科创板 buy-and-hold, the strategy needs a trend-persistence / add-on module: hold winners longer, reduce time exits during strong trend states, and allow higher caps for confirmed T3 or Chan Core V2 uptrend lifecycle states.

## Verification

Completed:

- Pulled and persisted qfq daily data for the selected STAR Market candidates via `data_manager.update_stock_data`.
- Excluded short-history `688820` and selected `688110` to keep 20 near-three-year samples.
- Ran 20-stock `ChanStructureStrategy` default-parameter backtests with `PYTHONPATH=src`.
- Wrote raw CSV/JSON artifacts under `/tmp/`.
- Created this QA record.

Not run:

- `python -m pytest`: no code or strategy logic changed.
- Browser screenshot: no browser-renderable surface changed for this analysis-only run.
