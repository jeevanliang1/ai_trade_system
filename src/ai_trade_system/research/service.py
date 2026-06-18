from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from ai_trade_system.market import Bar
from ai_trade_system.research.chan import scan_chan_patterns
from ai_trade_system.research.chan_structure import ChanStructureResult, scan_chan_structure
from ai_trade_system.research.dataframe import bars_to_frame
from ai_trade_system.research.enhanced_rsi import scan_enhanced_rsi
from ai_trade_system.research.models import (
    ChanDivergenceOverlay,
    ChanFractalOverlay,
    ChanPivotOverlay,
    ChanRecursivePivotOverlay,
    ChanSegmentOverlay,
    ChanStrokeOverlay,
    ChanStructureOverlay,
    ResearchSignal,
    ResearchSignalBlocker,
    ResearchSignalPreview,
    ResearchSignalScore,
)


def preview_research_signals(bars: Sequence[Bar], *, min_bars: int = 60, lookback: int = 120) -> ResearchSignalPreview:
    if not bars:
        return _empty_preview("NO_BARS", "没有可分析的行情数据")

    frame = bars_to_frame(bars)
    symbol = str(frame.iloc[-1]["symbol"])
    exchange = str(frame.iloc[-1]["exchange"])
    if len(frame) < min_bars:
        return ResearchSignalPreview(
            symbol=symbol,
            exchange=exchange,
            start=frame.iloc[0]["trading_day"],
            end=frame.iloc[-1]["trading_day"],
            bars=len(frame),
            signals=[],
            score=ResearchSignalScore(0.0, "neutral", 0.0, 0.0, 0.0, "K线数量不足，暂不生成缠论和增强 RSI 信号"),
            blockers=[ResearchSignalBlocker("INSUFFICIENT_BARS", f"至少需要 {min_bars} 根K线，当前 {len(frame)} 根")],
            chan_structure=_empty_chan_structure_overlay(),
        )

    chan = scan_chan_patterns(frame, lookback=lookback)
    rsi = scan_enhanced_rsi(frame, lookback=lookback)
    chan_structure = scan_chan_structure(frame, min_stroke_bars=5, min_rebound_pct=0.03, lookback=lookback)
    signals = sorted([*chan.signals, *rsi.signals], key=lambda signal: (signal.trading_day, signal.kind))
    return ResearchSignalPreview(
        symbol=symbol,
        exchange=exchange,
        start=frame.iloc[0]["trading_day"],
        end=frame.iloc[-1]["trading_day"],
        bars=len(frame),
        signals=signals,
        score=_score(chan.chan_score, rsi.rsi_score, signals),
        blockers=[],
        chan_structure=_chan_structure_overlay(chan_structure),
    )


def _empty_preview(code: str, message: str) -> ResearchSignalPreview:
    return ResearchSignalPreview(
        symbol="",
        exchange="",
        start=None,
        end=None,
        bars=0,
        signals=[],
        score=ResearchSignalScore(0.0, "neutral", 0.0, 0.0, 0.0, message),
        blockers=[ResearchSignalBlocker(code, message)],
        chan_structure=_empty_chan_structure_overlay(),
    )


def _score(chan_score: float, rsi_score: float, signals: list[ResearchSignal]) -> ResearchSignalScore:
    total = round(max(-100.0, min(100.0, chan_score + rsi_score)), 2)
    if total >= 20:
        direction = "bullish"
    elif total <= -20:
        direction = "bearish"
    else:
        direction = "neutral"
    confidence = round(min(1.0, abs(total) / 100.0 + min(len(signals), 6) * 0.04), 2)
    if not signals:
        summary = "未发现缠论或增强 RSI 触发信号"
    else:
        summary = f"发现 {len(signals)} 个研究信号，综合方向为 {direction}"
    return ResearchSignalScore(total, direction, confidence, round(chan_score, 2), round(rsi_score, 2), summary)


def _empty_chan_structure_overlay() -> ChanStructureOverlay:
    return ChanStructureOverlay(
        fractal_count=0,
        stroke_count=0,
        pivot_count=0,
        segment_count=0,
        recursive_pivot_count=0,
        divergence_count=0,
        latest_signal_kind=None,
        latest_signal_title=None,
    )


