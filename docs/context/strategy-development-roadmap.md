# Strategy Development Roadmap

Date: 2026-06-19

## Purpose

This file records how the "top ten quant strategy schemes" request maps onto the current A-share, daily-bar, single-symbol, long-only strategy engine.

The implemented strategies are research and backtest templates. They are not return promises and do not enable live trading.

## Source Basis

The strategy families below were selected from common quantitative trading categories that can be implemented with daily OHLCV data and the current engine:

- Trend following, mean reversion, arbitrage, and execution-style algorithmic categories: https://www.investopedia.com/articles/active-trading/101014/basics-algorithmic-trading-concepts-and-examples.asp
- Statistical arbitrage, factor investing, and risk-parity categories: https://www.investopedia.com/articles/trading/09/quant-strategies.asp
- Academic and implementation-oriented strategy library reference: https://www.quantconnect.com/docs/v2/writing-algorithms/strategy-library
- Momentum and rotation reference for future multi-symbol expansion: https://quantpedia.com/strategies/sector-momentum-rotational-system
- Pairs trading/statistical-arbitrage reference for future multi-symbol long-short expansion: https://portfoliooptimizationbook.com/book/15.3-pairs-trading-overview.html

## Current Ten Built-In Strategies

1. `DualMovingAverageStrategy`: moving-average trend following.
2. `RsiMeanReversionStrategy`: RSI oversold/overbought mean reversion.
3. `BollingerMeanReversionStrategy`: Bollinger-band mean reversion.
4. `DonchianBreakoutStrategy`: channel breakout trend following.
5. `PriceMomentumStrategy`: fixed-window price momentum.
6. `VolumeConfirmedMomentumStrategy`: price momentum confirmed by volume and trend, with tuned holding and trailing-stop exits.
7. `ChanRsiResearchStrategy`: Chan + enhanced RSI research signal wrapper.
8. `ChanStructureStrategy`: Chan structure, point-family filters, certainty-based position sizing, and risk caps.
9. `MacdTrendStrategy`: MACD cross trend strategy with a long trend filter.
10. `AtrVolatilityBreakoutStrategy`: volatility breakout with ATR stop, ATR trailing exit, and time exit.

## Current Combination Support

`PortfolioStrategy` already combines multiple strategies for one symbol through:

- `weighted_vote`
- `equal_vote`
- `first_active`

The React Portfolio Lab can edit allocations and run portfolio previews/backtests through this layer.

Portfolio Lab also exposes three preconfigured templates:

- `conservative_trend_reversion`: trend confirmation plus RSI/Bollinger mean reversion.
- `momentum_breakout_stack`: volume momentum, ATR/Donchian breakout, price momentum, and MACD confirmation.
- `chan_research_stack`: Chan structure, Chan RSI research, volume momentum, and ATR confirmation.

## Deferred Strategy Families

These are good quantitative strategy families but need engine expansion before they should be first-class built-ins:

- Pairs trading/statistical arbitrage: needs multi-symbol synchronized bars and long-short or spread accounting.
- Factor rotation/sector momentum: needs cross-sectional ranking, multi-symbol holdings, and allocation rebalancing.
- Risk parity: needs portfolio-level volatility/covariance estimates and multi-asset sizing.
- Market making/execution algorithms: not appropriate for the current daily-bar research scaffold.
- Machine-learning signal models: need feature storage, training/validation splits, model persistence, and overfitting controls.

## Next Practical Slice

Tune the preset combinations for lower turnover and drawdown, then consider expanding the engine for true multi-symbol strategies such as pairs trading, factor rotation, and risk parity.
