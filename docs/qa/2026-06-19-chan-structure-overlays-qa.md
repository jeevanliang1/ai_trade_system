# Chan Structure Overlays QA

Date: 2026-06-19

## Scope

Validate Strategy Workshop Chan structure overlays:

- `/api/research/signals/preview` includes chart-ready `chan_structure` data.
- Strategy Workshop K-line chart can render fractals, strokes, pivots, and structure buy/sell markers.
- The chart toolbar can hide and restore the Chan structure overlay.
- The research panel shows compact structure counts.
- Fixed benchmark backtests for 中芯国际 and 五粮液 are recorded because this work changes a strategy research/inspection workflow.

## TDD Evidence

RED checks:

- `PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_preview_includes_chan_structure_overlay_payload -q`
  - Failed with `AttributeError: 'ResearchSignalPreview' object has no attribute 'chan_structure'`.
- `cd frontend && npm test -- chartOptions.test.ts StrategyPage.test.tsx --run`
  - Failed because `priceOption` returned only `K线`, `MA20`, `MA60`, `买入`, and `卖出`.
  - Failed because Strategy Workshop did not have the `显示缠论结构` checkbox.

GREEN checks:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_preview_includes_chan_structure_overlay_payload -q
```

Result: `1 passed in 0.45s`

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
```

Result: `13 passed in 0.47s`

```bash
cd frontend && npm test -- chartOptions.test.ts StrategyPage.test.tsx --run
```

Result: `2 passed`, `14 passed`

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: `105 passed in 4.36s`

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
| 中芯国际 `688981/SSE` | `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv` | 720 | 2023-06-19 to 2026-06-18 | 104415.73 | 4.4157% | 155.5394% | -151.1237% | -5.1712% | 59 | 48.2759% | 1.4314 |
| 五粮液 `000858/SZSE` | `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv` | 726 | 2023-06-19 to 2026-06-18 | 93318.64 | -6.6814% | -52.8208% | 46.1394% | -6.7334% | 62 | 25.8065% | 0.1678 |

Interpretation:

- This change does not alter `ChanStructureStrategy` trading logic; benchmark results match the previous no-tuning baseline.
- 中芯国际 remains low-exposure and drawdown-controlled, but misses most buy-and-hold upside.
- 五粮液 remains negative on absolute return, but avoids much of the benchmark decline.

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
- Research preview rendered structure summary containing `分型`, `笔`, and `中枢`.
- K-line chart rendered two canvas elements; the first chart canvas was `492x360`.
- `显示缠论结构` toggled from `false` back to `true`.
- Browser console `warn/error` logs were empty.
- Screenshot: `/tmp/ai_trade_system_chan_structure_overlays.png`

## Follow-Up

Next Chan development item: deepen the Chan core analyzer with segment-level structure, recursive pivots, and divergence-style confirmation.
