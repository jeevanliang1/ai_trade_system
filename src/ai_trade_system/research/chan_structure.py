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
    base_score: float
    macd_strength: float
    volume_strength: float
    confirmation_score: float
    macd_reference: float
    macd_current: float
    volume_reference: float
    volume_current: float
    pivot_level: str | None = None
    pivot_start_index: int | None = None
    pivot_end_index: int | None = None
    pivot_low: float | None = None
    pivot_high: float | None = None


@dataclass(frozen=True)
class ChanIndicatorContext:
    macd_histogram: dict[int, float]
    volume: dict[int, float]


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
    indicator_context = _build_indicator_context(working)
    klines = normalize_containment(working)
    fractals = _clean_fractals(_detect_fractals(klines))
    strokes = _build_strokes(fractals, min_stroke_bars=max(1, int(min_stroke_bars)))
    pivots = _build_pivots(strokes)
    segments = _build_segments(strokes)
    recursive_pivots = _build_recursive_pivots(strokes, segments)
    divergences = _detect_divergences(segments, indicator_context, recursive_pivots)
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


def _build_indicator_context(frame: pd.DataFrame) -> ChanIndicatorContext:
    if frame.empty:
        return ChanIndicatorContext(macd_histogram={}, volume={})
    closes = frame["close"].astype(float)
    ema_fast = closes.ewm(span=12, adjust=False).mean()
    ema_slow = closes.ewm(span=26, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=9, adjust=False).mean()
    histogram = (dif - dea) * 2
    volumes = frame["volume"].astype(float)
    return ChanIndicatorContext(
        macd_histogram={int(index): round(float(value), 6) for index, value in histogram.items()},
        volume={int(index): round(float(value), 4) for index, value in volumes.items()},
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
    return [
        *_build_recursive_pivots_for_level("stroke", strokes),
        *_build_recursive_pivots_for_level("segment", segments),
    ]


def _build_recursive_pivots_for_level(level: str, components: list[ChanStroke] | list[ChanSegment]) -> list[ChanRecursivePivot]:
    pivots: list[ChanRecursivePivot] = []
    cursor = 0
    while cursor + 2 < len(components):
        window = components[cursor : cursor + 3]
        pivot_low = max(component.low for component in window)
        pivot_high = min(component.high for component in window)
        if pivot_low > pivot_high:
            cursor += 1
            continue

        end_index = cursor + 2
        scan_index = end_index + 1
        while scan_index < len(components):
            component = components[scan_index]
            next_low = max(pivot_low, component.low)
            next_high = min(pivot_high, component.high)
            if next_low > next_high:
                break
            pivot_low = next_low
            pivot_high = next_high
            end_index = scan_index
            scan_index += 1

        pivots.append(_recursive_pivot_from_components(level, components[cursor : end_index + 1], pivot_low, pivot_high))
        cursor = end_index + 1
    return pivots


def _recursive_pivot_from_components(
    level: str,
    components: list[ChanStroke] | list[ChanSegment],
    pivot_low: float,
    pivot_high: float,
) -> ChanRecursivePivot:
    first = components[0]
    latest = components[-1]
    return ChanRecursivePivot(
        level=level,
        start_index=first.start.index,
        end_index=latest.end.index,
        start_day=first.start.trading_day,
        end_day=latest.end.trading_day,
        low=round(pivot_low, 4),
        high=round(pivot_high, 4),
        direction=first.direction,
        component_count=len(components),
    )


def _detect_divergences(
    segments: list[ChanSegment],
    indicators: ChanIndicatorContext | None = None,
    recursive_pivots: list[ChanRecursivePivot] | None = None,
) -> list[ChanDivergence]:
    divergences: list[ChanDivergence] = []
    latest_by_direction: dict[str, ChanSegment] = {}
    for segment in segments:
        reference = latest_by_direction.get(segment.direction)
        if reference is not None and segment.energy < reference.energy:
            if segment.direction == "down" and segment.low < reference.low:
                evidence = _divergence_evidence(reference, segment, indicators)
                pivot_context = _divergence_pivot_context(segment, recursive_pivots or [])
                divergences.append(
                    ChanDivergence(
                        kind="bottom",
                        action="buy",
                        segment=segment,
                        reference_segment=reference,
                        reference_energy=reference.energy,
                        current_energy=segment.energy,
                        price_extreme=segment.low,
                        **evidence,
                        **pivot_context,
                    )
                )
            elif segment.direction == "up" and segment.high > reference.high:
                evidence = _divergence_evidence(reference, segment, indicators)
                pivot_context = _divergence_pivot_context(segment, recursive_pivots or [])
                divergences.append(
                    ChanDivergence(
                        kind="top",
                        action="sell",
                        segment=segment,
                        reference_segment=reference,
                        reference_energy=reference.energy,
                        current_energy=segment.energy,
                        price_extreme=segment.high,
                        **evidence,
                        **pivot_context,
                    )
                )
        latest_by_direction[segment.direction] = segment
    return divergences


def _divergence_pivot_context(segment: ChanSegment, pivots: list[ChanRecursivePivot]) -> dict[str, str | int | float | None]:
    pivot = _nearest_recursive_pivot(segment, pivots)
    if pivot is None:
        return {
            "pivot_level": None,
            "pivot_start_index": None,
            "pivot_end_index": None,
            "pivot_low": None,
            "pivot_high": None,
        }
    return {
        "pivot_level": pivot.level,
        "pivot_start_index": pivot.start_index,
        "pivot_end_index": pivot.end_index,
        "pivot_low": pivot.low,
        "pivot_high": pivot.high,
    }


def _nearest_recursive_pivot(segment: ChanSegment, pivots: list[ChanRecursivePivot]) -> ChanRecursivePivot | None:
    candidates = [pivot for pivot in pivots if _pivot_overlaps_segment(pivot, segment)]
    if not candidates:
        return None

    def sort_key(pivot: ChanRecursivePivot) -> tuple[int, int, int, int]:
        level_rank = 0 if pivot.level == "segment" else 1
        contains_rank = 0 if pivot.start_index <= segment.start.index and pivot.end_index >= segment.end.index else 1
        edge_distance = abs(pivot.start_index - segment.start.index) + abs(pivot.end_index - segment.end.index)
        return (level_rank, contains_rank, edge_distance, -pivot.component_count)

    return sorted(candidates, key=sort_key)[0]


def _pivot_overlaps_segment(pivot: ChanRecursivePivot, segment: ChanSegment) -> bool:
    return pivot.start_index <= segment.end.index and pivot.end_index >= segment.start.index


def _divergence_evidence(
    reference: ChanSegment,
    current: ChanSegment,
    indicators: ChanIndicatorContext | None,
) -> dict[str, float]:
    macd_reference = _segment_macd_pressure(reference, indicators)
    macd_current = _segment_macd_pressure(current, indicators)
    volume_reference = _segment_average_volume(reference, indicators)
    volume_current = _segment_average_volume(current, indicators)
    energy_strength = _fade_strength(reference.energy, current.energy, scale=50.0, cap=28.0)
    macd_strength = _fade_strength(macd_reference, macd_current, scale=30.0, cap=18.0)
    volume_strength = _fade_strength(volume_reference, volume_current, scale=20.0, cap=12.0)
    base_score = round(min(82.0, 30.0 + energy_strength + macd_strength + volume_strength), 2)
    break_component = 6.0 if current.broken_by_next or current.break_stroke_index is not None else 0.0
    confirmation_score = round(min(92.0, base_score + 12.0 + break_component), 2)
    return {
        "base_score": base_score,
        "macd_strength": macd_strength,
        "volume_strength": volume_strength,
        "confirmation_score": confirmation_score,
        "macd_reference": round(macd_reference, 6),
        "macd_current": round(macd_current, 6),
        "volume_reference": round(volume_reference, 4),
        "volume_current": round(volume_current, 4),
    }


def _fade_strength(reference: float, current: float, *, scale: float, cap: float) -> float:
    if reference <= 0:
        return 0.0
    return round(min(cap, max(0.0, (1 - current / reference) * scale)), 2)


def _segment_macd_pressure(segment: ChanSegment, indicators: ChanIndicatorContext | None) -> float:
    if indicators is None:
        return 0.0
    values = _segment_values(segment, indicators.macd_histogram)
    if not values:
        return 0.0
    if segment.direction == "up":
        directional = [max(0.0, value) for value in values]
    else:
        directional = [abs(min(0.0, value)) for value in values]
    if sum(directional) <= 0:
        directional = [abs(value) for value in values]
    price_span = max(abs(segment.end.price - segment.start.price), 1e-6)
    return (sum(directional) / len(directional)) / price_span


def _segment_average_volume(segment: ChanSegment, indicators: ChanIndicatorContext | None) -> float:
    if indicators is None:
        return 0.0
    values = _segment_values(segment, indicators.volume)
    if not values:
        return 0.0
    return sum(values) / len(values)


def _segment_values(segment: ChanSegment, series: dict[int, float]) -> list[float]:
    left = min(segment.start.index, segment.end.index)
    right = max(segment.start.index, segment.end.index)
    return [series[index] for index in range(left, right + 1) if index in series]


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
        confirmed, confirmation_reason = _divergence_confirmation(buy_divergence, latest, min_rebound_pct)
        base_score = buy_divergence.base_score
        signals.append(
            ResearchSignal(
                trading_day=latest.trading_day,
                symbol=symbol,
                exchange=exchange,
                kind="CHAN_STRUCT_BUY_T1_DIVERGENCE",
                action="buy",
                price=round(latest.close, 3),
                strength=_signal_strength(base_score),
                score=base_score,
                title="缠论底背驰",
                reason=_divergence_watch_reason(buy_divergence, confirmation_reason, confirmed),
                tags=_divergence_tags(("chan", "structure", "divergence", "first-buy"), confirmed),
            )
        )
        if confirmed:
            confirmation_score = buy_divergence.confirmation_score
            signals.append(
                ResearchSignal(
                    trading_day=latest.trading_day,
                    symbol=symbol,
                    exchange=exchange,
                    kind="CHAN_STRUCT_BUY_CONFIRM",
                    action="buy",
                    price=round(latest.close, 3),
                    strength=_signal_strength(confirmation_score),
                    score=confirmation_score,
                    title="缠论底背驰确认",
                    reason=f"{_divergence_reason(buy_divergence)}，{confirmation_reason}",
                    tags=("chan", "structure", "divergence", "confirmation", "first-buy"),
                )
            )

    sell_divergence = latest_by_action.get("sell")
    if sell_divergence is not None:
        confirmed, confirmation_reason = _divergence_confirmation(sell_divergence, latest, min_rebound_pct)
        base_score = -sell_divergence.base_score
        signals.append(
            ResearchSignal(
                trading_day=latest.trading_day,
                symbol=symbol,
                exchange=exchange,
                kind="CHAN_STRUCT_SELL_T1_DIVERGENCE",
                action="sell",
                price=round(latest.close, 3),
                strength=_signal_strength(base_score),
                score=base_score,
                title="缠论顶背驰",
                reason=_divergence_watch_reason(sell_divergence, confirmation_reason, confirmed),
                tags=_divergence_tags(("chan", "structure", "divergence", "first-sell"), confirmed),
            )
        )
        if confirmed:
            confirmation_score = -sell_divergence.confirmation_score
            signals.append(
                ResearchSignal(
                    trading_day=latest.trading_day,
                    symbol=symbol,
                    exchange=exchange,
                    kind="CHAN_STRUCT_SELL_CONFIRM",
                    action="sell",
                    price=round(latest.close, 3),
                    strength=_signal_strength(confirmation_score),
                    score=confirmation_score,
                    title="缠论顶背驰确认",
                    reason=f"{_divergence_reason(sell_divergence)}，{confirmation_reason}",
                    tags=("chan", "structure", "divergence", "confirmation", "first-sell"),
                )
            )
    return signals


def _divergence_confirmation(divergence: ChanDivergence, latest: ChanKLine, min_rebound_pct: float) -> tuple[bool, str]:
    if divergence.action == "buy":
        repair_price = divergence.segment.end.price * (1 + min_rebound_pct)
        if latest.close >= repair_price:
            return True, f"并向上修复超过 {min_rebound_pct:.2%}"
        if divergence.segment.broken_by_next:
            return True, "并出现反向笔破坏下跌线段"
        return False, f"等待向上修复超过 {min_rebound_pct:.2%} 或反向笔破坏下跌线段"

    break_price = divergence.segment.end.price * (1 - min_rebound_pct)
    if latest.close <= break_price:
        return True, f"并向下破位超过 {min_rebound_pct:.2%}"
    if divergence.segment.broken_by_next:
        return True, "并出现反向笔破坏上涨线段"
    return False, f"等待向下破位超过 {min_rebound_pct:.2%} 或反向笔破坏上涨线段"


def _divergence_watch_reason(divergence: ChanDivergence, confirmation_reason: str, confirmed: bool) -> str:
    if confirmed:
        return _divergence_reason(divergence)
    return f"{_divergence_reason(divergence)}，{confirmation_reason}"


def _divergence_tags(base_tags: tuple[str, ...], confirmed: bool) -> tuple[str, ...]:
    if confirmed:
        return base_tags
    return (*base_tags, "watch")


def _signal_strength(score: float) -> float:
    return round(min(0.95, max(0.1, abs(score) / 100.0)), 2)


def _divergence_reason(divergence: ChanDivergence) -> str:
    if divergence.action == "buy":
        return (
            "下跌线段创新低但单位推进力度减弱："
            f"{divergence.current_energy:.4f} < {divergence.reference_energy:.4f}，"
            f"MACD衰减 {divergence.macd_strength:.2f}，"
            f"成交量衰减 {divergence.volume_strength:.2f}"
        )
    return (
        "上涨线段创新高但单位推进力度减弱："
        f"{divergence.current_energy:.4f} < {divergence.reference_energy:.4f}，"
        f"MACD衰减 {divergence.macd_strength:.2f}，"
        f"成交量衰减 {divergence.volume_strength:.2f}"
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
