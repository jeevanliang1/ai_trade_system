# Chan And Enhanced RSI Signal Preview Design

## Goal

Build the first integration slice from `MambaWoW/market_analysis` into `ai_trade_system`: a single-symbol research signal preview that scans the currently loaded A-share K-line data for Chan-style structure signals and enhanced RSI exhaustion/risk scoring.

This first slice is a research and timing layer. It does not place orders, does not add live trading behavior, does not require ClickHouse, and does not introduce full-market scanning.

## Scope

The first implementation will add a signal preview for the currently selected symbol and CSV/data settings already used by the React + FastAPI platform.

Included:

- Convert existing `Bar` rows to an internal OHLCV frame for research calculations.
- Detect lightweight Chan-style second buy, third buy, second sell, and third sell structure signals from local K-line data.
- Compute enhanced RSI risk and signal-quality context:
  - RSI overbought and oversold states.
  - Prior-peak RSI bearish divergence.
  - Optional trend-health context from medium/long moving averages.
  - Final quality score that can promote, keep, or downgrade a Chan signal.
- Add a local FastAPI endpoint returning signal points, score details, and blockers.
- Display the result inside the existing React workbench, preferably in Strategy Workshop or Backtest Center result tabs, with K-line markers and a compact signal table.
- Keep the system research-only: the preview can inform backtests but cannot bypass `PaperBroker`, `risk`, or future execution controls.

Excluded from this first implementation:

- Full-market stock screening.
- ClickHouse ingestion or database persistence.
- The `market_analysis` Dashboard, strong-stock pool, ETF rotation, and OpenRouter CIO memo.
- Direct `chan-py` + ClickHouse adapter. The first version should use a lightweight in-repo detector and leave an adapter seam for a later official Chan engine.
- Automatic paper/live trading from these signals.

## Source Interpretation

`market_analysis` has two relevant strategy families for this slice:

- Chan pattern logic: second buy/third buy and mirrored sell patterns from `python/core/signals/chan_analyzer.py`, plus heavier `chan_signal.py` using `chan-py` and ClickHouse.
- Enhanced signal scoring: RSI divergence and exhaustion ideas from `python/core/chan/chan_scorer.py` and auxiliary extreme-signal logic in `python/core/signals/auxiliary_signals.py`.

Because the external repository currently has no visible license file in the cloned snapshot, implementation should re-create the behavior and data contracts in `ai_trade_system` style instead of copying large source blocks verbatim.

## Architecture

Add a small research package:

```text
src/ai_trade_system/research/
  __init__.py
  models.py
  dataframe.py
  chan.py
  enhanced_rsi.py
  service.py
```

Responsibilities:

- `models.py`: immutable result models such as `ResearchSignal`, `SignalScore`, `SignalPreviewResult`, and `SignalBlocker`.
- `dataframe.py`: convert `list[Bar]` to a pandas DataFrame with `open`, `high`, `low`, `close`, `volume`, `turnover`, indexed by trading day.
- `chan.py`: a lightweight detector over OHLCV data. It should expose a stable function such as `scan_chan_patterns(frame, config)` and return normalized `ResearchSignal` rows.
- `enhanced_rsi.py`: RSI series, overbought/oversold classification, prior-peak divergence detection, and score adjustment helpers.
- `service.py`: orchestrate data conversion, pattern scan, RSI scoring, blocker collection, and final sorting.

The API layer should add request and response schemas in `src/ai_trade_system/api/schemas.py`, service functions in `src/ai_trade_system/api/service.py`, and a route in `src/ai_trade_system/api/app.py`:

```text
POST /api/research/signals/preview
```

The frontend should add types and client method in `frontend/src/types.ts` and `frontend/src/api/client.ts`, then surface the preview in an existing page. The preferred first UI placement is a Strategy Workshop tab or panel because the user already studies K-line, signal preview, strategy params, and backtest output there.

## Data Flow

```text
PlatformSettings
  -> existing load_data path
  -> list[Bar]
  -> research.dataframe.bars_to_frame
  -> research.chan.scan_chan_patterns
  -> research.enhanced_rsi.score_signal_context
  -> SignalPreviewResult
  -> React signal table + chart markers + inspector summary
```

