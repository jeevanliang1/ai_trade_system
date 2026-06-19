# Chan Low-Confidence Gate QA

Date: 2026-06-19

## Scope

Implemented the approved B variant for `ChanStructureStrategy`:

- Ordinary 二买/二卖 T2 signals are now low-confidence signals behind `low_confidence_gate`.
- Default gate is `divergence_or_trend`, which allows T2 through high score or compatible Chan Core V2 trend context.
- T1 背驰观察后的 armed confirmation bypasses the low-confidence gate.
- 三买/三卖 T3 and explicit BUY/SELL confirmation signals keep the existing certainty-based position sizing behavior.

This QA validates behavior and benchmark impact. It is not broad parameter optimization.

## Default Parameter Set

```text
symbol=<fixture symbol>
min_bars=60
lookback=160
min_stroke_bars=5
min_rebound_pct=0.03
min_signal_score=28.0
signal_mode=all
allowed_point_types=all
allowed_levels=all
max_holding_bars=15
watch_confirm_bars=20
low_confidence_gate=divergence_or_trend
low_confidence_min_score=32.0
range_max_units=1
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
- Requested source range: `20230619` to `20260619`
- Local fixture range observed: `2023-06-19` to `2026-06-18`

## Fixture Persistence

The benchmark uses the persisted six-stock qfq fixtures under the canonical data-manager layout.

| Stock | Fixture | Rows | Start | End |
| --- | --- | ---: | --- | --- |
| 中芯国际 `688981/SSE` | `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv` | 720 | 2023-06-19 | 2026-06-18 |
| 五粮液 `000858/SZSE` | `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |
| 中国平安 `601318/SSE` | `data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |
| 江苏金租 `600901/SSE` | `data/market/a_share/SSE/600901/600901_SSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |
| 宝丰能源 `600989/SSE` | `data/market/a_share/SSE/600989/600989_SSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |
| 兆易创新 `603986/SSE` | `data/market/a_share/SSE/603986/603986_SSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |

## Six-Stock Benchmark

Command shape:

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.analytics import calculate_backtest_metrics
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import read_bars_csv
from ai_trade_system.strategies.popular import ChanStructureStrategy

# Iterate the six fixture paths and run ChanStructureStrategy(code) with BacktestConfig().
PY
```

Raw artifacts:

- `/tmp/chan_low_confidence_gate_benchmark.csv`
- `/tmp/chan_low_confidence_gate_benchmark.json`

| Stock | Final Equity | Return % | Benchmark % | Excess % | Max DD % | Trades | Win % | Profit Factor | Exposure % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | 105285.81 | 5.2858 | 155.5394 | -150.2536 | -4.2248 | 69 | 47.0588 | 1.3480 | 5.9260 |
| 五粮液 `000858/SZSE` | 97272.04 | -2.7280 | -52.8208 | 50.0928 | -4.4337 | 56 | 25.0000 | 0.6017 | 3.2318 |
| 中国平安 `601318/SSE` | 97925.52 | -2.0745 | 23.8525 | -25.9270 | -2.9396 | 69 | 32.3529 | 0.6267 | 3.0005 |
| 江苏金租 `600901/SSE` | 99907.29 | -0.0927 | 85.0153 | -85.1080 | -0.3171 | 79 | 35.8974 | 1.1002 | 0.3736 |
| 宝丰能源 `600989/SSE` | 100892.83 | 0.8928 | 87.6963 | -86.8035 | -1.0470 | 50 | 50.0000 | 1.9958 | 0.7983 |
| 兆易创新 `603986/SSE` | 159453.90 | 59.4539 | 459.7579 | -400.3040 | -6.6854 | 109 | 50.9434 | 3.1968 | 11.2700 |

Aggregate notes:

- Positive strategy returns: 3 of 6 fixtures.
- Worst strategy return: 五粮液 at `-2.7280%`.
- Best strategy return: 兆易创新 at `59.4539%`.
- Median strategy return: `0.4001%`.
- Average strategy return: `10.1229%`.
- Worst max drawdown: 兆易创新 at `-6.6854%`.
- Total trades across six fixtures: 432.

## Comparison To A Position-Sizing Variant

Baseline A results come from `docs/qa/2026-06-19-chan-position-sizing-qa.md`.

| Stock | A Return % | B Return % | Return Change | A Trades | B Trades | Trade Change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | 4.5061 | 5.2858 | 0.7797 | 73 | 69 | -4 |
| 五粮液 `000858/SZSE` | -5.5352 | -2.7280 | 2.8072 | 64 | 56 | -8 |
| 中国平安 `601318/SSE` | -2.7167 | -2.0745 | 0.6422 | 73 | 69 | -4 |
| 江苏金租 `600901/SSE` | -0.0877 | -0.0927 | -0.0050 | 79 | 79 | 0 |
| 宝丰能源 `600989/SSE` | 0.7505 | 0.8928 | 0.1423 | 56 | 50 | -6 |
| 兆易创新 `603986/SSE` | 48.4322 | 59.4539 | 11.0217 | 119 | 109 | -10 |

Interpretation:

- B reduced total trades from 464 to 432 while improving average return from `7.5582%` to `10.1229%`.
- The gate improved five of six fixtures by suppressing low-certainty T2 churn or requiring stronger context.
- 江苏金租 was effectively unchanged and slightly worse on return.
- 兆易创新 return improved materially, but worst drawdown deepened from `-6.4968%` to `-6.6854%`, which supports a follow-up C variant around dynamic position caps or risk budget.

## Verification

Completed before this QA file was written:

- `PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py -q` -> `55 passed`
- `PYTHONPATH=src python -m pytest` -> `152 passed`
- `cd frontend && npm test -- --run` -> `18 files / 89 tests passed`
- `cd frontend && npm run build` -> passed
- `git diff --check` -> no output
- Six-stock benchmark command above -> completed and wrote `/tmp/chan_low_confidence_gate_benchmark.csv`

Browser acceptance:

- URL: `http://127.0.0.1:5173/`
- Page title: `AI量化平台`
- Flow: app loads -> select `缠论结构策略` -> parameter panel shows `低确定性门控`, `低确定性放行分`, and `震荡区最大仓位`.
- Console errors/warnings: none.
- Desktop screenshot: `/tmp/ai_trade_system_chan_low_confidence_gate_desktop_params.png`
- Mobile screenshot: `/tmp/ai_trade_system_chan_low_confidence_gate_mobile_params.png`
