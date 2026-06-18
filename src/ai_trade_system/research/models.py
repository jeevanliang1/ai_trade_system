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
class ChanFractalOverlay:
    index: int
    trading_day: date
    kind: str
    price: float
    high: float
    low: float


@dataclass(frozen=True)
class ChanStrokeOverlay:
    direction: str
    start_index: int
    end_index: int
    start_day: date
    end_day: date
    start_price: float
    end_price: float
    high: float
    low: float


@dataclass(frozen=True)
class ChanPivotOverlay:
    start_index: int
    end_index: int
    start_day: date
    end_day: date
    low: float
    high: float


@dataclass(frozen=True)
class ChanStructureOverlay:
    fractal_count: int
    stroke_count: int
    pivot_count: int
    latest_signal_kind: str | None
    latest_signal_title: str | None
    fractals: list[ChanFractalOverlay] = field(default_factory=list)
    strokes: list[ChanStrokeOverlay] = field(default_factory=list)
    pivots: list[ChanPivotOverlay] = field(default_factory=list)
    signals: list[ResearchSignal] = field(default_factory=list)


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
    chan_structure: ChanStructureOverlay | None = None


@dataclass(frozen=True)
class EnhancedRsiResult:
    signals: list[ResearchSignal]
    latest_rsi: float | None
    rsi_score: float


@dataclass(frozen=True)
class ChanPatternResult:
    signals: list[ResearchSignal]
    chan_score: float
