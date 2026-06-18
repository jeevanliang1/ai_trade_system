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
class ChanSegment:
    start: ChanFractal
    end: ChanFractal
    direction: str
    high: float
    low: float
    stroke_count: int
    energy: float
    broken_by_next: bool = False
    start_stroke_index: int = 0
    end_stroke_index: int = 0
    break_stroke_index: int | None = None


@dataclass(frozen=True)
class ChanRecursivePivot:
    level: str
    start_index: int
    end_index: int
    start_day: date
    end_day: date
    low: float
    high: float
    direction: str
    component_count: int


@dataclass(frozen=True)
class ChanDivergence:
    kind: str
    action: str
    segment: ChanSegment
    reference_segment: ChanSegment
    reference_energy: float
    current_energy: float
    price_extreme: float


@dataclass(frozen=True)
class ChanStructureResult:
    klines: list[ChanKLine]
    fractals: list[ChanFractal]
    strokes: list[ChanStroke]
    pivots: list[ChanPivot]
    segments: list[ChanSegment]
    recursive_pivots: list[ChanRecursivePivot]
    divergences: list[ChanDivergence]
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
    segments = _build_segments(strokes)
    recursive_pivots = _build_recursive_pivots(strokes, segments)
    divergences = _detect_divergences(segments)
    signals = _structure_signals(
        klines,
        fractals,
        strokes,
        pivots,
        divergences,
        min_rebound_pct=max(0.0, float(min_rebound_pct)),
    )
    chan_score = round(max(-100.0, min(100.0, sum(signal.score for signal in signals[-4:]))), 2)
    return ChanStructureResult(
        klines=klines,
        fractals=fractals,
        strokes=strokes,
        pivots=pivots,
        segments=segments,
        recursive_pivots=recursive_pivots,
        divergences=divergences,
        signals=signals,
        chan_score=chan_score,
    )


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


def _build_segments(strokes: list[ChanStroke]) -> list[ChanSegment]:
    segments: list[ChanSegment] = []
    cursor = 0
    while cursor + 2 < len(strokes):
        segment = _candidate_segment(strokes, cursor)
        if segment is None:
            cursor += 1
            continue

        start_stroke_index = cursor
        end_stroke_index = cursor + 2
        break_stroke_index: int | None = None
        scan_index = end_stroke_index + 1
        while scan_index < len(strokes):
            stroke = strokes[scan_index]
            if stroke.direction == segment.direction:
                if _stroke_extends_segment(stroke, segment):
                    end_stroke_index = scan_index
                    segment = _segment_from_strokes(strokes[start_stroke_index : end_stroke_index + 1], start_stroke_index, end_stroke_index)
            elif _stroke_breaks_segment(stroke, segment):
                break_stroke_index = scan_index
                segment = _segment_from_strokes(
                    strokes[start_stroke_index : end_stroke_index + 1],
                    start_stroke_index,
                    end_stroke_index,
                    broken_by_next=True,
                    break_stroke_index=break_stroke_index,
                )
                break
            scan_index += 1

        segments.append(segment)
        if break_stroke_index is None:
            cursor = end_stroke_index + 1
        else:
            cursor = break_stroke_index
    return segments


def _candidate_segment(strokes: list[ChanStroke], start_index: int) -> ChanSegment | None:
    window = strokes[start_index : start_index + 3]
    if len(window) < 3:
        return None
    first, _, third = window
    if first.direction != third.direction:
        return None
    return _segment_from_strokes(window, start_index, start_index + 2)


def _segment_from_strokes(
    strokes: list[ChanStroke],
    start_stroke_index: int,
    end_stroke_index: int,
    *,
    broken_by_next: bool = False,
    break_stroke_index: int | None = None,
) -> ChanSegment:
    start = strokes[0].start
    end = strokes[-1].end
    index_span = max(1, end.index - start.index)
    return ChanSegment(
        start=start,
        end=end,
        direction=strokes[0].direction,
        high=max(stroke.high for stroke in strokes),
        low=min(stroke.low for stroke in strokes),
        stroke_count=len(strokes),
        energy=round(abs(end.price - start.price) / index_span, 6),
        broken_by_next=broken_by_next,
        start_stroke_index=start_stroke_index,
        end_stroke_index=end_stroke_index,
        break_stroke_index=break_stroke_index,
    )


def _stroke_extends_segment(stroke: ChanStroke, segment: ChanSegment) -> bool:
    if segment.direction == "up":
        return stroke.end.price > segment.end.price or stroke.high > segment.high
    return stroke.end.price < segment.end.price or stroke.low < segment.low


def _stroke_breaks_segment(stroke: ChanStroke, segment: ChanSegment) -> bool:
    if segment.direction == "up":
        return stroke.low < segment.low
    return stroke.high > segment.high


def _build_recursive_pivots(strokes: list[ChanStroke], segments: list[ChanSegment]) -> list[ChanRecursivePivot]:
    pivots: list[ChanRecursivePivot] = []
    for first, second, third in zip(strokes, strokes[1:], strokes[2:]):
        pivot = _recursive_pivot_from_components("stroke", first, second, third)
        if pivot is not None:
            pivots.append(pivot)
    for first, second, third in zip(segments, segments[1:], segments[2:]):
        pivot = _recursive_pivot_from_components("segment", first, second, third)
        if pivot is not None:
            pivots.append(pivot)
    return pivots


