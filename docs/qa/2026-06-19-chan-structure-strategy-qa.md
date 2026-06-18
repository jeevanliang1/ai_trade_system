# Chan Structure Strategy QA

Date: 2026-06-19

## Scope

Validate the first-cut `ChanStructureStrategy` implementation:

- `research.chan_structure` analyzer for containment, fractals, strokes, pivots, and T2/T3 signals.
- Built-in `ChanStructureStrategy` signal emission.
- Strategy registry metadata and Chinese parameter guidance.
- React Strategy Workshop visibility and selection.

## TDD Evidence

RED checks were observed during implementation:

- `PYTHONPATH=src python -m pytest tests/test_research_signals.py -q` failed before `ai_trade_system.research.chan_structure` existed.
- `PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py -q` failed before `ChanStructureStrategy` existed.
- `PYTHONPATH=src python -m pytest tests/test_strategy_registry.py -q` failed before registry metadata was added.

GREEN checks:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py -q
```

Result: `35 passed in 0.37s`

```bash
PYTHONPATH=src python -m pytest
```

Result: `103 passed in 2.14s`

```bash
cd frontend && npm test
```

Result: `18 passed`, `85 passed`

```bash
cd frontend && npm run build
```

Result: Vite production build completed successfully.

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Target:

- URL: `http://localhost:5173/`
- Title: `AI量化平台`
- Flow: app loads -> Strategy Workshop renders -> search for `缠论结构` -> select `缠论结构策略`.

Evidence:

- Page identity matched the React platform.
- DOM contained `缠论结构策略` and `ChanStructureStrategy`.
- After selection, the banner showed `策略：缠论结构策略`.
- Parameter guidance rendered `成笔最小间隔` and `二买二卖确认幅度`.
- Browser console `warn/error` logs were empty before and after the interaction.
- Screenshot: `/tmp/ai_trade_system_chan_structure_strategy.png`

## Fixed Benchmark Backtest Baseline

Execution used a one-off `PYTHONPATH=src python` runner that loaded the fixed local qfq CSV files with `read_bars_csv`, instantiated `ChanStructureStrategy`, ran the shared `run_backtest` engine, and summarized results through `calculate_backtest_metrics`.

Default `ChanStructureStrategy` parameters:

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

Results:

| Stock | Local CSV | Rows | Date Range | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv` | 720 | 2023-06-19 to 2026-06-18 | 104415.73 | 4.4157% | 155.5394% | -151.1237% | -5.1712% | 59 | 48.2759% | 1.4314 |
| 五粮液 `000858/SZSE` | `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv` | 726 | 2023-06-19 to 2026-06-18 | 93318.64 | -6.6814% | -52.8208% | 46.1394% | -6.7334% | 62 | 25.8065% | 0.1678 |

Interpretation:

- This is a no-tuning baseline, not an optimized strategy result.
- 中芯国际 shows low exposure and controlled drawdown, but misses most of the buy-and-hold upside.
- 五粮液 loses money on absolute return, but avoids a large part of the benchmark drawdown.
- Future strategy iteration should compare against this same fixed local dataset before accepting changes.

## Notes

This validates the first single-symbol daily-bar slice. Full recursive multi-timeframe Chan analysis, overlay visualization, and Signal Radar scoring-mode integration remain follow-up work.
