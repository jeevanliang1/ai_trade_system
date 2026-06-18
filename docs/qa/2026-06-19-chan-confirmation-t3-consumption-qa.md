# Chan confirmation T3 consumption QA

Date: 2026-06-19

## Scope

Updated `ChanStructureStrategy` confirmation mode so it can consume Chan third-buy and third-sell signals. T3 is treated as a confirmation-style setup because it represents leaving a pivot and retesting without returning into the pivot range. T2 remains a structure-only signal.

## TDD Evidence

RED check:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_confirmation_mode_trades_third_buy_and_sell -q
```

Result before implementation: failed because `signal_mode="confirmation"` returned no signals for patched `CHAN_STRUCT_BUY_T3` and `CHAN_STRUCT_SELL_T3`.

GREEN checks:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_confirmation_mode_trades_third_buy_and_sell \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_signal_mode_filters_structure_family \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_signal_mode_filters_confirmation_family -q
```

Result: 3 passed in 1.41s. The T2-only structure-family test still confirms confirmation mode does not admit lower-confidence T2 signals.

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py -q
```

Result: 9 passed in 0.47s.

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: 123 passed in 6.11s.

```bash
cd frontend && npm test -- --run
```

Result: 18 test files passed, 87 tests passed.

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
| default_all | `signal_mode=all`, `min_signal_score=30`, `max_holding_bars=0` | 104716.19 | 4.7162% | 155.5394% | -150.8232% | -4.6198% | 1 | n/a | n/a |
| confirmation_t3 | `signal_mode=confirmation`, `min_signal_score=30`, `max_holding_bars=0` | 104716.19 | 4.7162% | 155.5394% | -150.8232% | -4.6198% | 1 | n/a | n/a |
| confirmation_t3_lifecycle | `signal_mode=confirmation`, `min_signal_score=30`, `max_holding_bars=20` | 100478.58 | 0.4786% | 155.5394% | -155.0608% | -1.5512% | 10 | 60.0000% | 1.3169 |
| structure_lifecycle | `signal_mode=structure`, `min_signal_score=24`, `max_holding_bars=20` | 100822.78 | 0.8228% | 155.5394% | -154.7166% | -5.4956% | 69 | 50.0000% | 0.9815 |

### 五粮液 000858/SZSE

Fixture: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`

Rows: 726, date range: 2023-06-19 to 2026-06-18.

| Config | Params | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default_all | `signal_mode=all`, `min_signal_score=30`, `max_holding_bars=0` | 99185.16 | -0.8148% | -52.8208% | 52.0060% | -3.4008% | 2 | 0.0000% | 0.0000 |
| confirmation_t3 | `signal_mode=confirmation`, `min_signal_score=30`, `max_holding_bars=0` | 99185.16 | -0.8148% | -52.8208% | 52.0060% | -3.4008% | 2 | 0.0000% | 0.0000 |
| confirmation_t3_lifecycle | `signal_mode=confirmation`, `min_signal_score=30`, `max_holding_bars=20` | 100621.73 | 0.6217% | -52.8208% | 53.4425% | -1.2718% | 2 | 100.0000% | n/a |
| structure_lifecycle | `signal_mode=structure`, `min_signal_score=24`, `max_holding_bars=20` | 94490.29 | -5.5097% | -52.8208% | 47.3111% | -5.8528% | 62 | 29.0323% | 0.2409 |

## Interpretation

The confirmation-mode zero-trade blocker is resolved for the fixed fixtures without lowering the score threshold or admitting T2 signals. The lifecycle configuration now produces lower-drawdown confirmation-style trades on both fixtures. Next Chan work should add an explicit watch-divergence arming state so T1 watch signals can later be confirmed by repair bars or T2/T3 structures.

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Evidence:

- App loaded at `http://127.0.0.1:5173/`.
- Page title: `AI量化平台`.
- Strategy Workshop rendered with `ChanStructureStrategy` selected.
- Visible text included the updated confirmation-mode description, `信号模式`, and `最大持仓天数`.
- Browser console errors: none.
- Screenshot: `/tmp/ai_trade_system_chan_confirmation_t3.png`.
