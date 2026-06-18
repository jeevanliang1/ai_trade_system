# Volume-Confirmed Momentum Strategy Design

Date: 2026-06-19

## Goal

Build the first dedicated A-share volume-price momentum strategy for the current strategy engine. The strategy must be usable in the existing React + FastAPI workbench, local backtests, and paper-trading replay, while staying inside the project's current boundary: single-symbol daily bars, long-only signals, public/local market data, and no live trading.

## Chosen Approach

Add a new built-in strategy named `VolumeConfirmedMomentumStrategy` under `src/ai_trade_system/strategies/`.

The strategy enters only when price momentum and volume confirmation agree:

- Price momentum: current close is higher than the close `momentum_window` bars ago by at least `min_momentum_pct`.
- Volume confirmation: current volume is at least `volume_multiplier` times the average volume over `volume_window`.
- Trend filter: current close is above the average close over `trend_window`.

The strategy exits when momentum weakens, trend breaks, or the position has been held for too many bars:

- Momentum exit: current close is not higher than the close `momentum_window` bars ago.
- Trend exit: current close falls below the `trend_window` average close.
- Time exit: `max_holding_bars` is reached after entry.

## Parameters

- `symbol`: target stock code. The React workbench should keep using the shared stock selector and existing strategy parameter plumbing.
- `momentum_window`: price lookback window. Higher values require a longer trend; lower values react faster.
- `min_momentum_pct`: minimum price rise required for entry. Higher values reduce trades and favor stronger breakouts.
- `volume_window`: volume baseline window. Higher values make the volume baseline steadier; lower values react faster.
- `volume_multiplier`: volume expansion threshold. Higher values require stronger market participation.
- `trend_window`: trend filter window. Higher values favor broader uptrends; lower values are more responsive.
- `max_holding_bars`: maximum holding period. Higher values allow longer trend participation; lower values force quicker exits.
- `trade_size`: fixed order size emitted in `Signal`.

## Integration

The new strategy should follow the existing built-in strategy pattern:

- Inherit `ai_trade_system.strategy.Strategy`.
- Emit only `Signal("buy", ...)` and `Signal("sell", ...)`.
- Ignore bars for other symbols.
- Track only local strategy state needed for open-position and hold-duration decisions.
- Register through the existing built-in strategy discovery path so `/api/strategies`, Strategy Workshop, Backtest Center, Portfolio Lab, and Paper Trading can all see it without new frontend-specific code.
- Add Chinese display metadata and parameter guidance through `strategy_registry` so the UI shows a Chinese name, plain-language description, and tuning impact.

Suggested display name: `量价动量策略`.

Suggested description: `价格上涨动量、成交量放大和趋势过滤同时满足时买入；动量转弱、跌破趋势或持仓超期时卖出。`

## Data Flow

1. React or CLI selects a strategy and parameter values.
2. FastAPI or CLI instantiates `VolumeConfirmedMomentumStrategy`.
3. Backtest or paper replay feeds daily `Bar` objects to `on_bar`.
4. The strategy maintains rolling closes and volumes.
5. Entry and exit rules emit deterministic `Signal` objects.
6. Existing backtest, analytics, risk, and paper-trading modules consume those signals unchanged.

## Error Handling And Edge Cases

- Before enough close and volume history exists, return no signals.
- If bar volume is missing or non-positive, treat volume confirmation as failed.
- If parameter windows are too small, normalize them to sensible minimums in the constructor rather than raising UI-facing errors.
- Avoid duplicate buy signals while already in a position.
- Avoid sell signals when no position is open.
- Keep reasons explicit enough for chart markers and paper-trading logs, such as `volume_confirmed_momentum_entry`, `momentum_exit`, `trend_exit`, and `time_exit`.

## Tests

Use test-first implementation.

Python tests should cover:

- The strategy buys only when price momentum, volume expansion, and trend filter all pass.
- The strategy does not buy when volume expansion fails.
- The strategy sells when momentum weakens.
- The strategy sells when price falls below the trend average.
- The strategy sells when `max_holding_bars` is reached.
- The strategy is discoverable through the strategy registry/API metadata path with Chinese display name and parameter guidance.

After implementation, run targeted strategy tests first, then the relevant broader Python suite. Because the strategy becomes browser-visible through existing metadata, perform React platform screenshot acceptance after the code path is complete.

## Out Of Scope

- Multi-symbol ranking or portfolio rotation.
- Intraday data, tick data, short selling, or leverage.
- Live broker integration or real order placement.
- New frontend controls beyond the existing strategy discovery and parameter rendering path.
