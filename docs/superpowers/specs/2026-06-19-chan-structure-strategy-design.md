# Chan Structure Strategy Design

Date: 2026-06-19

## Goal

Build a testable first-cut Chan theory strategy that goes beyond the current lightweight swing-based `scan_chan_patterns` implementation. The strategy should identify core Chan structures from local daily bars and emit deterministic long-only signals that can run through the existing strategy registry, backtest, paper trading, and React workbench.

This is not a full multi-level Chan engine. The first version focuses on a daily-bar, single-symbol, pure-Python structure layer that can be expanded later.

## Background

Current code already has `ChanRsiResearchStrategy`, but its Chan side only detects simplified higher-low second buys and lower-high second sells from swing points. It does not model the standard structure chain:

K-line containment -> fractal -> stroke -> segment -> pivot -> buy/sell point.

The new work should add a separate Chan structure analyzer instead of overloading the lightweight existing detector.

## Scope

Create a new research module:

`src/ai_trade_system/research/chan_structure.py`

The module should provide:

- K-line containment normalization.
- Top and bottom fractal detection.
- Alternating stroke construction from valid fractals.
- Simplified segment/pivot construction from overlapping consecutive strokes.
- Structure-based second buy/sell and third buy/sell research signals.
- A result object that exposes enough structure for tests and future UI work.

Add a new built-in strategy:

`ChanStructureStrategy`

The strategy should:

- Inherit `ai_trade_system.strategy.Strategy`.
- Keep a rolling daily-bar window.
- Call the structure analyzer on each bar after enough history is available.
- Emit a buy signal for current-bar second-buy or third-buy structure signals when not already in a position.
- Emit a sell signal for current-bar second-sell or third-sell structure signals when already in a position.
- Avoid duplicate emissions for the same trading day, signal kind, and action.
- Remain pure Python and long-only.

## First-Cut Chan Rules

### Containment

When two adjacent K-lines have containment, merge them deterministically:

- In an upward context, use the higher high and higher low.
- In a downward context, use the lower high and lower low.
- In a neutral initial context, use the wider high-low range.

This keeps the analyzer stable without attempting every nuanced Chan interpretation.

### Fractals

Detect strict three-bar fractals after containment normalization:

- Top fractal: middle bar has both a higher high and higher low than its neighbors.
- Bottom fractal: middle bar has both a lower high and lower low than its neighbors.

If consecutive fractals have the same kind, keep the more extreme one:

- For tops, keep the higher high.
- For bottoms, keep the lower low.

### Strokes

Build strokes from alternating top and bottom fractals with a configurable minimum spacing:

- `min_stroke_bars`, default `5`.
- Bottom to top is an upward stroke.
- Top to bottom is a downward stroke.

The analyzer should expose stroke direction, start/end dates, high, low, and end price.

### Pivots

Construct simplified pivots from every three consecutive strokes whose price ranges overlap:

- `pivot_low = max(stroke.low for the three strokes)`.
- `pivot_high = min(stroke.high for the three strokes)`.
- A pivot exists when `pivot_low <= pivot_high`.

This is a practical first-cut central-zone approximation, not a complete recursive segment-level pivot engine.

### Signals

Generate signals from the latest structure:

- `CHAN_STRUCT_BUY_T2`: latest bottom is higher than the previous bottom and latest close has rebounded by at least `min_rebound_pct`.
- `CHAN_STRUCT_SELL_T2`: latest top is lower than the previous top and latest close has fallen by at least `min_rebound_pct`.
- `CHAN_STRUCT_BUY_T3`: a prior upward stroke leaves the latest pivot, followed by a downward pullback that does not re-enter the pivot.
- `CHAN_STRUCT_SELL_T3`: a prior downward stroke leaves the latest pivot, followed by an upward pullback that does not re-enter the pivot.

Third-class signals should rank above second-class signals when both appear on the same bar.

## Parameters

Expose these user-facing strategy parameters:

- `symbol`: target stock code.
- `min_bars`: minimum bars before analysis, default `60`.
- `lookback`: rolling window, default `160`.
- `min_stroke_bars`: minimum spacing between opposite fractals, default `5`.
- `min_rebound_pct`: second buy/sell rebound or breakdown threshold, default `0.03`.
- `min_signal_score`: minimum absolute research signal score to trade, default `24.0`.
- `trade_size`: fixed shares per emitted signal, default `100`.

## Integration

- Register `ChanStructureStrategy` in `src/ai_trade_system/strategy_registry.py`.
- Use Chinese display name `缠论结构策略`.
- Prefer a plain-language Chinese description and parameter guidance.
- Keep `ChanRsiResearchStrategy` unchanged for backward compatibility.
- Keep Signal Radar unchanged for this slice; it can use this analyzer later as another score mode.

## Tests

Use TDD.

Analyzer tests should cover:

- Containment normalization reduces adjacent contained K-lines deterministically.
- Fractal detection produces alternating top/bottom structures.
- Stroke construction respects `min_stroke_bars`.
- Pivot construction detects overlap across three strokes.
- Third buy and third sell signals are produced from explicit synthetic structures.

Strategy tests should cover:

- `ChanStructureStrategy` emits a buy signal on a current-bar structural buy signal.
- It does not emit duplicate buy signals for the same structure.
- It emits a sell signal when in position and a current-bar structural sell signal appears.
- Strategy registry exposes the Chinese display name and parameter guidance.

## Out Of Scope

- Full recursive multi-timeframe Chan analysis.
- Tick or intraday data.
- Short selling, leverage, or live trading.
- UI structure visualization of fractals/strokes/pivots.
- Signal Radar score-mode integration for Chan structure.
- Benchmark threshold tuning against 中芯国际 and 五粮液.
