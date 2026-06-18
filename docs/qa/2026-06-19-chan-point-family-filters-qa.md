# Chan Point-Family Filters QA

## Scope

This QA record covers adding metadata-backed point-family and structure-level filters to `ChanStructureStrategy`.

Implemented behavior:

- `ChanStructureStrategy` accepts `allowed_point_types`, defaulting to `all`.
- `ChanStructureStrategy` accepts `allowed_levels`, defaulting to `all`.
- Direct tradable signals and armed-watch confirmation signals respect the filters.
- T1 divergence watch arming remains setup-only and is not blocked by the filters before a tradable confirmation arrives.
- Unknown point-type or level tokens fail fast with `ValueError`.
- Strategy registry metadata exposes `买卖点类型过滤` and `结构层级过滤` with accepted token guidance.

## TDD Evidence

Initial targeted RED command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_filters_allowed_point_types \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_filters_allowed_levels \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_armed_watch_respects_confirmation_filters \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_unknown_allowed_point_types \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_unknown_allowed_levels \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score \
  -q
```

RED result before implementation:

- 7 failed.
- Strategy failures were `ChanStructureStrategy.__init__() got an unexpected keyword argument 'allowed_point_types'` or `allowed_levels`.
- Registry failures were missing `allowed_point_types` and `allowed_levels` metadata/defaults.

GREEN result after implementation:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_filters_allowed_point_types \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_filters_allowed_levels \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_armed_watch_respects_confirmation_filters \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_unknown_allowed_point_types \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_unknown_allowed_levels \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score \
  -q
```

Result: `7 passed in 0.35s`.

Broader targeted result:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py -q
```

Result: `43 passed in 1.87s`.

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: `136 passed in 4.33s`.

```bash
cd frontend && npm test -- --run
```

Result: `18 passed (18)`, `87 passed (87)`.

```bash
cd frontend && npm run build
```

Result: TypeScript and Vite production build completed successfully.

## Fixed Benchmark Fixtures

Parameters:

- Initial cash: 100000
- Commission: 0.0003
- Slippage: 0.01
- Max order cash: 50000
- Trade size: 100
- Data: persisted local qfq fixtures under `data/market/a_share/`

### 中芯国际 688981/SSE

Fixture: `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`

Rows: 720, date range: 2023-06-19 to 2026-06-18.

| Config | Params | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default_all | `min_signal_score=30.0, signal_mode=all, max_holding_bars=0, watch_confirm_bars=20` | 104716.19 | 4.7162% | 155.5394% | -150.8232% | -4.6198% | 1 | n/a | n/a |
| confirmation_lifecycle | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20` | 100478.58 | 0.4786% | 155.5394% | -155.0608% | -1.5512% | 10 | 60.0000% | 1.3169 |
| point_first_confirmation | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20, allowed_point_types=first-buy,first-sell` | 100000.00 | 0.0000% | 155.5394% | -155.5394% | 0.0000% | 0 | n/a | n/a |
| point_second_structure | `min_signal_score=24.0, signal_mode=structure, max_holding_bars=20, watch_confirm_bars=20, allowed_point_types=second-buy,second-sell` | 99662.97 | -0.3370% | 155.5394% | -155.8764% | -5.5921% | 47 | 39.1304% | 0.8596 |
| point_third_confirmation | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20, allowed_point_types=third-buy,third-sell` | 100478.58 | 0.4786% | 155.5394% | -155.0608% | -1.5512% | 10 | 60.0000% | 1.3169 |
| level_segment_confirmation | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20, allowed_levels=segment` | 100000.00 | 0.0000% | 155.5394% | -155.5394% | 0.0000% | 0 | n/a | n/a |
| level_stroke_confirmation | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20, allowed_levels=stroke` | 100478.58 | 0.4786% | 155.5394% | -155.0608% | -1.5512% | 10 | 60.0000% | 1.3169 |
| level_fractal_structure | `min_signal_score=24.0, signal_mode=structure, max_holding_bars=20, watch_confirm_bars=20, allowed_levels=fractal` | 99662.97 | -0.3370% | 155.5394% | -155.8764% | -5.5921% | 47 | 39.1304% | 0.8596 |

