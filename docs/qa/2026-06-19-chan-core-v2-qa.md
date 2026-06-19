# Chan Core V2 QA

## Scope

This QA record covers the Chan Core V2 slice:

- multi-level trend type records for `stroke` and `segment` levels;
- pivot lifecycle records with confirmed, extended, broken, and completed states;
- additive V2 summary fields on the Chan structure overlay;
- conservative incremental cache integration in `ChanStructureStrategy`.

This slice intentionally does not tune strategy defaults or add a new default signal family.

## Implementation Summary

- Added `src/ai_trade_system/research/chan_core_v2.py`.
- Extended `ChanStructureResult` with additive `core_v2` metadata.
- Extended `ChanStructureOverlay` with compact V2 summary fields:
  - `core_v2_trend_count`
  - `core_v2_pivot_lifecycle_count`
  - `core_v2_cache`
  - `core_v2_latest_trend`
  - `core_v2_pivot_states`
- Updated `ChanStructureStrategy` to feed every same-symbol bar into `ChanCoreV2Analyzer`, while still waiting for `min_bars` before consuming signals.

## TDD Evidence

Initial RED command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_research_signals.py::test_chan_core_v2_classifies_multilevel_trends_and_lifecycle_states \
  tests/test_research_signals.py::test_chan_structure_result_and_overlay_expose_chan_core_v2_summary \
  tests/test_research_signals.py::test_chan_core_v2_incremental_analyzer_matches_full_scan_for_strategy_fields \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_uses_incremental_chan_core_v2_analyzer -q
```

Initial RED result:

- Failed during collection with `ModuleNotFoundError: No module named 'ai_trade_system.research.chan_core_v2'`.

Core snapshot GREEN command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_research_signals.py::test_chan_core_v2_classifies_multilevel_trends_and_lifecycle_states \
  tests/test_research_signals.py::test_chan_structure_result_and_overlay_expose_chan_core_v2_summary -q
```

Core snapshot GREEN result: `2 passed in 0.36s`.

Analyzer/strategy RED command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_research_signals.py::test_chan_core_v2_incremental_analyzer_matches_full_scan_for_strategy_fields \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_uses_incremental_chan_core_v2_analyzer -q
```

Analyzer/strategy RED result:

- `test_chan_core_v2_incremental_analyzer_matches_full_scan_for_strategy_fields` passed after core implementation.
- `test_chan_structure_strategy_uses_incremental_chan_core_v2_analyzer` failed with missing `popular.ChanCoreV2Analyzer`, proving the strategy was not yet using the incremental analyzer.

Analyzer/strategy GREEN command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_research_signals.py::test_chan_core_v2_incremental_analyzer_matches_full_scan_for_strategy_fields \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_uses_incremental_chan_core_v2_analyzer -q
```

Analyzer/strategy GREEN result: `2 passed in 0.87s`.

## Regression Verification

Targeted backend regression:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py tests/test_builtin_popular_strategies.py -q
```

Result: `62 passed in 2.38s`.

Full backend regression:

```bash
PYTHONPATH=src python -m pytest
```

Result: `141 passed in 4.43s`.

Frontend regression:

```bash
cd frontend && npm test -- --run
```

First run result:

- `1 failed | 88 passed`.
- Failure was `StrategyPage loads editable source into a line-numbered safe editor`.
- The failed file had no current diff and is unrelated to the Chan Core V2 backend paths.

Debug checks:

```bash
cd frontend && npm test -- --run src/pages/StrategyPage.test.tsx -t "loads editable source"
```

Result: `1 passed | 7 skipped`.

Fresh frontend rerun:

```bash
cd frontend && npm test -- --run
```

Result: `18 passed`, `89 passed`.

Frontend build:

```bash
cd frontend && npm run build
```

Result: TypeScript and Vite build completed successfully.

## Fixed Benchmark Backtests

Benchmarks use the real default `ChanStructureStrategy`, persisted local qfq fixtures, and `BacktestConfig()` defaults:

- Initial cash: `100000`
- Commission rate: `0.0003`
- Slippage: `0.01`
- Max order cash: `50000`
- Trade size: `100`

| Symbol | Name | CSV | Rows | Range | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `688981/SSE` | 中芯国际 | `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv` | 720 | 2023-06-19 to 2026-06-18 | 101513.78 | 1.5138% | 155.5394% | -154.0256% | -1.5070% | 12 | 66.6667% | 2.0302 |
| `000858/SZSE` | 五粮液 | `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv` | 726 | 2023-06-19 to 2026-06-18 | 101170.56 | 1.1706% | -52.8208% | 53.9914% | -0.7333% | 2 | 100.0000% | n/a |

Interpretation:

- Results match the previous balanced-parameter benchmark, so this V2 infrastructure slice did not intentionally change default trading behavior.
- Cache metadata is now available for future performance tuning and true partial recompute work.

## Browser QA

Command:

```bash
./scripts/run_app.sh
node scripts/capture_app_screenshots.mjs --url http://127.0.0.1:5173/ --prefix ai_trade_system_chan_core_v2
```

Surface:

- URL: `http://127.0.0.1:5173/`
- Page: default React Strategy Workshop surface.

Screenshots:

```text
/tmp/ai_trade_system_chan_core_v2_desktop_1440.png
/tmp/ai_trade_system_chan_core_v2_mobile_390.png
```

Visual check:

- Desktop screenshot rendered the React workbench, K-line chart, volume chart, strategy list, and right AI/risk inspector.
- No blank page or server error screen was observed.

## Follow-Up

V2 currently uses conservative dirty-window recomputation. The next Chan-specific improvement can replace the internal recompute with true suffix-level structural mutation once the lifecycle and trend-type contracts are exercised by more strategy logic.
