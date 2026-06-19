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
    metadata: dict[str, object] = field(default_factory=dict)


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
class ChanSegmentOverlay:
    level: str
    sequence_index: int
    lineage_id: str
    direction: str
    start_index: int
    end_index: int
    start_stroke_index: int
    end_stroke_index: int
    break_stroke_index: int | None
    start_day: date
    end_day: date
    start_price: float
    end_price: float
    high: float
    low: float
    stroke_count: int
    energy: float
    broken_by_next: bool


@dataclass(frozen=True)
class ChanRecursivePivotOverlay:
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
class ChanDivergenceOverlay:
    kind: str
    action: str
    start_index: int
    end_index: int
    reference_start_index: int
    reference_end_index: int
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
    pivot_level: str | None
    pivot_start_index: int | None
    pivot_end_index: int | None
    pivot_low: float | None
    pivot_high: float | None


@dataclass(frozen=True)
class ChanStructureOverlay:
    fractal_count: int
    stroke_count: int
    pivot_count: int
    segment_count: int
    recursive_pivot_count: int
    divergence_count: int
    latest_signal_kind: str | None
    latest_signal_title: str | None
    fractals: list[ChanFractalOverlay] = field(default_factory=list)
    strokes: list[ChanStrokeOverlay] = field(default_factory=list)
    pivots: list[ChanPivotOverlay] = field(default_factory=list)
    segments: list[ChanSegmentOverlay] = field(default_factory=list)
    recursive_pivots: list[ChanRecursivePivotOverlay] = field(default_factory=list)
    divergences: list[ChanDivergenceOverlay] = field(default_factory=list)
    signals: list[ResearchSignal] = field(default_factory=list)
    core_v2_trend_count: int = 0
    core_v2_pivot_lifecycle_count: int = 0
    core_v2_cache: dict[str, object] = field(default_factory=dict)
    core_v2_latest_trend: str | None = None
    core_v2_pivot_states: dict[str, int] = field(default_factory=dict)


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
