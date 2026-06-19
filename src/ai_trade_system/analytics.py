from __future__ import annotations

from dataclasses import dataclass
import math

from ai_trade_system.backtest import EquityPoint, TradeAttribution, classify_signal_family
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


@dataclass(frozen=True)
class SignalAttributionRow:
    family: str
    label: str
    trade_count: int
    buy_count: int
    sell_count: int
    entry_closed_trades: int
    entry_realized_pnl: float
    entry_return_pct: float
    entry_win_rate_pct: float | None
    entry_profit_factor: float | None
    entry_realized_drawdown_pct: float
    exit_closed_trades: int
    exit_realized_pnl: float
    exit_return_pct: float
    exit_win_rate_pct: float | None
    exit_profit_factor: float | None
    exit_realized_drawdown_pct: float


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


def calculate_signal_attribution(
    trade_attributions: list[TradeAttribution],
    initial_cash: float,
) -> list[SignalAttributionRow]:
    if initial_cash <= 0:
        raise ValueError("initial_cash must be positive")

    buckets: dict[str, dict[str, object]] = {}
    open_lots: list[dict[str, object]] = []

    for trade in trade_attributions:
        bucket = _signal_bucket(buckets, trade.signal_family, trade.signal_label)
        bucket["trade_count"] = int(bucket["trade_count"]) + 1
        if trade.side == "buy":
            bucket["buy_count"] = int(bucket["buy_count"]) + 1
            if trade.volume > 0:
                open_lots.append(
                    {
                        "family": trade.signal_family,
                        "label": trade.signal_label,
                        "price": trade.price,
                        "remaining_volume": trade.volume,
                        "commission_per_share": trade.commission / trade.volume,
                    }
                )
            continue

        if trade.side != "sell":
            continue
        bucket["sell_count"] = int(bucket["sell_count"]) + 1
        remaining = trade.volume
        exit_commission_per_share = trade.commission / trade.volume if trade.volume > 0 else 0.0
        while remaining > 0 and open_lots:
            lot = open_lots[0]
            lot_volume = int(lot["remaining_volume"])
            matched = min(remaining, lot_volume)
            entry_commission = float(lot["commission_per_share"]) * matched
            exit_commission = exit_commission_per_share * matched
            pnl = (trade.price - float(lot["price"])) * matched - entry_commission - exit_commission

            entry_bucket = _signal_bucket(buckets, str(lot["family"]), str(lot["label"]))
            entry_bucket["entry_pnls"].append(pnl)  # type: ignore[index, union-attr]
            bucket["exit_pnls"].append(pnl)  # type: ignore[index, union-attr]

            remaining -= matched
            lot["remaining_volume"] = lot_volume - matched
            if int(lot["remaining_volume"]) == 0:
                open_lots.pop(0)

    rows = []
    for family, bucket in buckets.items():
        entry_stats = _realized_pnl_stats(bucket["entry_pnls"], initial_cash)  # type: ignore[arg-type]
        exit_stats = _realized_pnl_stats(bucket["exit_pnls"], initial_cash)  # type: ignore[arg-type]
        rows.append(
            SignalAttributionRow(
                family=family,
                label=str(bucket["label"]),
                trade_count=int(bucket["trade_count"]),
                buy_count=int(bucket["buy_count"]),
                sell_count=int(bucket["sell_count"]),
                entry_closed_trades=entry_stats["closed_trades"],
                entry_realized_pnl=entry_stats["realized_pnl"],
                entry_return_pct=entry_stats["return_pct"],
                entry_win_rate_pct=entry_stats["win_rate_pct"],
                entry_profit_factor=entry_stats["profit_factor"],
                entry_realized_drawdown_pct=entry_stats["realized_drawdown_pct"],
                exit_closed_trades=exit_stats["closed_trades"],
                exit_realized_pnl=exit_stats["realized_pnl"],
                exit_return_pct=exit_stats["return_pct"],
                exit_win_rate_pct=exit_stats["win_rate_pct"],
                exit_profit_factor=exit_stats["profit_factor"],
                exit_realized_drawdown_pct=exit_stats["realized_drawdown_pct"],
            )
        )
    return sorted(rows, key=lambda row: (-row.trade_count, row.family))


def _signal_bucket(buckets: dict[str, dict[str, object]], family: str, label: str) -> dict[str, object]:
    if family not in buckets:
        buckets[family] = {
            "label": label,
            "trade_count": 0,
            "buy_count": 0,
            "sell_count": 0,
            "entry_pnls": [],
            "exit_pnls": [],
        }
    return buckets[family]


def _realized_pnl_stats(pnls: list[float], initial_cash: float) -> dict[str, float | int | None]:
    if not pnls:
        return {
            "closed_trades": 0,
            "realized_pnl": 0.0,
            "return_pct": 0.0,
            "win_rate_pct": None,
            "profit_factor": None,
            "realized_drawdown_pct": 0.0,
        }
    wins = [pnl for pnl in pnls if pnl >= 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = None if gross_loss == 0 else round(gross_profit / gross_loss, 4)
    return {
        "closed_trades": len(pnls),
        "realized_pnl": round(sum(pnls), 2),
        "return_pct": _round_pct(sum(pnls) / initial_cash * 100),
        "win_rate_pct": _round_pct(len(wins) / len(pnls) * 100),
        "profit_factor": profit_factor,
        "realized_drawdown_pct": _realized_drawdown_pct(pnls, initial_cash),
    }


def _realized_drawdown_pct(pnls: list[float], initial_cash: float) -> float:
    peak = 0.0
    cumulative = 0.0
    worst = 0.0
    for pnl in pnls:
        cumulative += pnl
        peak = max(peak, cumulative)
        worst = min(worst, (cumulative - peak) / initial_cash * 100)
    return _round_pct(worst)


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
