# Chan Confirmation Lifecycle QA

## Scope

This QA record covers adding optional max-holding exits to `ChanStructureStrategy` so confirmation-mode entries can complete through an opposite confirmation signal or a deterministic time exit.

Changed behavior:

- `ChanStructureStrategy` now accepts `max_holding_bars`.
- Default `max_holding_bars=0` disables time exits and preserves existing default behavior.
- Positive `max_holding_bars` exits an open position after the configured held-bar count when no opposite signal exits first.
- Opposite confirmation signals still exit a long position before time exits.
- The registry exposes Chinese guidance that `0` disables time exits for strategies supporting this convention.

## TDD Evidence

Initial RED command:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_confirmation_mode_exits_on_opposite_signal tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_confirmation_mode_exits_after_max_holding_bars tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_negative_max_holding_bars tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score -q
```

Initial expected failures:

- `ChanStructureStrategy.__init__()` did not accept `max_holding_bars`.
- Registry inspection did not expose the new default.

After implementation, two tests initially failed because the test fixture used `min_bars=1`, which violates the existing strategy contract `min_bars >= 3`. The fixture was corrected to use `min_bars=3` without relaxing production validation.

Green result:

```text
5 passed in 0.34s
```

Targeted regression:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_research_signals.py -q
```

Result:

```text
50 passed in 1.79s
```

## Full Verification

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

Results:

```text
119 passed in 5.35s
18 passed, 87 tests passed
vite build succeeded
```

## Fixed Benchmark Backtests

Strategy base parameters:

- `min_bars=60`
- `lookback=160`
- `min_stroke_bars=5`
- `min_rebound_pct=0.03`
- `trade_size=100`
- initial cash `100000.0`
- default `BacktestConfig` commission, slippage, and max order cash

### 中芯国际 688981/SSE

- Fixture: `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
- Rows: `720`
- Date range: `2023-06-19` to `2026-06-18`

| Mode | Score | Max holding | Final equity | Return | Benchmark | Excess | Max drawdown | Trades | Win rate | Profit factor | Exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` default | `30.0` | `0` | `104716.19` | `4.7162%` | `155.5394%` | `-150.8232%` | `-4.6198%` | `1` | `None` | `None` | `5.3826%` |
| `confirmation` lifecycle | `30.0` | `20` | `100000.00` | `0.0000%` | `155.5394%` | `-155.5394%` | `0.0000%` | `0` | `None` | `None` | `0.0000%` |
| `structure` lifecycle | `24.0` | `20` | `100822.78` | `0.8228%` | `155.5394%` | `-154.7166%` | `-5.4956%` | `69` | `50.0%` | `0.9815` | `3.8499%` |

### 五粮液 000858/SZSE

- Fixture: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`
- Rows: `726`
- Date range: `2023-06-19` to `2026-06-18`

| Mode | Score | Max holding | Final equity | Return | Benchmark | Excess | Max drawdown | Trades | Win rate | Profit factor | Exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` default | `30.0` | `0` | `99185.16` | `-0.8148%` | `-52.8208%` | `52.0060%` | `-3.4008%` | `2` | `0.0%` | `0.0` | `1.7537%` |
| `confirmation` lifecycle | `30.0` | `20` | `100000.00` | `0.0000%` | `-52.8208%` | `52.8208%` | `0.0000%` | `0` | `None` | `None` | `0.0000%` |
| `structure` lifecycle | `24.0` | `20` | `94490.29` | `-5.5097%` | `-52.8208%` | `47.3111%` | `-5.8528%` | `62` | `29.0323%` | `0.2409` | `2.8984%` |

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

- `最大持仓天数` rendered in the parameter form.
- Default field value was `0`.
- Guidance stated `0 表示禁用时间退出`.
- `信号模式` remained visible with value `all`.
- Browser console warn/error log count: `0`.

Screenshot:

```text
/tmp/ai_trade_system_chan_confirmation_lifecycle.png
```

## Follow-Up

The lifecycle is now available, but `confirmation/30/max20` still produces zero trades on both fixed benchmark fixtures because current rolling scans do not emit confirmation-family entry signals for those fixtures. The next Chan strategy step should deepen confirmation signal generation or persistence, such as a divergence watch state that confirms bottom/top divergence after subsequent repair or break bars.
