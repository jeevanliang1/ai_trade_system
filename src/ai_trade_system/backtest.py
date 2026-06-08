from __future__ import annotations

from dataclasses import dataclass

from ai_trade_system.market import Bar
from ai_trade_system.paper import PaperBroker, RiskLimits, Trade
from ai_trade_system.strategy import Strategy


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000
    commission_rate: float = 0.0003
    slippage: float = 0.01
    max_order_cash: float = 50_000


@dataclass(frozen=True)
class EquityPoint:
    trading_day: object
    equity: float
    cash: float
    close_price: float


@dataclass(frozen=True)
class BacktestResult:
    final_equity: float
    equity_curve: list[EquityPoint]
    trades: list[Trade]


def run_backtest(bars: list[Bar], strategy: Strategy, config: BacktestConfig | None = None) -> BacktestResult:
    if not bars:
        raise ValueError("bars cannot be empty")
    config = config or BacktestConfig()
    broker = PaperBroker(
        initial_cash=config.initial_cash,
        risk_limits=RiskLimits(max_order_cash=config.max_order_cash),
        commission_rate=config.commission_rate,
        slippage=config.slippage,
    )
    equity_curve: list[EquityPoint] = []
    marks: dict[str, float] = {}

    strategy.on_init()
    strategy.on_start()
    try:
        for bar in bars:
            marks[bar.symbol] = bar.close_price
            for signal in strategy.on_bar(bar):
                if signal.action == "buy":
                    broker.buy(signal.symbol, signal.price, signal.volume, trading_day=bar.trading_day)
                elif signal.action == "sell":
                    broker.sell(signal.symbol, signal.price, signal.volume, trading_day=bar.trading_day)
            equity_curve.append(
                EquityPoint(
                    trading_day=bar.trading_day,
                    equity=broker.equity(marks),
                    cash=broker.cash,
                    close_price=bar.close_price,
                )
            )
    finally:
        strategy.on_stop()

    return BacktestResult(
        final_equity=equity_curve[-1].equity,
        equity_curve=equity_curve,
        trades=list(broker.trades),
    )
