from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Any

from ai_trade_system.research.dataframe import bars_to_frame


@dataclass(frozen=True)
class ChanCoreV2CacheStats:
    total_bars: int = 0
    effective_bars: int = 0
    update_count: int = 0
    recompute_count: int = 0
    dirty_start_index: int = 0
    source: str = "full-scan"


@dataclass(frozen=True)
class ChanTrendType:
    level: str
    trend_type: str
    phase: str
    direction: str
    start_index: int
    end_index: int
    high: float
    low: float
    component_count: int
    lineage_id: str


@dataclass(frozen=True)
class ChanPivotLifecycle:
    level: str
    lineage_id: str
    state: str
    start_index: int
    end_index: int
    low: float
    high: float
    direction: str
    component_count: int
    break_index: int | None = None
    break_direction: str | None = None


@dataclass(frozen=True)
class ChanCoreV2Snapshot:
    trends: list[ChanTrendType]
    pivot_lifecycles: list[ChanPivotLifecycle]
    cache: ChanCoreV2CacheStats


def build_chan_core_v2_snapshot(
    *,
    strokes: list[Any],
    segments: list[Any],
    recursive_pivots: list[Any],
    source: str = "full-scan",
    cache: ChanCoreV2CacheStats | None = None,
) -> ChanCoreV2Snapshot:
    components_by_level = {
        "stroke": strokes,
        "segment": segments,
    }
    base_cache = cache or ChanCoreV2CacheStats(source=source)
    pivots_by_level = {
        level: [pivot for pivot in recursive_pivots if pivot.level == level]
        for level in components_by_level
    }
    lifecycles = [
        lifecycle
        for level, pivots in pivots_by_level.items()
        for lifecycle in _build_pivot_lifecycles(level, pivots, components_by_level[level])
    ]
    return ChanCoreV2Snapshot(
        trends=[
            trend
            for level, components in components_by_level.items()
            if (trend := _classify_level_trend(level, components, pivots_by_level[level], lifecycles)) is not None
        ],
        pivot_lifecycles=lifecycles,
        cache=base_cache,
    )


def _build_pivot_lifecycles(level: str, pivots: list[Any], components: list[Any]) -> list[ChanPivotLifecycle]:
    lifecycles: list[ChanPivotLifecycle] = []
    for pivot_index, pivot in enumerate(pivots):
        lineage_id = _pivot_lineage_id(level, pivot)
        initial_state = "extended" if pivot.component_count > 3 else "confirmed"
        lifecycles.append(_pivot_lifecycle(level, pivot, lineage_id, initial_state))

        break_info = _pivot_break_info(pivot, components)
        if break_info is None:
            continue

        break_index, break_direction = break_info
        lifecycles.append(
            _pivot_lifecycle(
                level,
                pivot,
                lineage_id,
                "broken",
                break_index=break_index,
                break_direction=break_direction,
            )
        )
        if pivot_index < len(pivots) - 1:
            lifecycles.append(
                _pivot_lifecycle(
                    level,
                    pivot,
                    lineage_id,
                    "completed",
                    break_index=break_index,
                    break_direction=break_direction,
                )
            )
    return lifecycles


def _pivot_lifecycle(
    level: str,
    pivot: Any,
    lineage_id: str,
    state: str,
    *,
    break_index: int | None = None,
    break_direction: str | None = None,
) -> ChanPivotLifecycle:
    return ChanPivotLifecycle(
        level=level,
        lineage_id=lineage_id,
        state=state,
        start_index=pivot.start_index,
        end_index=pivot.end_index,
        low=pivot.low,
        high=pivot.high,
        direction=pivot.direction,
        component_count=pivot.component_count,
        break_index=break_index,
        break_direction=break_direction,
    )


def _pivot_break_info(pivot: Any, components: list[Any]) -> tuple[int, str] | None:
    for component in components:
        if component.end.index <= pivot.end_index:
            continue
        if component.low > pivot.high:
            return component.end.index, "up"
        if component.high < pivot.low:
            return component.end.index, "down"
    return None


