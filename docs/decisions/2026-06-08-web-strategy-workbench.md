# Web Strategy Workbench Decision

Date: 2026-06-08

## Decision

The Streamlit console is a strategy workbench, not only a data viewer. It must support:

- Managing user strategy files under `strategies/`.
- Editing and saving trusted user strategy source from the web page.
- Discovering built-in and user strategies through `strategy_registry`.
- Selecting any discovered strategy for signal preview, backtesting, and paper trading.
- Rendering strategy constructor parameters as web inputs.

## Context

The first web version hard-coded `DualMovingAverageStrategy`, which made the UI look interactive while still preventing real strategy choice. That was not acceptable for a quant system where the user expects to plug in and compare strategies.

The current approach keeps the strategy core pure Python:

```text
Bar -> Strategy.on_bar -> Signal
```

This keeps strategies easy to test, easy to edit, and later adaptable to vn.py `CtaTemplate`.

## Built-In Strategy Set

The built-in strategy set focuses on common single-symbol daily strategies that the current engine can support correctly:

- `DualMovingAverageStrategy`: trend following.
- `RsiMeanReversionStrategy`: RSI mean reversion.
- `BollingerMeanReversionStrategy`: Bollinger mean reversion.
- `DonchianBreakoutStrategy`: Donchian/Turtle breakout.
- `PriceMomentumStrategy`: price momentum.

Pairs trading, statistical arbitrage, and multi-factor rotation are not built in yet because they need multi-symbol synchronized data, portfolio construction, and allocation logic. Adding them to the current single-symbol engine would create misleading behavior.

## Consequences

- The web app can compare strategies without code changes.
- User strategies run as local Python code, so the UI must warn that only trusted strategy code should be executed.
- Future live trading remains out of scope until broker interfaces and operational risk rules are explicitly defined.
