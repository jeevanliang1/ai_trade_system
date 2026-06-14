from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_trade_system.research.models import ChanPatternResult, ResearchSignal


@dataclass(frozen=True)
class SwingPoint:
    index: int
    kind: str
    price: float


def scan_chan_patterns(frame: pd.DataFrame, *, lookback: int = 120, order: int = 2) -> ChanPatternResult:
    if frame.empty or len(frame) < (order * 2 + 6):
        return ChanPatternResult([], 0.0)

    working = frame.tail(lookback).reset_index(drop=True)
    swings = _swing_points(working, order=order)
    symbol = str(working.iloc[-1]["symbol"])
    exchange = str(working.iloc[-1]["exchange"])
    signals: list[ResearchSignal] = []

    buy = _second_buy(working, swings, symbol, exchange)
    if buy is not None:
        signals.append(buy)
    sell = _second_sell(working, swings, symbol, exchange)
    if sell is not None:
        signals.append(sell)

    chan_score = round(max(-50.0, min(50.0, sum(signal.score for signal in signals[-4:]))), 2)
    return ChanPatternResult(signals, chan_score)


def _swing_points(frame: pd.DataFrame, *, order: int) -> list[SwingPoint]:
    swings: list[SwingPoint] = []
    for index in range(order, len(frame) - order):
        window = frame.iloc[index - order : index + order + 1]
        row = frame.iloc[index]
        high = float(row["high"])
        low = float(row["low"])
        if high >= float(window["high"].max()):
            swings.append(SwingPoint(index, "high", high))
        if low <= float(window["low"].min()):
            swings.append(SwingPoint(index, "low", low))
    return swings


def _second_buy(frame: pd.DataFrame, swings: list[SwingPoint], symbol: str, exchange: str) -> ResearchSignal | None:
    lows = [point for point in swings if point.kind == "low"]
    if len(lows) < 2:
        return None
    prior, latest = lows[-2], lows[-1]
    last_close = float(frame.iloc[-1]["close"])
    if latest.price <= prior.price or last_close <= latest.price * 1.05:
        return None
    row = frame.iloc[-1]
    return ResearchSignal(
        trading_day=row["trading_day"],
        symbol=symbol,
        exchange=exchange,
        kind="CHAN_BUY_T2",
        action="buy",
        price=round(last_close, 3),
        strength=0.62,
        score=32.0,
        title="缠论二买",
        reason="回落低点抬高后向上修复，符合轻量二买观察条件",
        tags=("chan", "second-buy"),
    )


def _second_sell(frame: pd.DataFrame, swings: list[SwingPoint], symbol: str, exchange: str) -> ResearchSignal | None:
    highs = [point for point in swings if point.kind == "high"]
    if len(highs) < 2:
        return None
    prior, latest = highs[-2], highs[-1]
    last_close = float(frame.iloc[-1]["close"])
    if latest.price >= prior.price or last_close >= latest.price * 0.95:
        return None
    row = frame.iloc[-1]
    return ResearchSignal(
        trading_day=row["trading_day"],
        symbol=symbol,
        exchange=exchange,
        kind="CHAN_SELL_T2",
        action="sell",
        price=round(last_close, 3),
        strength=0.62,
        score=-32.0,
        title="缠论二卖",
        reason="反弹高点降低后向下破位，符合轻量二卖观察条件",
        tags=("chan", "second-sell"),
    )
