# Chan Signal Mode Controls QA

## Scope

This QA record covers adding `signal_mode` to `ChanStructureStrategy`.

Changed behavior:

- `ChanStructureStrategy` now accepts `signal_mode`.
- Supported values are `all`, `confirmation`, and `structure`.
- Default mode is `all`, preserving the previous benchmark behavior while `min_signal_score=30.0` continues to filter lower-confidence 28-point T2/T3 churn.
- `confirmation` only admits `*_DIVERGENCE` and `*_CONFIRM` signals.
- `structure` only admits T2/T3 second/third buy-sell signals.
- The strategy registry exposes Chinese guidance for `signal_mode`.

## TDD Evidence

Initial RED command:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_signal_mode_filters_structure_family tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_signal_mode_filters_confirmation_family tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_unknown_signal_mode tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score -q
```

Initial expected failures:

- `ChanStructureStrategy.__init__()` did not accept `signal_mode`.
- Registry inspection did not expose `signal_mode`.

Green result after implementation:

```text
5 passed in 1.27s
```

Default-mode correction RED command:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_default_filters_low_confidence_structure_signals tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score -q
```

Expected failures:

- Direct default was `confirmation` instead of benchmark-preserving `all`.
- Registry default was `confirmation` instead of `all`.

Green result:

```text
2 passed in 0.35s
```

Targeted regression:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_research_signals.py -q
```

Result:

```text
47 passed in 1.79s
```

## Full Verification

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

Results:

```text
116 passed in 5.19s
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

| Mode | Score | Final equity | Return | Benchmark | Excess | Max drawdown | Trades | Win rate | Profit factor | Exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` default | `30.0` | `104716.19` | `4.7162%` | `155.5394%` | `-150.8232%` | `-4.6198%` | `1` | `None` | `None` | `5.3826%` |
| `confirmation` | `30.0` | `100000.00` | `0.0000%` | `155.5394%` | `-155.5394%` | `0.0000%` | `0` | `None` | `None` | `0.0000%` |
| `structure` | `24.0` | `104415.73` | `4.4157%` | `155.5394%` | `-151.1237%` | `-5.1712%` | `59` | `48.2759%` | `1.4314` | `4.0578%` |
| `all` exploratory | `24.0` | `104415.73` | `4.4157%` | `155.5394%` | `-151.1237%` | `-5.1712%` | `59` | `48.2759%` | `1.4314` | `4.0578%` |

### 五粮液 000858/SZSE

- Fixture: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`
- Rows: `726`
- Date range: `2023-06-19` to `2026-06-18`

| Mode | Score | Final equity | Return | Benchmark | Excess | Max drawdown | Trades | Win rate | Profit factor | Exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` default | `30.0` | `99185.16` | `-0.8148%` | `-52.8208%` | `52.0060%` | `-3.4008%` | `2` | `0.0%` | `0.0` | `1.7537%` |
| `confirmation` | `30.0` | `100000.00` | `0.0000%` | `-52.8208%` | `52.8208%` | `0.0000%` | `0` | `None` | `None` | `0.0000%` |
| `structure` | `24.0` | `93318.64` | `-6.6814%` | `-52.8208%` | `46.1394%` | `-6.7334%` | `62` | `25.8065%` | `0.1678` | `3.1800%` |
| `all` exploratory | `24.0` | `93318.64` | `-6.6814%` | `-52.8208%` | `46.1394%` | `-6.7334%` | `62` | `25.8065%` | `0.1678` | `3.1800%` |

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

- `信号模式` field rendered in the parameter form.
- Default field value was `all`.
- `最低信号分` field remained `30`.
- Chinese guidance described `confirmation`, `structure`, and `all`.
- Browser console warn/error log count: `0`.

Screenshots:

```text
/tmp/ai_trade_system_chan_signal_mode_controls.png
/tmp/ai_trade_system_chan_signal_mode_controls_visible.png
```

## Follow-Up

`confirmation/30` currently produces zero trades on both fixed benchmark fixtures. The next Chan strategy step should add confirmation-mode position lifecycle behavior, such as explicit buy-confirmation entry handling and opposite-signal or time-based exits, then rerun the same fixed benchmark comparison.