def _recursive_pivot_from_components(level: str, first: ChanStroke | ChanSegment, second: ChanStroke | ChanSegment, third: ChanStroke | ChanSegment) -> ChanRecursivePivot | None:
    pivot_low = max(first.low, second.low, third.low)
    pivot_high = min(first.high, second.high, third.high)
    if pivot_low > pivot_high:
        return None
    return ChanRecursivePivot(
        level=level,
        start_index=first.start.index,
        end_index=third.end.index,
        start_day=first.start.trading_day,
        end_day=third.end.trading_day,
        low=round(pivot_low, 4),
        high=round(pivot_high, 4),
        direction=first.direction,
        component_count=3,
    )


def _detect_divergences(segments: list[ChanSegment]) -> list[ChanDivergence]:
    divergences: list[ChanDivergence] = []
    latest_by_direction: dict[str, ChanSegment] = {}
    for segment in segments:
        reference = latest_by_direction.get(segment.direction)
        if reference is not None and segment.energy < reference.energy:
            if segment.direction == "down" and segment.low < reference.low:
                divergences.append(
                    ChanDivergence(
                        kind="bottom",
                        action="buy",
                        segment=segment,
                        reference_segment=reference,
                        reference_energy=reference.energy,
                        current_energy=segment.energy,
                        price_extreme=segment.low,
                    )
                )
            elif segment.direction == "up" and segment.high > reference.high:
                divergences.append(
                    ChanDivergence(
                        kind="top",
                        action="sell",
                        segment=segment,
                        reference_segment=reference,
                        reference_energy=reference.energy,
                        current_energy=segment.energy,
                        price_extreme=segment.high,
                    )
                )
        latest_by_direction[segment.direction] = segment
    return divergences


def _structure_signals(
    klines: list[ChanKLine],
    fractals: list[ChanFractal],
    strokes: list[ChanStroke],
    pivots: list[ChanPivot],
    divergences: list[ChanDivergence],
    *,
    min_rebound_pct: float,
) -> list[ResearchSignal]:
    if not klines:
        return []
    latest = klines[-1]
    symbol = latest.symbol
    exchange = latest.exchange
    signals: list[ResearchSignal] = []

    signals.extend(_divergence_signals(divergences, latest, symbol, exchange, min_rebound_pct))

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


def _divergence_signals(
    divergences: list[ChanDivergence],
    latest: ChanKLine,
    symbol: str,
    exchange: str,
    min_rebound_pct: float,
) -> list[ResearchSignal]:
    signals: list[ResearchSignal] = []
    latest_by_action: dict[str, ChanDivergence] = {}
    for divergence in divergences:
        latest_by_action[divergence.action] = divergence

    buy_divergence = latest_by_action.get("buy")
    if buy_divergence is not None:
        signals.append(
            ResearchSignal(
                trading_day=latest.trading_day,
                symbol=symbol,
                exchange=exchange,
                kind="CHAN_STRUCT_BUY_T1_DIVERGENCE",
                action="buy",
                price=round(latest.close, 3),
                strength=0.68,
                score=36.0,
                title="缠论底背驰",
                reason=_divergence_reason(buy_divergence),
                tags=("chan", "structure", "divergence", "first-buy"),
            )
        )
        if latest.close >= buy_divergence.segment.end.price * (1 + min_rebound_pct):
            signals.append(
                ResearchSignal(
                    trading_day=latest.trading_day,
                    symbol=symbol,
                    exchange=exchange,
                    kind="CHAN_STRUCT_BUY_CONFIRM",
                    action="buy",
                    price=round(latest.close, 3),
                    strength=0.82,
                    score=52.0,
                    title="缠论底背驰确认",
                    reason=f"{_divergence_reason(buy_divergence)}，并向上修复超过 {min_rebound_pct:.2%}",
                    tags=("chan", "structure", "divergence", "confirmation", "first-buy"),
                )
            )

    sell_divergence = latest_by_action.get("sell")
    if sell_divergence is not None:
        signals.append(
            ResearchSignal(
                trading_day=latest.trading_day,
                symbol=symbol,
                exchange=exchange,
                kind="CHAN_STRUCT_SELL_T1_DIVERGENCE",
                action="sell",
                price=round(latest.close, 3),
                strength=0.68,
                score=-36.0,
                title="缠论顶背驰",
                reason=_divergence_reason(sell_divergence),
                tags=("chan", "structure", "divergence", "first-sell"),
            )
        )
        if latest.close <= sell_divergence.segment.end.price * (1 - min_rebound_pct):
            signals.append(
                ResearchSignal(
                    trading_day=latest.trading_day,
                    symbol=symbol,
                    exchange=exchange,
                    kind="CHAN_STRUCT_SELL_CONFIRM",
                    action="sell",
                    price=round(latest.close, 3),
                    strength=0.82,
                    score=-52.0,
                    title="缠论顶背驰确认",
                    reason=f"{_divergence_reason(sell_divergence)}，并向下破位超过 {min_rebound_pct:.2%}",
                    tags=("chan", "structure", "divergence", "confirmation", "first-sell"),
                )
            )
    return signals


def _divergence_reason(divergence: ChanDivergence) -> str:
    if divergence.action == "buy":
        return (
            "下跌线段创新低但单位推进力度减弱："
            f"{divergence.current_energy:.4f} < {divergence.reference_energy:.4f}"
        )
    return (
        "上涨线段创新高但单位推进力度减弱："
        f"{divergence.current_energy:.4f} < {divergence.reference_energy:.4f}"
    )


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
