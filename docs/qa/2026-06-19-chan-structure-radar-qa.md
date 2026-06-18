# Chan Structure Radar QA

Date: 2026-06-19

## Scope

Validate Signal Radar `chan_structure` scoring mode:

- API accepts `score_mode="chan_structure"` in `/api/research/signals/batch`.
- Backend reuses `research.chan_structure` and returns structure diagnostics.
- React Signal Radar can select `缠论结构`, scan local managed CSV candidates, render diagnostics, and export structure fields.
- Fixed benchmark backtests for 中芯国际 and 五粮液 are recorded because this work expands strategy signal inspection.

## TDD Evidence

RED checks:

- `PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_research_signals_batch_route_ranks_chan_structure_from_managed_csv -q`
  - Failed with HTTP 422 before `chan_structure` was added to the API schema.
- `cd frontend && npm test -- SignalRadarPage.test.tsx`
  - Failed because the `评分模式` select did not contain value `chan_structure`.

GREEN checks:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_research_signals_batch_route_ranks_chan_structure_from_managed_csv -q
```

Result: `1 passed in 0.61s`

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py -q
```

Result: `19 passed in 0.89s`

```bash
cd frontend && npm test -- SignalRadarPage.test.tsx
```

Result: `1 passed`, `6 passed`

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: `104 passed in 2.22s`

```bash
cd frontend && npm test
```

Result: `18 passed`, `86 passed`

```bash
cd frontend && npm run build
```

Result: Vite production build completed successfully.

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

- Open `http://localhost:5173/`.
- Navigate to `信号雷达`.
- Select `评分模式 = 缠论结构`.
- Search `688981`.
- Click `批量扫描`.

Evidence:

- Page title: `AI量化平台`.
- Signal Radar page rendered nonblank.
- Selected score mode showed `缠论结构`.
- Scan returned `688981 中芯国际` with `缠论结构排行`.
- Table and detail card rendered `分型`, `笔`, and `中枢` diagnostics.
- CSV export href included `fractal_count`, `stroke_count`, `pivot_count`, and `structure_signal`.
- Browser console `warn/error` logs were empty.
- Screenshot: `/tmp/ai_trade_system_chan_structure_radar.png`

## Follow-Up

Next Chan development item: add Strategy Workshop visualization overlays for fractals, strokes, pivots, and T2/T3 signals.
