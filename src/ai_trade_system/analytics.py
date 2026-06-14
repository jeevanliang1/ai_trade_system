from __future__ import annotations

from dataclasses import dataclass
import math

from ai_trade_system.backtest import EquityPoint
from ai_trade_system.paper import Trade


@dataclass(frozen=True)
class DrawdownPoint:
    trading_day: object
    equity: float
    drawdown_pct: float


@dataclass(frozen=True)
class BacktestMetrics:
    final_equity: float
    total_return_pct: float
    annualized_return_pct: float
    benchmark_return_pct: float
    excess_return_pct: float
    annual_volatility_pct: float
    sharpe_ratio: float | None
    max_drawdown_pct: float
    trade_count: int
    win_rate_pct: float | None
    profit_factor: float | None
    exposure_pct: float


def drawdown_series(equity_curve: list[EquityPoint]) -> list[DrawdownPoint]:
    peak: float | None = None
    points: list[DrawdownPoint] = []
    for point in equity_curve:
        peak = point.equity if peak is None else max(peak, point.equity)
        drawdown_pct = 0.0 if not peak else (point.equity / peak - 1) * 100
        points.append(DrawdownPoint(point.trading_day, point.equity, drawdown_pct))
    return points


def calculate_backtest_metrics(
    equity_curve: list[EquityPoint],
    trades: list[Trade],
    initial_cash: float,
) -> BacktestMetrics:
    if not equity_curve:
        raise ValueError("equity_curve cannot be empty")
    if initial_cash <= 0:
        raise ValueError("initial_cash must be positive")

    final_equity = equity_curve[-1].equity
    total_return_pct = _round_pct((final_equity / initial_cash - 1) * 100)
    trading_days = max(1, len(equity_curve))
    annualized_return_pct = _round_pct(((final_equity / initial_cash) ** (252 / trading_days) - 1) * 100)
    benchmark_return_pct = _benchmark_return_pct(equity_curve)
    excess_return_pct = _round_pct(total_return_pct - benchmark_return_pct)
    annual_volatility_pct = _annual_volatility_pct(equity_curve)
    sharpe_ratio = None if annual_volatility_pct == 0 else round(annualized_return_pct / annual_volatility_pct, 4)
    max_drawdown_pct = _round_pct(min((point.drawdown_pct for point in drawdown_series(equity_curve)), default=0.0))
    exposure_pct = _round_pct(_average_exposure_pct(equity_curve))
    win_rate_pct, profit_factor = _trade_outcome_stats(trades)

    return BacktestMetrics(
        final_equity=final_equity,
        total_return_pct=total_return_pct,
        annualized_return_pct=annualized_return_pct,
        benchmark_return_pct=benchmark_return_pct,
        excess_return_pct=excess_return_pct,
        annual_volatility_pct=annual_volatility_pct,
        sharpe_ratio=sharpe_ratio,
        max_drawdown_pct=max_drawdown_pct,
        trade_count=len(trades),
        win_rate_pct=win_rate_pct,
        profit_factor=profit_factor,
        exposure_pct=exposure_pct,
    )


def _benchmark_return_pct(equity_curve: list[EquityPoint]) -> float:
    first_close = equity_curve[0].close_price
    last_close = equity_curve[-1].close_price
    if first_close <= 0:
        return 0.0
    return _round_pct((last_close / first_close - 1) * 100)


def _annual_volatility_pct(equity_curve: list[EquityPoint]) -> float:
    returns = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous.equity <= 0:
            continue
        returns.append(current.equity / previous.equity - 1)
    if not returns:
        return 0.0
    average = sum(returns) / len(returns)
    variance = sum((value - average) ** 2 for value in returns) / len(returns)
    return _round_pct(math.sqrt(variance) * math.sqrt(252) * 100)


def _average_exposure_pct(equity_curve: list[EquityPoint]) -> float:
    exposures = []
    for point in equity_curve:
        if point.equity <= 0:
            exposures.append(0.0)
        else:
            exposures.append(max(0.0, min(100.0, (point.equity - point.cash) / point.equity * 100)))
    return sum(exposures) / len(exposures)


def _trade_outcome_stats(trades: list[Trade]) -> tuple[float | None, float | None]:
    open_lots: list[Trade] = []
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0

    for trade in trades:
        if trade.side == "buy":
            open_lots.append(trade)
            continue
        if trade.side != "sell" or not open_lots:
            continue
        buy = open_lots.pop(0)
        pnl = (trade.price - buy.price) * min(trade.volume, buy.volume) - trade.commission - buy.commission
        if pnl >= 0:
            wins += 1
            gross_profit += pnl
        else:
            losses += 1
            gross_loss += abs(pnl)

    closed = wins + losses
    if closed == 0:
        return None, None
    profit_factor = None if gross_loss == 0 else gross_profit / gross_loss
    return _round_pct(wins / closed * 100), None if profit_factor is None else round(profit_factor, 4)


def _round_pct(value: float) -> float:
    return round(value, 4)
