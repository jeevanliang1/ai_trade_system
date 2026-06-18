# Chan Structure Default Threshold Tuning QA

## Scope

This QA record covers tuning the default `ChanStructureStrategy.min_signal_score` after indicator-backed divergence scoring.

Changed behavior:

- `ChanStructureStrategy` default `min_signal_score` changed from `24.0` to `30.0`.
- Explicit `min_signal_score` values continue to work unchanged.
- Strategy registry parameter inspection now exposes `30.0`, so React parameter forms load the tuned default.

## TDD Evidence

Red command:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_default_filters_low_confidence_structure_signals tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score -q
```

Initial expected failures:

- `assert 24.0 == 30.0` from direct `ChanStructureStrategy` instantiation.
- `assert 24.0 == 30.0` from registry parameter inspection.

Green command:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_default_filters_low_confidence_structure_signals tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score -q
```

Result:

```text
2 passed in 0.37s
```

Targeted regression:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_research_signals.py -q
```

Result:

```text
44 passed in 0.85s
```

## Full Verification

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

Results:

```text
113 passed in 4.33s
18 passed, 87 tests passed
vite build succeeded
```

## Threshold Selection

The tuning sweep held `lookback=160`, `min_stroke_bars=5`, and `min_rebound_pct=0.03` constant.

Compared thresholds:

- `24.0`: current baseline, includes 28-point T2/T3 signals.
- `30.0` through `44.0`: same benchmark trades, filters 28-point lower-confidence signals while retaining stronger divergence/confirmation signals.
- `46.0` and above: zero trades on both fixed fixtures.

Selected threshold:

- `30.0`, because it is the least restrictive value that removes current low-confidence churn while keeping both fixed fixtures active.

## Fixed Benchmark Backtests

Strategy: `ChanStructureStrategy`

Parameters:

- `min_bars=60`
- `lookback=160`
- `min_stroke_bars=5`
- `min_rebound_pct=0.03`
- `min_signal_score=30.0`
- `trade_size=100`
- initial cash `100000.0`
- default `BacktestConfig` commission, slippage, and max order cash

### 中芯国际 688981/SSE

- Fixture: `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
- Rows: `720`
- Date range: `2023-06-19` to `2026-06-18`
- Final equity: `104716.19`
- Strategy return: `4.7162%`
- Benchmark return: `155.5394%`
- Excess return: `-150.8232%`
- Max drawdown: `-4.6198%`
- Trade count: `1`
- Win rate: `None`
- Profit factor: `None`
- Exposure: `5.3826%`

Previous `min_signal_score=24.0` baseline:

- Strategy return: `4.4157%`
- Max drawdown: `-5.1712%`
- Trade count: `59`

### 五粮液 000858/SZSE

- Fixture: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`
- Rows: `726`
- Date range: `2023-06-19` to `2026-06-18`
- Final equity: `99185.16`
- Strategy return: `-0.8148%`
- Benchmark return: `-52.8208%`
- Excess return: `52.0060%`
- Max drawdown: `-3.4008%`
- Trade count: `2`
- Win rate: `0.0%`
- Profit factor: `0.0`
- Exposure: `1.7537%`

Previous `min_signal_score=24.0` baseline:

- Strategy return: `-6.6814%`
- Max drawdown: `-6.7334%`
- Trade count: `62`

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Surface:

- URL: `http://127.0.0.1:5173/`
- Page title: `AI量化平台`
- Workspace: `策略工坊`
- Selected strategy: `ChanStructureStrategy`

Checks:

- Strategy Workshop rendered with two chart canvases.
- `ChanStructureStrategy` could be selected from the strategy list.
- The parameter form showed `最低信号分` with value `30`.
- Browser console warn/error log count: `0`.

Screenshots:

```text
/tmp/ai_trade_system_chan_threshold_tuning.png
/tmp/ai_trade_system_chan_threshold_tuning_score_visible.png
```

## Follow-Up

Next Chan strategy step should add signal-family or trading-mode controls so confirmation-style divergence signals, T2/T3 structure signals, and full exploratory structure signals can be benchmarked independently.