### 五粮液 000858/SZSE

Fixture: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`

Rows: 726, date range: 2023-06-19 to 2026-06-18.

| Config | Params | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default_all | `min_signal_score=30.0, signal_mode=all, max_holding_bars=0, watch_confirm_bars=20` | 99185.16 | -0.8148% | -52.8208% | 52.0060% | -3.4008% | 2 | 0.0000% | 0.0000 |
| confirmation_lifecycle | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20` | 100621.73 | 0.6217% | -52.8208% | 53.4425% | -1.2718% | 2 | 100.0000% | n/a |
| point_first_confirmation | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20, allowed_point_types=first-buy,first-sell` | 100000.00 | 0.0000% | -52.8208% | 52.8208% | 0.0000% | 0 | n/a | n/a |
| point_second_structure | `min_signal_score=24.0, signal_mode=structure, max_holding_bars=20, watch_confirm_bars=20, allowed_point_types=second-buy,second-sell` | 94230.26 | -5.7697% | -52.8208% | 47.0511% | -6.1128% | 38 | 31.5789% | 0.2982 |
| point_third_confirmation | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20, allowed_point_types=third-buy,third-sell` | 100621.73 | 0.6217% | -52.8208% | 53.4425% | -1.2718% | 2 | 100.0000% | n/a |
| level_segment_confirmation | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20, allowed_levels=segment` | 100000.00 | 0.0000% | -52.8208% | 52.8208% | 0.0000% | 0 | n/a | n/a |
| level_stroke_confirmation | `min_signal_score=30.0, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20, allowed_levels=stroke` | 100621.73 | 0.6217% | -52.8208% | 53.4425% | -1.2718% | 2 | 100.0000% | n/a |
| level_fractal_structure | `min_signal_score=24.0, signal_mode=structure, max_holding_bars=20, watch_confirm_bars=20, allowed_levels=fractal` | 94230.26 | -5.7697% | -52.8208% | 47.0511% | -6.1128% | 38 | 31.5789% | 0.2982 |

## Interpretation

The default rows match the prior Chan same-level lineage and watch-divergence benchmark profile, which confirms `all` preserves existing behavior.

On the fixed fixtures, confirmation-mode lifecycle trades are entirely carried by `third-buy`/`third-sell` and `stroke` metadata. `first-buy`/`first-sell` and `segment` confirmation filters produce no trades for these two datasets, while `second-buy`/`second-sell` and `fractal` structure filters isolate the lower-score T2/T2-style repair stream.

This is strategy slicing, not threshold tuning. The next practical step is to expose enum-like strategy parameters as select controls so `signal_mode`, `allowed_point_types`, and `allowed_levels` are easier to set without free-text mistakes.

## Browser QA

Commands:

```bash
./scripts/run_app.sh
node scripts/capture_app_screenshots.mjs --url http://127.0.0.1:5173 --out-dir /tmp --prefix ai_trade_system_chan_point_family_filters
```

Additional CDP interaction selected `缠论结构策略 / ChanStructureStrategy`, verified the page text contained `买卖点类型过滤` and `结构层级过滤`, scrolled the parameter panel to the new fields, and captured a focused screenshot.

Evidence:

- App loaded at `http://127.0.0.1:5173/`.
- Page title: `AI量化平台`.
- `缠论结构策略` / `ChanStructureStrategy` could be selected.
- Visible fields included `信号模式`, `买卖点类型过滤`, `结构层级过滤`, and `背驰观察有效期`.
- Browser console errors: none observed during capture.
- Desktop screenshot: `/tmp/ai_trade_system_chan_point_family_filters_desktop_1440.png`.
- Mobile screenshot: `/tmp/ai_trade_system_chan_point_family_filters_mobile_390.png`.
- Focused strategy-parameter screenshot: `/tmp/ai_trade_system_chan_point_family_filters_strategy_params.png`.
