# Chan recursive confirmation QA

Date: 2026-06-19

## Scope

Deepened `research.chan_structure` with:

- recursive stroke/segment pivots that can extend beyond the initial three-component center;
- divergence records with nearest recursive pivot context;
- watchable pending divergence signals before confirmation;
- later confirmation signals after repair threshold or structural break;
- API overlay and frontend type fields for divergence pivot context.

## TDD Evidence

Initial targeted run before implementation:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_research_signals.py::test_chan_structure_extends_recursive_pivots_beyond_three_components \
  tests/test_research_signals.py::test_chan_structure_divergence_carries_recursive_pivot_context \
  tests/test_research_signals.py::test_chan_structure_keeps_divergence_watchable_until_later_confirmation \
  tests/test_research_signals.py::test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences -q
```

Result before implementation: 4 failed. Missing extended pivots, divergence pivot fields, watch tags, and overlay fields.

After implementation:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_research_signals.py::test_chan_structure_extends_recursive_pivots_beyond_three_components \
  tests/test_research_signals.py::test_chan_structure_divergence_carries_recursive_pivot_context \
  tests/test_research_signals.py::test_chan_structure_keeps_divergence_watchable_until_later_confirmation \
  tests/test_research_signals.py::test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences -q
```

Result: 4 passed in 0.37s.

Additional targeted checks:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
```

Result: 21 passed in 0.48s.

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py -q
```

Result: 32 passed in 1.96s.

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: 122 passed in 6.08s.

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
| confirmation | `signal_mode=confirmation`, `min_signal_score=30`, `max_holding_bars=0` | 100000.00 | 0.0000% | 155.5394% | -155.5394% | 0.0000% | 0 | n/a | n/a |
| confirmation_lifecycle | `signal_mode=confirmation`, `min_signal_score=30`, `max_holding_bars=20` | 100000.00 | 0.0000% | 155.5394% | -155.5394% | 0.0000% | 0 | n/a | n/a |
| structure_lifecycle | `signal_mode=structure`, `min_signal_score=24`, `max_holding_bars=20` | 100822.78 | 0.8228% | 155.5394% | -154.7166% | -5.4956% | 69 | 50.0000% | 0.9815 |

### 五粮液 000858/SZSE

Fixture: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`

Rows: 726, date range: 2023-06-19 to 2026-06-18.

| Config | Params | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default_all | `signal_mode=all`, `min_signal_score=30`, `max_holding_bars=0` | 99185.16 | -0.8148% | -52.8208% | 52.0060% | -3.4008% | 2 | 0.0000% | 0.0000 |
| confirmation | `signal_mode=confirmation`, `min_signal_score=30`, `max_holding_bars=0` | 100000.00 | 0.0000% | -52.8208% | 52.8208% | 0.0000% | 0 | n/a | n/a |
| confirmation_lifecycle | `signal_mode=confirmation`, `min_signal_score=30`, `max_holding_bars=20` | 100000.00 | 0.0000% | -52.8208% | 52.8208% | 0.0000% | 0 | n/a | n/a |
| structure_lifecycle | `signal_mode=structure`, `min_signal_score=24`, `max_holding_bars=20` | 94490.29 | -5.5097% | -52.8208% | 47.3111% | -5.8528% | 62 | 29.0323% | 0.2409 |

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Evidence:

- App loaded at `http://127.0.0.1:5173/`.
- Page title: `AI量化平台`.
- Strategy Workshop rendered with `ChanStructureStrategy` selected.
- Visible fields included `信号模式` and `最大持仓天数`.
- Browser page errors: none.
- Browser console errors: none.
- Screenshot: `/tmp/ai_trade_system_chan_core_deepening.png`.

## Interpretation

The analyzer now emits richer structure semantics, but the fixed benchmark confirmation-only strategy still has no trades for these two fixtures with the current `min_signal_score=30` threshold. The next strategy-development slice should tune confirmation signal persistence/scoring or add more direct strategy consumption of watch-to-confirm transitions, then rerun the same fixtures.
