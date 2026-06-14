from __future__ import annotations

from collections.abc import Sequence

from ai_trade_system.market import Bar
from ai_trade_system.research.models import ResearchSignalBlocker, ResearchSignalPreview, ResearchSignalScore


def preview_research_signals(bars: Sequence[Bar], *, min_bars: int = 60, lookback: int = 120) -> ResearchSignalPreview:
    if not bars:
        return ResearchSignalPreview(
            symbol="",
            exchange="",
            start=None,
            end=None,
            bars=0,
            signals=[],
            score=ResearchSignalScore(0.0, "neutral", 0.0, 0.0, 0.0, "暂无行情数据"),
            blockers=[ResearchSignalBlocker("NO_BARS", "没有可分析的行情数据")],
        )
    raise NotImplementedError("research signal preview requires detector implementation")
