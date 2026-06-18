# Strategy Parameter Options QA

## Scope

This QA record covers exposing enum-like strategy parameter metadata through the registry/API and rendering that metadata as safe controls in the React `ParameterForm`.

Implemented behavior:

- `StrategyParameter` and API strategy parameter views expose `options` and `multiple`.
- `ChanStructureStrategy` metadata declares option lists for `signal_mode`, `allowed_point_types`, and `allowed_levels`.
- React renders metadata-backed single-select parameters as native selects.
- React renders metadata-backed multi-select parameters as compact checkbox groups while preserving the string contract expected by strategy constructors.
- Selecting a specific multi-select token removes `all`; selecting `all` clears specific tokens.

## TDD Evidence

Initial backend RED command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_api_routes.py::test_strategies_route_exposes_enum_parameter_options -q
```

RED result before implementation:

- `2 failed`.
- Registry failure: `AttributeError: 'StrategyParameter' object has no attribute 'options'`.
- API failure: `KeyError: 'options'`.

Initial frontend RED command:

```bash
cd frontend && npm test -- --run src/components/ParameterForm.test.tsx
```

RED result before implementation:

- `1 failed`.
- The metadata-backed multi-select test could not find checkbox label `买卖点类型过滤 second-buy` because the parameter still rendered as a single select.

GREEN targeted results after implementation:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_api_routes.py::test_strategies_route_exposes_enum_parameter_options -q
```

Result: `2 passed in 0.67s`.

```bash
cd frontend && npm test -- --run src/components/ParameterForm.test.tsx
```

Result: `1 passed`, `6 tests passed`.

Broader targeted regression:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py tests/test_api_routes.py -q
```

Result: `29 passed in 1.07s`.

```bash
cd frontend && npm test -- --run src/components/ParameterForm.test.tsx src/pages/StrategyPage.test.tsx
```

Result: `2 passed`, `14 tests passed`.

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: `137 passed in 6.02s`.

```bash
cd frontend && npm test -- --run
```

Result: `18 files passed`, `89 tests passed`.

```bash
cd frontend && npm run build
```

Result: TypeScript and Vite production build completed successfully.

## Fixed Benchmark Backtests

This slice changes metadata and UI controls only, not strategy trading logic. The default `ChanStructureStrategy` benchmark was still rerun on the required fixed fixtures to preserve comparable delivery evidence.

Parameters:

- `min_signal_score=30.0`
- `signal_mode=all`
- `max_holding_bars=0`
- `watch_confirm_bars=20`
- Initial cash: `100000`
- Persisted local qfq fixtures under `data/market/a_share/`

| Symbol | Name | Rows | Range | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `688981/SSE` | 中芯国际 | 720 | 2023-06-19 to 2026-06-18 | 104716.19 | 4.7162% | 155.5394% | -150.8232% | -4.6198% | 1 | n/a | n/a |
| `000858/SZSE` | 五粮液 | 726 | 2023-06-19 to 2026-06-18 | 99185.16 | -0.8148% | -52.8208% | 52.0060% | -3.4008% | 2 | 0.0000% | 0.0000 |

Interpretation:

- Results match the prior default `all` / `30.0` profile, confirming metadata/UI changes did not alter strategy output.
- 中芯国际 still captures one long-side trade but materially trails buy-and-hold over this fixture.
- 五粮液 still loses a small amount in absolute terms while outperforming its sharply negative benchmark return.

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Surface:

- URL: `http://127.0.0.1:5173/`
- Page title: `AI量化平台`
- Workspace: `策略工坊`
- Selected strategy: `缠论结构策略` / `ChanStructureStrategy`

Checks:

- `信号模式` rendered as a native select with options `all`, `confirmation`, and `structure`.
- `买卖点类型过滤` rendered as checkbox options for `all`, `first-buy`, `first-sell`, `second-buy`, `second-sell`, `third-buy`, and `third-sell`.
- `结构层级过滤` rendered as checkbox options for `all`, `segment`, `stroke`, and `fractal`.
- Browser interaction checked `second-buy` and `third-buy`; `all` became unchecked while both selected tokens remained checked.
- Browser dev log check returned `4` log entries and `0` warning/error/failed entries.

Screenshot:

```text
/tmp/ai_trade_system_strategy_parameter_options.png
```

## Follow-Up

The next recommended strategy item is `VolumeConfirmedMomentumStrategy` threshold and exit-rule tuning against the same fixed 中芯国际 and 五粮液 fixtures.
