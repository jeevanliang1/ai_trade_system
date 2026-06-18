# Chan Watch Divergence Arming QA

## Scope

This QA record covers adding bounded watch-divergence arming to `ChanStructureStrategy`.

Implemented behavior:

- `ChanStructureStrategy` accepts `watch_confirm_bars`, defaulting to `20`.
- Watch-tagged T1 bottom/top divergence signals can arm a future same-direction confirmation.
- Later same-direction `CHAN_STRUCT_*_CONFIRM`, T2, or T3 structures can consume the armed watch and emit an `ARMED_CONFIRM` trade signal.
- Watch arming can expire, be disabled with `watch_confirm_bars=0`, and rejects negative values.
- Strategy registry metadata exposes `背驰观察有效期` with plain-language guidance.

## TDD Evidence

Initial targeted RED command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_arms_bottom_divergence_watch_and_confirms_with_t2 \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_arms_top_divergence_watch_and_confirms_with_t3 \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_expires_armed_divergence_watch \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_can_disable_divergence_watch_arming \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_negative_watch_confirm_bars \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score -q
```

RED result before implementation:

- 7 failed.
- Strategy failures were `ChanStructureStrategy.__init__() got an unexpected keyword argument 'watch_confirm_bars'`.
- Registry failures were missing `watch_confirm_bars` metadata/default.

GREEN result after implementation:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_arms_bottom_divergence_watch_and_confirms_with_t2 \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_arms_top_divergence_watch_and_confirms_with_t3 \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_expires_armed_divergence_watch \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_can_disable_divergence_watch_arming \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_negative_watch_confirm_bars \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score -q
```

Result: `7 passed in 0.34s`.

Broader targeted result:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py -q
```

Result: `38 passed in 1.77s`.

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: `128 passed in 5.66s`.

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
| default_all | `min_signal_score=30, signal_mode=all, max_holding_bars=0, watch_confirm_bars=20` | 104716.19 | 4.7162% | 155.5394% | -150.8232% | -4.6198% | 1 | n/a | n/a |
| confirmation_t3 | `min_signal_score=30, signal_mode=confirmation, max_holding_bars=0, watch_confirm_bars=20` | 104716.19 | 4.7162% | 155.5394% | -150.8232% | -4.6198% | 1 | n/a | n/a |
| confirmation_t3_lifecycle | `min_signal_score=30, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20` | 100478.58 | 0.4786% | 155.5394% | -155.0608% | -1.5512% | 10 | 60.0000% | 1.3169 |
| confirmation_armed_disabled | `min_signal_score=30, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=0` | 100478.58 | 0.4786% | 155.5394% | -155.0608% | -1.5512% | 10 | 60.0000% | 1.3169 |
| structure_lifecycle | `min_signal_score=24, signal_mode=structure, max_holding_bars=20, watch_confirm_bars=20` | 100822.78 | 0.8228% | 155.5394% | -154.7166% | -5.4956% | 69 | 50.0000% | 0.9815 |

### 五粮液 000858/SZSE

Fixture: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`

Rows: 726, date range: 2023-06-19 to 2026-06-18.

| Config | Params | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default_all | `min_signal_score=30, signal_mode=all, max_holding_bars=0, watch_confirm_bars=20` | 99185.16 | -0.8148% | -52.8208% | 52.0060% | -3.4008% | 2 | 0.0000% | 0.0000 |
| confirmation_t3 | `min_signal_score=30, signal_mode=confirmation, max_holding_bars=0, watch_confirm_bars=20` | 99185.16 | -0.8148% | -52.8208% | 52.0060% | -3.4008% | 2 | 0.0000% | 0.0000 |
| confirmation_t3_lifecycle | `min_signal_score=30, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=20` | 100621.73 | 0.6217% | -52.8208% | 53.4425% | -1.2718% | 2 | 100.0000% | n/a |
| confirmation_armed_disabled | `min_signal_score=30, signal_mode=confirmation, max_holding_bars=20, watch_confirm_bars=0` | 100621.73 | 0.6217% | -52.8208% | 53.4425% | -1.2718% | 2 | 100.0000% | n/a |
| structure_lifecycle | `min_signal_score=24, signal_mode=structure, max_holding_bars=20, watch_confirm_bars=20` | 94490.29 | -5.5097% | -52.8208% | 47.3111% | -5.8528% | 62 | 29.0323% | 0.2409 |

## Interpretation

The two fixed fixtures produce the same benchmark rows with `watch_confirm_bars=20` and `watch_confirm_bars=0`. That means the current real fixture signal sequence does not include a watch-tagged T1 divergence later consumed by an eligible same-direction confirmation/T2/T3 signal. The strategy-level state machine is still covered by deterministic patched-signal tests, so future analyzer work can safely emit richer watch-to-confirm chains without changing the strategy contract again.

This is validation, not parameter tuning. The next Chan strategy slice should deepen same-level decomposition and buy/sell point hierarchy so watch, repair, and confirmation lineage are more explicit in analyzer output.

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Evidence:

- App loaded at `http://127.0.0.1:5173/`.
- Page title: `AI量化平台`.
- Strategy Workshop rendered.
- `缠论结构策略` / `ChanStructureStrategy` could be selected.
- Visible fields included `背驰观察有效期`, its T1 背驰说明, `信号模式`, and `最大持仓天数`.
- Browser console errors: none.
- Screenshot: `/tmp/ai_trade_system_chan_watch_divergence_arming.png`.
