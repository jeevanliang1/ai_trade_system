from __future__ import annotations

from collections.abc import Sequence

from ai_trade_system.market import Bar
from ai_trade_system.research.chan import scan_chan_patterns
from ai_trade_system.research.dataframe import bars_to_frame
from ai_trade_system.research.enhanced_rsi import scan_enhanced_rsi
from ai_trade_system.research.models import ResearchSignal, ResearchSignalBlocker, ResearchSignalPreview, ResearchSignalScore


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
        )

    chan = scan_chan_patterns(frame, lookback=lookback)
    rsi = scan_enhanced_rsi(frame, lookback=lookback)
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
