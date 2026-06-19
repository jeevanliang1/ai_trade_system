# Chan Structure Position Sizing QA

Date: 2026-06-19

## Scope

Implemented the approved A variant for `ChanStructureStrategy`:

- 二买/二卖 are low-certainty position adjustments.
- 底/顶背驰 confirmation raises certainty before changing target units.
- 三买/三卖 are high-certainty add/clear signals.
- Strategy state is now integer `position_units`; `in_position` remains a compatibility boolean property.

This QA is baseline validation for the new semantics, not parameter optimization.

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

The four newly requested benchmark stocks were pulled with `update_stock_data(...)` and persisted under the existing data-manager layout. The CSV fixture files are local data artifacts and are ignored by git via `data/*`.

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

- `/tmp/chan_position_sizing_benchmark.csv`
- `/tmp/chan_position_sizing_benchmark.json`

| Stock | Final Equity | Return % | Benchmark % | Excess % | Max DD % | Trades | Win % | Profit Factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | 104506.06 | 4.5061 | 155.5394 | -151.0333 | -4.2558 | 73 | 47.2222 | 1.2521 |
| 五粮液 `000858/SZSE` | 94464.78 | -5.5352 | -52.8208 | 47.2856 | -5.9423 | 64 | 25.8065 | 0.2469 |
| 中国平安 `601318/SSE` | 97283.34 | -2.7167 | 23.8525 | -26.5692 | -2.9584 | 73 | 30.5556 | 0.5267 |
| 江苏金租 `600901/SSE` | 99912.29 | -0.0877 | 85.0153 | -85.1030 | -0.3241 | 79 | 35.8974 | 1.1109 |
| 宝丰能源 `600989/SSE` | 100750.50 | 0.7505 | 87.6963 | -86.9458 | -1.0484 | 56 | 44.4444 | 1.7195 |
| 兆易创新 `603986/SSE` | 148432.25 | 48.4322 | 459.7579 | -411.3257 | -6.4968 | 119 | 46.5517 | 2.5416 |

Aggregate notes:

- Positive strategy returns: 3 of 6 fixtures.
- Worst strategy return: 五粮液 at `-5.5352%`.
- Best strategy return: 兆易创新 at `48.4322%`.
- Median strategy return: `0.3314%`.
- Average strategy return: `7.5582%`.
- Worst max drawdown: 兆易创新 at `-6.4968%`.
- Total trades across six fixtures: 464.

## Comparison To Previous V2 Default

Previous Chan Core V2 default used `allowed_point_types=third-buy,third-sell` and one-unit binary entries/exits. The recorded two-fixture default result was:

| Stock | Previous V2 Return % | Position-Sizing Return % | Change |
| --- | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | 1.5138 | 4.5061 | +2.9923 |
| 五粮液 `000858/SZSE` | 1.1706 | -5.5352 | -6.7058 |

Interpretation:

- The new semantics make 三买 high certainty visible in position size and allow 二买/背驰 confirmation to participate by default.
- The increased participation improves 中芯国际 and materially improves 兆易创新, but it introduces substantial churn and losses on 五粮液 and 中国平安.
- This supports keeping the implementation, but not treating the current defaults as tuned. The next strategy iteration should inspect whether sector/volatility-specific filters, stronger sell confirmation, or narrower point-type participation are needed.

## Verification

Completed before this QA file was written:

- `PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py -q` -> `39 passed`
- `PYTHONPATH=src python -m pytest tests/test_strategy_registry.py -q` -> `9 passed`
- Six-stock benchmark command above -> completed and wrote `/tmp/chan_position_sizing_benchmark.csv`

Final verification:

- `PYTHONPATH=src python -m pytest` -> `145 passed`
- `cd frontend && npm test -- --run` -> `18 files / 89 tests passed`
- `cd frontend && npm run build` -> passed
- `git diff --check` -> no output

Browser acceptance:

- URL: `http://127.0.0.1:5173/`
- Page title: `AI量化平台`
- Flow: app loads -> search/select `缠论结构策略` -> sizing parameters render -> search/selection interaction changes visible state
- Console errors/warnings: none relevant
- DOM evidence: `低确定性目标仓位`, `背驰确认目标仓位`, `高确定性目标仓位`, and `卖出确认保留仓位` are present with defaults `1/2/3/1`
- Screenshots:
  - `/tmp/ai_trade_system_chan_position_sizing_desktop_1440.png`
  - `/tmp/ai_trade_system_chan_position_sizing_mobile_390.png`
  - `/tmp/ai_trade_system_chan_position_sizing_desktop_visible_1440.png`
  - `/tmp/ai_trade_system_chan_position_sizing_mobile_visible_390.png`
  - `/tmp/ai_trade_system_chan_position_sizing_desktop_lower_1440.png`
  - `/tmp/ai_trade_system_chan_position_sizing_mobile_lower_390.png`
