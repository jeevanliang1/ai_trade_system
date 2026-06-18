# Chan Indicator Divergence Scoring QA

## Scope

This QA record covers the Chan analyzer slice that adds MACD and volume-backed divergence evidence plus dynamic confirmation scoring.

Changed behavior:

- `ChanDivergence` now records `base_score`, `macd_strength`, `volume_strength`, `confirmation_score`, `macd_reference`, `macd_current`, `volume_reference`, and `volume_current`.
- Divergence and confirmation signals use dynamic buy/sell scores derived from segment energy, MACD pressure, volume participation, and confirmation evidence.
- The API overlay serializes the new divergence evidence fields.
- Frontend Chan overlay types now keep stroke-index metadata on `ChanSegmentOverlay` and expose the new divergence evidence fields.

## TDD Evidence

Red command:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_scores_divergence_with_macd_and_volume_evidence tests/test_research_signals.py::test_chan_structure_overlay_exposes_indicator_divergence_evidence -q
```

Initial expected failures:

- `AttributeError: 'ChanDivergence' object has no attribute 'base_score'`
- `AttributeError: 'ChanDivergenceOverlay' object has no attribute 'base_score'`

Green command:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_scores_divergence_with_macd_and_volume_evidence tests/test_research_signals.py::test_chan_structure_overlay_exposes_indicator_divergence_evidence -q
```

Result:

```text
2 passed in 0.41s
```

Targeted regression:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py tests/test_builtin_popular_strategies.py tests/test_api_routes.py -q
cd frontend && npm test -- --run src/pages/chartOptions.test.ts
```

Results:

```text
53 passed in 1.52s
6 passed
```

## Full Verification

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

Results:

```text
111 passed in 4.81s
18 passed, 87 tests passed
vite build succeeded
```

## Fixed Benchmark Backtests

Strategy: `ChanStructureStrategy`

Parameters:

- `min_bars=60`
- `lookback=160`
- `min_stroke_bars=5`
- `min_rebound_pct=0.03`
- `min_signal_score=24.0`
- `trade_size=100`
- initial cash `100000.0`
- default `BacktestConfig` commission, slippage, and max order cash

### 中芯国际 688981/SSE

- Fixture: `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
- Rows: `720`
- Date range: `2023-06-19` to `2026-06-18`
- Final equity: `104415.73`
- Strategy return: `4.4157%`
- Benchmark return: `155.5394%`
- Excess return: `-151.1237%`
- Max drawdown: `-5.1712%`
- Trade count: `59`
- Win rate: `48.2759%`
- Profit factor: `1.4314`
- Exposure: `4.0578%`

### 五粮液 000858/SZSE

- Fixture: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`
- Rows: `726`
- Date range: `2023-06-19` to `2026-06-18`
- Final equity: `93318.64`
- Strategy return: `-6.6814%`
- Benchmark return: `-52.8208%`
- Excess return: `46.1394%`
- Max drawdown: `-6.7334%`
- Trade count: `62`
- Win rate: `25.8065%`
- Profit factor: `0.1678`
- Exposure: `3.1800%`

The default threshold configuration produced the same trade counts as the strict segment baseline. This slice improves signal evidence and dynamic score semantics; it does not tune entry or exit thresholds.

## Browser QA

Command:

```bash
./scripts/run_app.sh
```

Surface:

- URL: `http://127.0.0.1:5173/`
- Page title: `AI量化平台`
- Workspace: `策略工坊`

Checks:

- Clicked `缠论/RSI研判`.
- Verified the `显示缠论结构` checkbox exists and starts checked.
- Toggled the checkbox off and back on.
- Verified final checked state is `true`.
- Verified two chart canvases render with sizes `492x360` and `492x130`.
- Browser console warn/error log count: `0`.

Screenshot:

```text
/tmp/ai_trade_system_chan_indicator_divergence_scoring.png
```

## Follow-Up

Next strategy-development step should tune `ChanStructureStrategy` scoring thresholds and structure parameters against the fixed 中芯国际 and 五粮液 benchmark fixtures now that indicator-backed divergence scoring is stable.
