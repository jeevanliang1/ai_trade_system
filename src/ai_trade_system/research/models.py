from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ResearchSignal:
    trading_day: date
    symbol: str
    exchange: str
    kind: str
    action: str
    price: float
    strength: float
    score: float
    title: str
    reason: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResearchSignalBlocker:
    code: str
    message: str


@dataclass(frozen=True)
class ResearchSignalScore:
    total_score: float
    direction: str
    confidence: float
    chan_score: float
    rsi_score: float
    summary: str


@dataclass(frozen=True)
class ResearchSignalPreview:
    symbol: str
    exchange: str
    start: date | None
    end: date | None
    bars: int
    signals: list[ResearchSignal]
    score: ResearchSignalScore
    blockers: list[ResearchSignalBlocker] = field(default_factory=list)