def _classify_level_trend(
    level: str,
    components: list[Any],
    pivots: list[Any],
    lifecycles: list[ChanPivotLifecycle],
) -> ChanTrendType | None:
    if not components:
        return None

    latest = components[-1]
    previous = components[-2] if len(components) >= 2 else None
    phase = _trend_phase(level, components, pivots, lifecycles)
    trend_type = _trend_type(latest, previous, pivots)
    return ChanTrendType(
        level=level,
        trend_type=trend_type,
        phase=phase,
        direction=latest.direction,
        start_index=components[0].start.index,
        end_index=latest.end.index,
        high=round(max(component.high for component in components), 4),
        low=round(min(component.low for component in components), 4),
        component_count=len(components),
        lineage_id=f"core-v2:{level}:{components[0].start.index}-{latest.end.index}",
    )


def _trend_phase(
    level: str,
    components: list[Any],
    pivots: list[Any],
    lifecycles: list[ChanPivotLifecycle],
) -> str:
    if len(components) < 3:
        return "forming"
    level_lifecycles = [lifecycle for lifecycle in lifecycles if lifecycle.level == level]
    if any(lifecycle.state == "broken" for lifecycle in level_lifecycles):
        return "broken"
    if any(lifecycle.state == "extended" for lifecycle in level_lifecycles):
        return "extended"
    if pivots:
        return "confirmed"
    return "transition"


def _trend_type(latest: Any, previous: Any | None, pivots: list[Any]) -> str:
    active_pivot = pivots[-1] if pivots else None
    if active_pivot is not None and latest.low <= active_pivot.high and latest.high >= active_pivot.low:
        return "range"
    if previous is None:
        return "transition"
    if latest.direction == "up" and (latest.high > previous.high or latest.end.price > previous.end.price):
        return "up"
    if latest.direction == "down" and (latest.low < previous.low or latest.end.price < previous.end.price):
        return "down"
    return "transition"


def _pivot_lineage_id(level: str, pivot: Any) -> str:
    return f"core-v2:{level}:{pivot.start_index}-{pivot.end_index}"


class ChanCoreV2Analyzer:
    def __init__(self, *, min_stroke_bars: int = 5, min_rebound_pct: float = 0.03, lookback: int | None = None) -> None:
        if min_stroke_bars < 1:
            raise ValueError("min_stroke_bars must be positive")
        if min_rebound_pct < 0:
            raise ValueError("min_rebound_pct must be non-negative")
        if lookback is not None and lookback < 1:
            raise ValueError("lookback must be positive")
        self.min_stroke_bars = min_stroke_bars
        self.min_rebound_pct = min_rebound_pct
        self.lookback = lookback
        self.bars: deque[Any] = deque(maxlen=lookback)
        self.total_bars = 0
        self.update_count = 0
        self.recompute_count = 0
        self._identity: tuple[str, str] | None = None

    def update_bar(self, bar: Any) -> Any:
        identity = (str(bar.symbol), str(bar.exchange))
        if self._identity is not None and identity != self._identity:
            self.bars.clear()
            self.total_bars = 0
            self.update_count = 0
            self.recompute_count = 0
        self._identity = identity
        self.bars.append(bar)
        self.total_bars += 1
        self.update_count += 1
        self.recompute_count += 1

        from ai_trade_system.research.chan_structure import scan_chan_structure

        result = scan_chan_structure(
            bars_to_frame(list(self.bars)),
            min_stroke_bars=self.min_stroke_bars,
            min_rebound_pct=self.min_rebound_pct,
        )
        cache = ChanCoreV2CacheStats(
            total_bars=self.total_bars,
            effective_bars=len(self.bars),
            update_count=self.update_count,
            recompute_count=self.recompute_count,
            dirty_start_index=max(0, self.total_bars - len(self.bars)),
            source="incremental-window",
        )
        if result.core_v2 is None:
            return result
        return replace(result, core_v2=replace(result.core_v2, cache=cache))
