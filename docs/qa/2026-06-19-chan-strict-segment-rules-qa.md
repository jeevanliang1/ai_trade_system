# Chan Strict Segment Rules QA

Date: 2026-06-19

## Scope

Validate the strict segment split/break/rebuild slice for `research.chan_structure`:

- Replace overlapping three-stroke sliding-window segments with non-overlapping stateful segments.
- Record segment source metadata: start stroke index, end stroke index, and break stroke index.
- Preserve segment-level recursive pivots and divergence/confirmation signals on explicit break/rebuild samples.
- Expose new segment metadata through preview overlay payloads and frontend types.
- Record fixed benchmark backtests for 中芯国际 and 五粮液 because `ChanStructureStrategy` behavior can change.

## TDD Evidence

RED checks:

- `PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_builds_non_overlapping_segments_from_breaks tests/test_research_signals.py::test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences -q`
  - Failed with `AttributeError: 'ChanSegment' object has no attribute 'start_stroke_index'`.
  - Failed with `AttributeError: 'ChanSegmentOverlay' object has no attribute 'start_stroke_index'`.

GREEN checks:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py tests/test_builtin_popular_strategies.py tests/test_api_routes.py -q
```

Result: `51 passed in 1.44s`

```bash
cd frontend && npm test -- --run src/pages/chartOptions.test.ts
```

Result: `6 passed`

## Full Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: `109 passed in 2.47s`

```bash
cd frontend && npm test -- --run
```

Result: `18 passed`, `87 passed`

```bash
cd frontend && npm run build
```

Result: TypeScript and Vite production build completed successfully.

## Fixed Benchmark Backtest

Execution used the fixed local qfq daily-bar fixtures and default `ChanStructureStrategy` parameters:

- `min_bars=60`
- `lookback=160`
- `min_stroke_bars=5`
- `min_rebound_pct=0.03`
- `min_signal_score=24.0`
- `trade_size=100`

Backtest config:

- `initial_cash=100000`
- `commission_rate=0.0003`
- `slippage=0.01`
- `max_order_cash=50000`

| Stock | Local CSV | Rows | Date Range | Final Equity | Strategy Return | Benchmark Return | Excess Return | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 中芯国际 `688981/SSE` | `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv` | 720 | 2023-06-19 to 2026-06-18 | 104415.73 | 4.4157% | 155.5394% | -151.1237% | -5.1712% | 59 | 48.2759% | 1.4314 |
| 五粮液 `000858/SZSE` | `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv` | 726 | 2023-06-19 to 2026-06-18 | 93318.64 | -6.6814% | -52.8208% | 46.1394% | -6.7334% | 62 | 25.8065% | 0.1678 |

Interpretation:

- Strict segment split/break/rebuild removes the extra overlapping segment confirmations from the prior slice.
- The benchmark reverts to the earlier first-cut `ChanStructureStrategy` trade profile while preserving lower drawdown on both fixtures.
- This is still no-tuning validation; MACD/volume divergence and parameter work remain follow-up.

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Flow:

- Open `http://127.0.0.1:5173/`.
- Confirm page title `AI量化平台`.
- Use the default Strategy Workshop view.
- Click `缠论/RSI研判`.
- Confirm `显示缠论结构` exists and can toggle off/back on.

Evidence:

- Page URL: `http://127.0.0.1:5173/`.
- Page title: `AI量化平台`.
- Strategy Workshop rendered nonblank with real strategy/data content.
- Research preview rendered Chan summary text containing `分型` and `中枢`.
- K-line and volume charts rendered as two canvases, `492x360` and `492x130`.
- `显示缠论结构` ended checked after toggle verification.
- Browser console `warn/error` logs were empty.
- Screenshot: `/tmp/ai_trade_system_chan_strict_segment_rules.png` (`1280x720`).

## Follow-Up

Next Chan development item: add MACD/volume divergence strength and confirmation scoring on top of the stricter segment model before parameter tuning.