The endpoint should use the same data source behavior as existing data/backtest requests: load the configured CSV when available and return a clear blocker when the data cannot be loaded.

## Signal Semantics

Chan signals:

- `CHAN_BUY_T2`: class-two buy or class-two-like buy. A later pullback does not break the prior pullback low, or only breaks within a configured tolerance.
- `CHAN_BUY_T3`: third buy. A pullback after leaving a central range stays above the range top.
- `CHAN_SELL_T2`: mirrored class-two sell.
- `CHAN_SELL_T3`: mirrored third sell.

Enhanced RSI signals and scoring:

- `RSI_OVERBOUGHT`: latest RSI is above the configured overbought threshold.
- `RSI_OVERSOLD`: latest RSI is below the configured oversold threshold.
- `RSI_BEARISH_DIVERGENCE`: price makes a higher recent peak while RSI fails to make a higher peak.
- `RSI_BULLISH_RECOVERY`: optional positive context when RSI recovers from oversold while price stabilizes.

Quality score:

- Start with a base score from signal type.
- Add small positive context when medium/long trend remains intact.
- Subtract for RSI bearish divergence, severe overbought, ATR-like overheat if implemented in this slice, or missing confirmation data.
- Clamp to a stable range, for example `0..100`.

The first version should make score details explicit so the user can inspect why a signal was upgraded or downgraded.

## Error Handling

The preview must return structured blockers instead of failing silently:

- `NO_BARS`: no data loaded.
- `INSUFFICIENT_BARS`: fewer than the minimum bars needed for Chan or RSI calculations.
- `UNSUPPORTED_DATA`: required OHLCV fields missing or invalid.
- `OPTIONAL_ENGINE_UNAVAILABLE`: future use only, when a heavier Chan engine is requested but not installed.

FastAPI should return normal `200` responses for valid requests with blockers, and `400` only for invalid request payloads or unsafe paths already covered by existing API protections.

## UI Design

Keep the first UI small and functional:

- Add a button or action near existing signal/backtest controls: `扫描缠论+RSI`.
- Add a compact result section with:
  - latest signal summary,
  - table of date, type, side, price, final score, and reason,
  - score detail chips for RSI divergence, overbought/oversold, and trend context,
  - empty state when no signal is found.
- Reuse existing K-line chart marker patterns for buy/sell/warning markers.
- Show blockers as explicit user-facing messages.

Avoid creating a new full page in the first implementation. A dedicated Signal Radar page can be a later phase after this preview proves useful.

## Testing

Backend tests:

- `bars_to_frame` converts `Bar` rows into correctly named and sorted OHLCV data.
- RSI returns stable values for rising, falling, and flat series.
- RSI divergence detects a higher-price/lower-RSI prior-peak pattern.
- Chan scanner returns no signals for insufficient bars.
- Chan scanner returns deterministic second-buy and third-buy signals on synthetic OHLCV fixtures.
- API endpoint returns blockers for missing or insufficient data and signals for valid fixtures.

Frontend tests:

- The preview action calls the new client method.
- Loading, empty, blocker, and populated states render.
- Signal score and reason text appear without layout breakage.

Verification:

- Run `python -m pytest`.
- Run `cd frontend && npm test`.
- Run `cd frontend && npm run build`.
- Run browser QA on `http://localhost:5173` and capture headless screenshots when the UI is changed.

## Follow-Up Phases

Phase 2 can wrap the signal preview as a backtestable `Strategy` such as `ChanRsiTimingStrategy`.

Phase 3 can add a dedicated Signal Radar page and batch scan across selected A-share watchlists.

Phase 4 can add an optional `chan-py` adapter if dependency, data-source, and licensing constraints are resolved.

Phase 5 can combine this signal layer with market-wide RS/VAIF stock selection.

## Open Decisions

The approved first implementation should use a lightweight in-repo detector and not depend on ClickHouse or `chan-py`.

The first UI should live in an existing workbench page, with Strategy Workshop preferred unless implementation discovery shows Backtest Center is a cleaner fit.
