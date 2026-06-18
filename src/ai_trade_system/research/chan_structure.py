from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ai_trade_system.research.models import ResearchSignal


@dataclass(frozen=True)
class ChanKLine:
    index: int
    trading_day: date
    symbol: str
    exchange: str
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class ChanFractal:
    index: int
    trading_day: date
    kind: str
    price: float
    high: float
    low: float


@dataclass(frozen=True)
class ChanStroke:
    start: ChanFractal
    end: ChanFractal
    direction: str
    high: float
    low: float


@dataclass(frozen=True)
class ChanPivot:
    start_index: int
    end_index: int
    low: float
    high: float


@dataclass(frozen=True)
class ChanStructureResult:
    klines: list[ChanKLine]
    fractals: list[ChanFractal]
    strokes: list[ChanStroke]
    pivots: list[ChanPivot]
    signals: list[ResearchSignal]
    chan_score: float


def scan_chan_structure(
    frame: pd.DataFrame,
    *,
    min_stroke_bars: int = 5,
    min_rebound_pct: float = 0.03,
    lookback: int | None = None,
) -> ChanStructureResult:
    working = frame.tail(lookback).reset_index(drop=True) if lookback else frame.reset_index(drop=True)
    klines = normalize_containment(working)
    fractals = _clean_fractals(_detect_fractals(klines))
    strokes = _build_strokes(fractals, min_stroke_bars=max(1, int(min_stroke_bars)))
    pivots = _build_pivots(strokes)
    signals = _structure_signals(klines, fractals, strokes, pivots, min_rebound_pct=max(0.0, float(min_rebound_pct)))
    chan_score = round(max(-100.0, min(100.0, sum(signal.score for signal in signals[-4:]))), 2)
    return ChanStructureResult(klines, fractals, strokes, pivots, signals, chan_score)