def _chan_structure_overlay(result: ChanStructureResult) -> ChanStructureOverlay:
    latest_signal = result.signals[-1] if result.signals else None
    days_by_index = {kline.index: kline.trading_day for kline in result.klines}
    return ChanStructureOverlay(
        fractal_count=len(result.fractals),
        stroke_count=len(result.strokes),
        pivot_count=len(result.pivots),
        segment_count=len(result.segments),
        recursive_pivot_count=len(result.recursive_pivots),
        divergence_count=len(result.divergences),
        latest_signal_kind=latest_signal.kind if latest_signal else None,
        latest_signal_title=latest_signal.title if latest_signal else None,
        fractals=[
            ChanFractalOverlay(
                index=fractal.index,
                trading_day=fractal.trading_day,
                kind=fractal.kind,
                price=fractal.price,
                high=fractal.high,
                low=fractal.low,
            )
            for fractal in result.fractals
        ],
        strokes=[
            ChanStrokeOverlay(
                direction=stroke.direction,
                start_index=stroke.start.index,
                end_index=stroke.end.index,
                start_day=stroke.start.trading_day,
                end_day=stroke.end.trading_day,
                start_price=stroke.start.price,
                end_price=stroke.end.price,
                high=stroke.high,
                low=stroke.low,
            )
            for stroke in result.strokes
        ],
        pivots=[
            ChanPivotOverlay(
                start_index=pivot.start_index,
                end_index=pivot.end_index,
                start_day=_chan_index_day(days_by_index, pivot.start_index),
                end_day=_chan_index_day(days_by_index, pivot.end_index),
                low=pivot.low,
                high=pivot.high,
            )
            for pivot in result.pivots
        ],
        segments=[
            ChanSegmentOverlay(
                direction=segment.direction,
                start_index=segment.start.index,
                end_index=segment.end.index,
                start_stroke_index=segment.start_stroke_index,
                end_stroke_index=segment.end_stroke_index,
                break_stroke_index=segment.break_stroke_index,
                start_day=segment.start.trading_day,
                end_day=segment.end.trading_day,
                start_price=segment.start.price,
                end_price=segment.end.price,
                high=segment.high,
                low=segment.low,
                stroke_count=segment.stroke_count,
                energy=segment.energy,
                broken_by_next=segment.broken_by_next,
            )
            for segment in result.segments
        ],
        recursive_pivots=[
            ChanRecursivePivotOverlay(
                level=pivot.level,
                start_index=pivot.start_index,
                end_index=pivot.end_index,
                start_day=pivot.start_day,
                end_day=pivot.end_day,
                low=pivot.low,
                high=pivot.high,
                direction=pivot.direction,
                component_count=pivot.component_count,
            )
            for pivot in result.recursive_pivots
        ],
        divergences=[
            ChanDivergenceOverlay(
                kind=divergence.kind,
                action=divergence.action,
                start_index=divergence.segment.start.index,
                end_index=divergence.segment.end.index,
                reference_start_index=divergence.reference_segment.start.index,
                reference_end_index=divergence.reference_segment.end.index,
                reference_energy=divergence.reference_energy,
                current_energy=divergence.current_energy,
                price_extreme=divergence.price_extreme,
                base_score=divergence.base_score,
                macd_strength=divergence.macd_strength,
                volume_strength=divergence.volume_strength,
                confirmation_score=divergence.confirmation_score,
                macd_reference=divergence.macd_reference,
                macd_current=divergence.macd_current,
                volume_reference=divergence.volume_reference,
                volume_current=divergence.volume_current,
                pivot_level=divergence.pivot_level,
                pivot_start_index=divergence.pivot_start_index,
                pivot_end_index=divergence.pivot_end_index,
                pivot_low=divergence.pivot_low,
                pivot_high=divergence.pivot_high,
            )
            for divergence in result.divergences
        ],
        signals=result.signals,
    )


def _chan_index_day(days_by_index: dict[int, date], index: int) -> date:
    if index in days_by_index:
        return days_by_index[index]
    closest_index = min(days_by_index, key=lambda value: abs(value - index))
    return days_by_index[closest_index]
