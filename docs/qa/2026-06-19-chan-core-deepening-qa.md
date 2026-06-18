# Chan Core Deepening QA

Date: 2026-06-19

## Scope

Validate the next `research.chan_structure` slice:

- Build simplified line-segment structures above strokes.
- Build recursive pivots on both stroke and segment levels.
- Detect segment-level top/bottom divergence by comparing price extremes against segment energy.
- Emit divergence and confirmation signals that `ChanStructureStrategy` can consume.
- Expose segment, recursive pivot, and divergence diagnostics through preview/batch payloads and Strategy Workshop chart overlays.
- Record fixed benchmark backtests for 中芯国际 and 五粮液 because this changes strategy behavior.

## TDD Evidence

RED checks:

- `PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_builds_segments_recursive_pivots_and_divergence -q`
  - Failed with `AttributeError: 'ChanStructureResult' object has no attribute 'segments'`.
- `PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences -q`
  - Failed with `AttributeError: 'ChanStructureOverlay' object has no attribute 'segment_count'`.
- `cd frontend && npm test -- --run src/pages/chartOptions.test.ts`
  - Failed because the chart series did not include `缠论线段` and `递归中枢`.

GREEN checks:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
```

Result: `15 passed in 0.47s`

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py -q
```

Result: `16 passed in 0.50s`

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py -q
```

Result: `19 passed in 1.02s`

```bash
cd frontend && npm test -- --run src/pages/chartOptions.test.ts
```

Result: `6 passed`

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: `108 passed in 2.16s`

```bash
cd frontend && npm test -- --run
```

Result: `18 passed`, `87 passed`

```bash
cd frontend && npm run build
```

Result: TypeScript and Vite production build completed successfully.

## Fixed Benchmark Backtest

Execution used the fixed local qfq daily-bar fixtures and default `ChanStructureStrategy` parameters:

- `min_bars=60`
- `lookback=160`
- `min_stroke_bars=5`
- `min_rebound_pct=0.03`
- `min_signal_score=24.0`
- `trade_size=100`

Backtest config:

- `initial_cash=100000`
- `commission_rate=0.0003`
- `slippage=0.01`
- `max_order_cash=50000`

| Stock | Local CSV | Rows | Date Range | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv` | 720 | 2023-06-19 to 2026-06-18 | 104525.48 | 4.5255% | 155.5394% | -151.0139% | -5.1660% | 69 | 47.0588% | 1.4027 |
| 五粮液 `000858/SZSE` | `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv` | 726 | 2023-06-19 to 2026-06-18 | 92726.08 | -7.2739% | -52.8208% | 45.5469% | -7.7672% | 82 | 29.2683% | 0.1890 |

Interpretation:

- 中芯国际 remains low-drawdown and profitable, but still misses most buy-and-hold upside.
- 五粮液 remains negative on absolute return, but avoids much of the benchmark decline.
- Trade count rose versus the first-cut baseline because divergence/confirmation signals are now tradable by `ChanStructureStrategy`.

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Flow:

- Open `http://127.0.0.1:5173/`.
- Confirm page title `AI量化平台`.
- Use the default Strategy Workshop view.
- Click `缠论/RSI研判`.
- Confirm `显示缠论结构` exists and is checked.
- Toggle `显示缠论结构` off and back on.

Evidence:

- Page URL: `http://127.0.0.1:5173/`.
- Page title: `AI量化平台`.
- Strategy Workshop rendered nonblank with real strategy/data content.
- Research preview rendered Chan summary text containing `分型` and `中枢`.
- K-line and volume charts rendered as two canvases, `492x360` and `492x130`.
- `显示缠论结构` checkbox toggled and ended checked.
- Browser console `warn/error` logs were empty.
- Screenshot: `/tmp/ai_trade_system_chan_core_deepening.png` (`1280x720`).

## Follow-Up

Next Chan development item: replace the simplified sliding-window segment builder with stricter Chan segment split/break/rebuild rules, then add MACD/volume divergence strength and multi-level pivot linkage before parameter tuning.