def normalize_containment(frame: pd.DataFrame) -> list[ChanKLine]:
    klines: list[ChanKLine] = []
    for index, row in frame.reset_index(drop=True).iterrows():
        current = ChanKLine(
            index=index,
            trading_day=row["trading_day"],
            symbol=str(row["symbol"]),
            exchange=str(row["exchange"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
        )
        if not klines:
            klines.append(current)
            continue

        latest = klines[-1]
        if not _contains(latest, current) and not _contains(current, latest):
            klines.append(current)
            continue

        direction = _containment_context(klines)
        if direction == "up":
            merged_high = max(latest.high, current.high)
            merged_low = max(latest.low, current.low)
        elif direction == "down":
            merged_high = min(latest.high, current.high)
            merged_low = min(latest.low, current.low)
        else:
            merged_high = max(latest.high, current.high)
            merged_low = min(latest.low, current.low)
        klines[-1] = ChanKLine(
            index=current.index,
            trading_day=current.trading_day,
            symbol=current.symbol,
            exchange=current.exchange,
            high=merged_high,
            low=merged_low,
            close=current.close,
        )
    return klines


def _detect_fractals(klines: list[ChanKLine]) -> list[ChanFractal]:
    fractals: list[ChanFractal] = []
    for index in range(1, len(klines) - 1):
        previous, current, following = klines[index - 1], klines[index], klines[index + 1]
        if current.high > previous.high and current.high > following.high and current.low > previous.low and current.low > following.low:
            fractals.append(ChanFractal(current.index, current.trading_day, "top", current.high, current.high, current.low))
        if current.low < previous.low and current.low < following.low and current.high < previous.high and current.high < following.high:
            fractals.append(ChanFractal(current.index, current.trading_day, "bottom", current.low, current.high, current.low))
    return fractals


def _clean_fractals(fractals: list[ChanFractal]) -> list[ChanFractal]:
    cleaned: list[ChanFractal] = []
    for fractal in fractals:
        if not cleaned or cleaned[-1].kind != fractal.kind:
            cleaned.append(fractal)
            continue
        latest = cleaned[-1]
        if fractal.kind == "top" and fractal.price > latest.price:
            cleaned[-1] = fractal
        elif fractal.kind == "bottom" and fractal.price < latest.price:
            cleaned[-1] = fractal
    return cleaned


def _build_strokes(fractals: list[ChanFractal], *, min_stroke_bars: int) -> list[ChanStroke]:
    if not fractals:
        return []
    strokes: list[ChanStroke] = []
    start = fractals[0]
    for current in fractals[1:]:
        if current.kind == start.kind:
            start = current
            continue
        if current.index - start.index < min_stroke_bars:
            continue
        direction = "up" if start.kind == "bottom" and current.kind == "top" else "down"
        strokes.append(
            ChanStroke(
                start=start,
                end=current,
                direction=direction,
                high=max(start.high, current.high),
                low=min(start.low, current.low),
            )
        )
        start = current
    return strokes


def _build_pivots(strokes: list[ChanStroke]) -> list[ChanPivot]:
    pivots: list[ChanPivot] = []
    for first, second, third in zip(strokes, strokes[1:], strokes[2:]):
        pivot_low = max(first.low, second.low, third.low)
        pivot_high = min(first.high, second.high, third.high)
        if pivot_low <= pivot_high:
            pivots.append(ChanPivot(first.start.index, third.end.index, round(pivot_low, 4), round(pivot_high, 4)))
    return pivots


def _structure_signals(
    klines: list[ChanKLine],
    fractals: list[ChanFractal],
    strokes: list[ChanStroke],
    pivots: list[ChanPivot],
    *,
    min_rebound_pct: float,
) -> list[ResearchSignal]:
    if not klines:
        return []
    latest = klines[-1]
    symbol = latest.symbol
    exchange = latest.exchange
    signals: list[ResearchSignal] = []

    third_buy = _third_buy_signal(strokes, pivots, latest, symbol, exchange)
    if third_buy is not None:
        signals.append(third_buy)
    third_sell = _third_sell_signal(strokes, pivots, latest, symbol, exchange)
    if third_sell is not None:
        signals.append(third_sell)

    second_buy = _second_buy_signal(fractals, latest, symbol, exchange, min_rebound_pct)
    if second_buy is not None:
        signals.append(second_buy)
    second_sell = _second_sell_signal(fractals, latest, symbol, exchange, min_rebound_pct)
    if second_sell is not None:
        signals.append(second_sell)

    return sorted(signals, key=lambda signal: (signal.trading_day, -abs(signal.score), signal.kind))


def _third_buy_signal(strokes: list[ChanStroke], pivots: list[ChanPivot], latest: ChanKLine, symbol: str, exchange: str) -> ResearchSignal | None:
    if not pivots or len(strokes) < 4:
        return None
    pivot = pivots[-1]
    prior, pullback = strokes[-2], strokes[-1]
    if prior.direction != "up" or pullback.direction != "down":
        return None
    if prior.high <= pivot.high or pullback.low <= pivot.high:
        return None
    return ResearchSignal(
        trading_day=latest.trading_day,
        symbol=symbol,
        exchange=exchange,
        kind="CHAN_STRUCT_BUY_T3",
        action="buy",
        price=round(latest.close, 3),
        strength=0.78,
        score=44.0,
        title="缠论三买",
        reason="向上离开中枢后的回抽未跌回中枢上沿",
        tags=("chan", "structure", "third-buy"),
    )


def _third_sell_signal(strokes: list[ChanStroke], pivots: list[ChanPivot], latest: ChanKLine, symbol: str, exchange: str) -> ResearchSignal | None:
    if not pivots or len(strokes) < 4:
        return None
    pivot = pivots[-1]
    prior, pullback = strokes[-2], strokes[-1]
    if prior.direction != "down" or pullback.direction != "up":
        return None
    if prior.low >= pivot.low or pullback.high >= pivot.low:
        return None
    return ResearchSignal(
        trading_day=latest.trading_day,
        symbol=symbol,
        exchange=exchange,
        kind="CHAN_STRUCT_SELL_T3",
        action="sell",
        price=round(latest.close, 3),
        strength=0.78,
        score=-44.0,
        title="缠论三卖",
        reason="向下离开中枢后的回抽未重新站回中枢下沿",
        tags=("chan", "structure", "third-sell"),
    )


def _second_buy_signal(
    fractals: list[ChanFractal],
    latest: ChanKLine,
    symbol: str,
    exchange: str,
    min_rebound_pct: float,
) -> ResearchSignal | None:
    lows = [fractal for fractal in fractals if fractal.kind == "bottom"]
    if len(lows) < 2:
        return None
    previous, current = lows[-2], lows[-1]
    if current.price <= previous.price or latest.close < current.price * (1 + min_rebound_pct):
        return None
    return ResearchSignal(
        trading_day=latest.trading_day,
        symbol=symbol,
        exchange=exchange,
        kind="CHAN_STRUCT_BUY_T2",
        action="buy",
        price=round(latest.close, 3),
        strength=0.62,
        score=28.0,
        title="缠论二买",
        reason="回落低点抬高后重新向上修复",
        tags=("chan", "structure", "second-buy"),
    )


def _second_sell_signal(
    fractals: list[ChanFractal],
    latest: ChanKLine,
    symbol: str,
    exchange: str,
    min_rebound_pct: float,
) -> ResearchSignal | None:
    highs = [fractal for fractal in fractals if fractal.kind == "top"]
    if len(highs) < 2:
        return None
    previous, current = highs[-2], highs[-1]
    if current.price >= previous.price or latest.close > current.price * (1 - min_rebound_pct):
        return None
    return ResearchSignal(
        trading_day=latest.trading_day,
        symbol=symbol,
        exchange=exchange,
        kind="CHAN_STRUCT_SELL_T2",
        action="sell",
        price=round(latest.close, 3),
        strength=0.62,
        score=-28.0,
        title="缠论二卖",
        reason="反弹高点降低后重新向下破位",
        tags=("chan", "structure", "second-sell"),
    )


def _contains(left: ChanKLine, right: ChanKLine) -> bool:
    return left.high >= right.high and left.low <= right.low


def _containment_context(klines: list[ChanKLine]) -> str:
    if len(klines) < 2:
        return "neutral"
    previous, latest = klines[-2], klines[-1]
    if latest.high >= previous.high and latest.low >= previous.low:
        return "up"
    if latest.high <= previous.high and latest.low <= previous.low:
        return "down"
    return "neutral"
