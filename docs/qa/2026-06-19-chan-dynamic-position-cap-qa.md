# Chan Dynamic Position Cap QA

Date: 2026-06-19

## Scope

Implemented the C variant for `ChanStructureStrategy`:

- Buy target units can now be capped by `position_cap_mode`.
- Default mode is `risk`, which prevents add-on buys after the current position reaches the floating-loss budget.
- Optional `trend` and `trend_risk` modes also cap buy targets by Chan Core V2 trend context.
- Sell and reduction signals are not blocked by the cap.
- The strategy tracks `average_entry_price` internally and clears it on full exits.

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
position_cap_mode=risk
trend_cap_units=2
risk_drawdown_cap_pct=8.0
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

- `/tmp/chan_dynamic_position_cap_benchmark.csv`
- `/tmp/chan_dynamic_position_cap_benchmark.json`

| Stock | Final Equity | Return % | Benchmark % | Excess % | Max DD % | Trades | Win % | Profit Factor | Exposure % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | 104780.84 | 4.7808 | 155.5394 | -150.7586 | -4.6154 | 68 | 45.4545 | 1.3370 | 5.9397 |
| 五粮液 `000858/SZSE` | 97272.04 | -2.7280 | -52.8208 | 50.0928 | -4.4337 | 56 | 25.0000 | 0.6017 | 3.2318 |
| 中国平安 `601318/SSE` | 98023.55 | -1.9764 | 23.8525 | -25.8289 | -2.8425 | 68 | 38.2353 | 0.6924 | 2.9661 |
| 江苏金租 `600901/SSE` | 99907.29 | -0.0927 | 85.0153 | -85.1080 | -0.3171 | 79 | 35.8974 | 1.1002 | 0.3736 |
| 宝丰能源 `600989/SSE` | 100892.83 | 0.8928 | 87.6963 | -86.8035 | -1.0470 | 50 | 50.0000 | 1.9958 | 0.7983 |
| 兆易创新 `603986/SSE` | 157302.04 | 57.3020 | 459.7579 | -402.4559 | -6.7301 | 105 | 51.0204 | 3.1668 | 11.1927 |

Aggregate notes:

- Positive strategy returns: 3 of 6 fixtures.
- Worst strategy return: 五粮液 at `-2.7280%`.
- Best strategy return: 兆易创新 at `57.3020%`.
- Median strategy return: `0.4001%`.
- Average strategy return: `9.6964%`.
- Worst max drawdown: 兆易创新 at `-6.7301%`.
- Total trades across six fixtures: 426.

## Comparison To B Low-Confidence Gate

Baseline B results come from `docs/qa/2026-06-19-chan-low-confidence-gate-qa.md`.

| Stock | B Return % | C Return % | Return Change | B Trades | C Trades | Trade Change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | 5.2858 | 4.7808 | -0.5050 | 69 | 68 | -1 |
| 五粮液 `000858/SZSE` | -2.7280 | -2.7280 | 0.0000 | 56 | 56 | 0 |
| 中国平安 `601318/SSE` | -2.0745 | -1.9764 | 0.0981 | 69 | 68 | -1 |
| 江苏金租 `600901/SSE` | -0.0927 | -0.0927 | 0.0000 | 79 | 79 | 0 |
| 宝丰能源 `600989/SSE` | 0.8928 | 0.8928 | 0.0000 | 50 | 50 | 0 |
| 兆易创新 `603986/SSE` | 59.4539 | 57.3020 | -2.1519 | 109 | 105 | -4 |

Interpretation:

- C default reduces total trades from 432 to 426, but average return falls from `10.1229%` to `9.6964%`.
- The default is intentionally `risk`, not `trend_risk`, because a quick local mode check showed trend-based caps can misclassify context and materially reduce returns on the current fixtures.
- The floating-loss cap is useful as a risk-budget guard, but it is not yet a tuned alpha improvement.
- Next work should add signal attribution by T1/T2/T3/divergence/time-exit so later tuning can identify which signal family produces or destroys PnL.

## Verification

Completed for this QA record:

- `PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py -q` -> `62 passed`
- `PYTHONPATH=src python -m pytest` -> `159 passed`
- `cd frontend && npm test -- --run` -> `18 files / 89 tests passed`
- `cd frontend && npm run build` -> passed
- `git diff --check` -> no output
- Six-stock benchmark command above -> completed and wrote `/tmp/chan_dynamic_position_cap_benchmark.csv`

Browser acceptance:

- URL: `http://127.0.0.1:5173/`
- Title: `AI量化平台`
- Flow: app loads -> select `缠论结构策略` -> inspect C parameters -> change `动态仓位上限` from `risk` to `trend_risk` -> restore `risk`.
- Page identity, non-empty app content, no framework overlay, and console health passed.
- Console check: `tab.dev.logs({ levels: ["error", "warn"], limit: 50 })` returned no entries.
- Desktop screenshot: `/tmp/ai_trade_system_chan_dynamic_position_cap_desktop_params_scrolled.png`
- Mobile screenshot: `/tmp/ai_trade_system_chan_dynamic_position_cap_mobile_final.png`
