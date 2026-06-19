# Chan Parameter Tuning QA

## Scope

This QA record covers the 2026-06-19 tuning pass for `ChanStructureStrategy` defaults on the fixed benchmark fixtures.

Changed defaults:

- `min_signal_score`: `30.0` -> `28.0`
- `allowed_point_types`: `all` -> `third-buy,third-sell`
- `max_holding_bars`: `0` -> `15`
- Preserved `signal_mode=all`, `allowed_levels=all`, and `watch_confirm_bars=20`

Rationale:

- The old default maximized two-stock sum return but left 五粮液 negative and carried a larger drawdown.
- The selected balanced configuration makes both fixed fixtures positive, raises the worst single-stock return from `-0.8148%` to `1.1706%`, and lowers worst drawdown from `-4.6198%` to `-1.5070%`.
- `allowed_levels=stroke` produced the same fixed-fixture result, but the default keeps `allowed_levels=all` to avoid over-narrowing by level before broader validation.

## Parameter Guidance

- `min_signal_score`: higher means fewer, stronger signals. This pass lowered it to `28.0` only because `third-buy/third-sell` filtering removes lower-quality T2 churn.
- `signal_mode`: `all` remains the default so confirmation and structure signals can both participate after point-type filtering.
- `allowed_point_types`: `third-buy,third-sell` focuses on pivot retest style entries/exits and avoided the weak second-buy/second-sell stream on the fixed fixtures.
- `max_holding_bars`: `15` adds a bounded time exit. It reduced drawdown and turned 五粮液 positive versus unlimited holding.
- `watch_confirm_bars`: unchanged at `20`. In the selected third-buy/third-sell configuration, tested values `0/10/20/40` produced the same benchmark result.

## TDD Evidence

RED command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_default_filters_low_confidence_structure_signals -q
```

RED result before implementation:

- `2 failed`.
- Both failures confirmed current defaults still used `min_signal_score=30.0` instead of the selected `28.0` profile.

GREEN command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_default_filters_low_confidence_structure_signals -q
```

GREEN result after implementation: `2 passed in 0.40s`.

Strategy regression:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py -q
```

Result: `43 passed in 1.83s`.

Full backend verification:

```bash
PYTHONPATH=src python -m pytest
```

Result: `137 passed in 3.85s`.

## Grid Search Evidence

The first full-object 240-config grid was interrupted because each config repeated the expensive per-bar Chan scan. The accelerated runner then precomputed same-day Chan structure signals once and simulated threshold/mode/filter/holding behavior.

Validation against the real strategy object matched exactly for these representative configs:

- Current default on both fixtures.
- `signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20`.
- `signal_mode=structure, min_signal_score=24.0, max_holding_bars=20, watch_confirm_bars=20`.

Second-round grid scope:

- `min_signal_score`: `28.0`, `30.0`, `32.0`, `36.0`, `40.0`
- `signal_mode`: `all`, `confirmation`, `structure`
- `max_holding_bars`: `0`, `5`, `7`, `10`, `12`, `15`, `20`, `30`
- `watch_confirm_bars`: `0`, `10`, `20`, `40`
- `allowed_point_types`: `all`, `second-buy,second-sell`, `third-buy,third-sell`, `second-buy,second-sell,third-buy,third-sell`
- `allowed_levels`: `all`, `stroke`, `fractal`

Key compared configs:

| Config | Params | Sum Return | Worst Return | Worst Drawdown | Total Trades |
| --- | --- | ---: | ---: | ---: | ---: |
| old default | `min_signal_score=30.0, signal_mode=all, allowed_point_types=all, allowed_levels=all, max_holding_bars=0, watch_confirm_bars=20` | 3.9014% | -0.8148% | -4.6198% | 3 |
| balanced selected | `min_signal_score=28.0, signal_mode=all, allowed_point_types=third-buy,third-sell, allowed_levels=all, max_holding_bars=15, watch_confirm_bars=20` | 2.6844% | 1.1706% | -1.5070% | 14 |
| sum-return runner-up | `min_signal_score=28.0, signal_mode=all, allowed_point_types=second-buy,second-sell, allowed_levels=stroke, max_holding_bars=0, watch_confirm_bars=20` | 3.9188% | -0.4795% | -4.6338% | 5 |

The selected config is not the highest sum-return row. It is the best balanced row among tested configs where both fixed fixtures stayed positive.

## Fixed Benchmark Backtests

Benchmarks below use the real `ChanStructureStrategy` object with the selected parameters, the persisted local qfq fixtures, `BacktestConfig()` defaults, and initial cash `100000`.

| Symbol | Name | Rows | Range | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `688981/SSE` | 中芯国际 | 720 | 2023-06-19 to 2026-06-18 | 101513.78 | 1.5138% | 155.5394% | -154.0256% | -1.5070% | 12 | 66.6667% | 2.0302 |
| `000858/SZSE` | 五粮液 | 726 | 2023-06-19 to 2026-06-18 | 101170.56 | 1.1706% | -52.8208% | 53.9914% | -0.7333% | 2 | 100.0000% | n/a |

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Surface:

- URL: `http://127.0.0.1:5173/`
- Workspace: `策略工坊`
- Selected strategy: `缠论结构策略` / `ChanStructureStrategy`

Checks:

- `最低信号分` displayed default `28`.
- `信号模式` displayed default `all`.
- `买卖点类型过滤` displayed `third-buy` and `third-sell` checked, with `all` unchecked.
- `结构层级过滤` displayed `all` checked.
- `最大持仓天数` displayed default `15`.
- Browser dev log check returned `3` log entries and `0` warning/error/failed entries.

Screenshots:

```text
/tmp/ai_trade_system_chan_parameter_tuning.png
/tmp/ai_trade_system_chan_parameter_tuning_defaults.png
/tmp/ai_trade_system_chan_parameter_tuning_filters.png
/tmp/ai_trade_system_chan_parameter_tuning_holding.png
```

## Follow-Up

This is a two-fixture balanced default, not a broad market optimization. Before increasing position size or using it as a live signal, run broader local-CSV universe validation and compare the old high-sum profile against this lower-drawdown profile.
