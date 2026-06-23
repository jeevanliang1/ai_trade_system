from __future__ import annotations

from dataclasses import dataclass, field

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
    trade_attributions: list[TradeAttribution] = field(default_factory=list)


@dataclass(frozen=True)
class TradeAttribution:
    side: str
    symbol: str
    price: float
    volume: int
    commission: float
    trading_day: object
    signal_reason: str
    signal_family: str
    signal_label: str


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
    trade_attributions: list[TradeAttribution] = []
    marks: dict[str, float] = {}

    strategy.on_init()
    strategy.on_start()
    try:
        for bar in bars:
            bar_time = bar.timestamp or bar.trading_day
            marks[bar.symbol] = bar.close_price
            for signal in strategy.on_bar(bar):
                if signal.action == "buy":
                    result = broker.buy(signal.symbol, signal.price, signal.volume, trading_day=bar_time)
                    if result.accepted:
                        trade_attributions.append(_trade_attribution(broker.trades[-1], signal.reason))
                elif signal.action == "sell":
                    result = broker.sell(signal.symbol, signal.price, signal.volume, trading_day=bar_time)
                    if result.accepted:
                        trade_attributions.append(_trade_attribution(broker.trades[-1], signal.reason))
            equity_curve.append(
                EquityPoint(
                    trading_day=bar_time,
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
        trade_attributions=trade_attributions,
    )


def _trade_attribution(trade: Trade, signal_reason: str) -> TradeAttribution:
    family, label = classify_signal_family(signal_reason)
    return TradeAttribution(
        side=trade.side,
        symbol=trade.symbol,
        price=trade.price,
        volume=trade.volume,
        commission=trade.commission,
        trading_day=trade.trading_day,
        signal_reason=signal_reason,
        signal_family=family,
        signal_label=label,
    )


def classify_signal_family(reason: str) -> tuple[str, str]:
    normalized = reason.upper()
    if "TIME_EXIT" in normalized:
        return "time_exit", "时间退出"
    if "ARMED_CONFIRM" in normalized or "BUY_CONFIRM" in normalized or "SELL_CONFIRM" in normalized:
        return "divergence_confirm", "背驰确认"
    if "T1_DIVERGENCE" in normalized:
        return "t1_divergence", "T1背驰"
    if "_T3" in normalized or "THIRD-BUY" in normalized or "THIRD-SELL" in normalized:
        return "t3", "T3三买三卖"
    if "_T2" in normalized or "SECOND-BUY" in normalized or "SECOND-SELL" in normalized:
        return "t2", "T2二买二卖"
    return "other", "其他信号"
