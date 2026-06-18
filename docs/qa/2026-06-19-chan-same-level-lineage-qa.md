# Chan Same-Level Lineage QA

## Scope

This QA record covers adding explicit same-level decomposition identity and buy/sell point lineage metadata to `research.chan_structure`.

Implemented behavior:

- `ResearchSignal` now supports JSON-safe `metadata`.
- `ChanSegment` carries `level`, `sequence_index`, and deterministic `lineage_id`.
- `ChanSegmentOverlay` and frontend types expose the same-level segment identity fields.
- T1 divergence/watch/confirm, T2, and T3 Chan structure signals now carry:
  - `level`
  - `point_type`
  - `pivot_relation`
  - `lineage`
  - related pivot/fractal/segment indexes where applicable
- Chan structure signal reasons include a readable hierarchy suffix such as `层级 segment，关系 inside-segment-pivot，链路 segment:...`.

## TDD Evidence

Initial targeted RED command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_research_signals.py::test_chan_structure_segments_carry_same_level_sequence_and_lineage \
  tests/test_research_signals.py::test_chan_structure_divergence_signals_carry_hierarchy_metadata \
  tests/test_research_signals.py::test_chan_structure_second_and_third_points_carry_pivot_lineage \
  tests/test_research_signals.py::test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences -q
```

RED result before implementation:

- 4 failed.
- Failures were missing `ChanSegment.level`, missing `ResearchSignal.metadata`, and missing `ChanSegmentOverlay.level`.

GREEN result after implementation:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_research_signals.py::test_chan_structure_segments_carry_same_level_sequence_and_lineage \
  tests/test_research_signals.py::test_chan_structure_divergence_signals_carry_hierarchy_metadata \
  tests/test_research_signals.py::test_chan_structure_second_and_third_points_carry_pivot_lineage \
  tests/test_research_signals.py::test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences -q
```

Result: `4 passed in 0.34s`.

Broader targeted result:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py -q
```

Result: `24 passed in 0.40s`.

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: `131 passed in 5.94s`.

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

The benchmark rows match the previous Chan watch-divergence arming slice. This is expected because the implementation adds metadata, lineage, tags, and reason text without changing signal action, score, thresholds, or lifecycle state.

The practical value is downstream traceability: strategy filters, Signal Radar diagnostics, and future UI details can now distinguish first/second/third buy-sell point families, pivot relationships, and segment lineage without parsing Chinese reason text.

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
- Visible fields included `背驰观察有效期`, `信号模式`, `最大持仓天数`, and research/signal preview panel copy.
- Browser console errors: none.
- Screenshot: `/tmp/ai_trade_system_chan_same_level_lineage.png`.
