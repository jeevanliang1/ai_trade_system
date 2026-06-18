from __future__ import annotations

from datetime import date, timedelta

from ai_trade_system.market import Bar
from ai_trade_system.research.chan import scan_chan_patterns
from ai_trade_system.research.chan_structure import ChanFractal, ChanStructureResult, ChanStroke, _build_recursive_pivots, _build_segments, normalize_containment, scan_chan_structure
from ai_trade_system.research.dataframe import bars_to_frame
from ai_trade_system.research.enhanced_rsi import relative_strength_index, scan_enhanced_rsi
from ai_trade_system.research.service import preview_research_signals
from ai_trade_system.research.service import _chan_structure_overlay


def _bar(index: int, close: float, *, high: float | None = None, low: float | None = None, volume: float = 1000.0) -> Bar:
    trading_day = date(2024, 1, 1) + timedelta(days=index)
    high_price = high if high is not None else close + 0.4
    low_price = low if low is not None else close - 0.4
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=trading_day,
        open_price=close - 0.1,
        high_price=high_price,
        low_price=low_price,
        close_price=close,
        volume=volume,
        turnover=round(volume * close, 2),
    )


def _bars(closes: list[float]) -> list[Bar]:
    return [_bar(index, close) for index, close in enumerate(closes)]


def _fractal(index: int, kind: str, price: float) -> ChanFractal:
    return ChanFractal(index, date(2024, 1, 1) + timedelta(days=index), kind, price, price, price)


def _stroke(start_index: int, end_index: int, direction: str, start_price: float, end_price: float) -> ChanStroke:
    start_kind = "bottom" if direction == "up" else "top"
    end_kind = "top" if direction == "up" else "bottom"
    return ChanStroke(
        start=_fractal(start_index, start_kind, start_price),
        end=_fractal(end_index, end_kind, end_price),
        direction=direction,
        high=max(start_price, end_price),
        low=min(start_price, end_price),
    )


def _strict_segment_strokes() -> list[ChanStroke]:
    return [
        _stroke(0, 5, "up", 10.0, 15.0),
        _stroke(5, 10, "down", 15.0, 12.0),
        _stroke(10, 15, "up", 12.0, 16.0),
        _stroke(15, 20, "down", 16.0, 13.0),
        _stroke(20, 25, "up", 13.0, 17.0),
        _stroke(25, 30, "down", 17.0, 9.0),
        _stroke(30, 35, "up", 9.0, 14.0),
        _stroke(35, 40, "down", 14.0, 8.0),
        _stroke(40, 45, "up", 8.0, 12.0),
        _stroke(45, 50, "down", 12.0, 7.0),
        _stroke(50, 55, "up", 7.0, 18.0),
        _stroke(55, 60, "down", 18.0, 13.0),
        _stroke(60, 65, "up", 13.0, 19.0),
    ]


def _bars_from_extrema(points: list[tuple[int, float]]) -> list[Bar]:
    bars: list[Bar] = []
    for index in range(points[-1][0] + 2):
        if index <= points[0][0]:
            close = points[0][1] + (points[0][0] - index + 1) * 0.2
        elif index >= points[-1][0]:
            close = points[-1][1] - (index - points[-1][0] + 1) * 0.2
        else:
            close = points[-1][1]
            for (left_index, left_price), (right_index, right_price) in zip(points, points[1:]):
                if left_index <= index <= right_index:
                    ratio = (index - left_index) / (right_index - left_index)
                    close = left_price + (right_price - left_price) * ratio
                    break
        close = round(close, 4)
        bars.append(_bar(index, close, high=close + 0.1, low=close - 0.1))
    return bars


def _strict_chan_bars() -> list[Bar]:
    return _bars_from_extrema(
        [
            (1, 10.0),
            (6, 15.0),
            (11, 12.0),
            (16, 16.0),
            (21, 13.0),
            (26, 17.0),
            (31, 9.0),
            (36, 14.0),
            (41, 8.0),
            (46, 12.0),
            (51, 7.0),
            (86, 18.0),
            (91, 13.0),
            (96, 19.0),
            (101, 6.0),
            (130, 15.0),
            (160, 5.0),
            (190, 14.0),
            (220, 4.0),
        ]
    )


def _indicator_divergence_bars(*, rebound_after_bottom: bool) -> list[Bar]:
    points = [
        (1, 10.0),
        (6, 15.0),
        (11, 12.0),
        (16, 16.0),
        (21, 13.0),
        (26, 17.0),
        (31, 9.0),
        (36, 14.0),
        (41, 8.0),
        (46, 12.0),
        (51, 7.0),
        (86, 18.0),
        (91, 13.0),
        (96, 19.0),
        (101, 6.0),
        (130, 15.0),
        (160, 5.0),
        (190, 14.0),
    ]
    if not rebound_after_bottom:
        points.append((220, 4.0))

    bars = _bars_from_extrema(points)
    adjusted: list[Bar] = []
    for bar in bars:
        if bar.trading_day <= date(2024, 1, 1) + timedelta(days=26):
            volume = 2400.0
        elif bar.trading_day <= date(2024, 1, 1) + timedelta(days=51):
            volume = 2200.0
        elif bar.trading_day <= date(2024, 1, 1) + timedelta(days=96):
            volume = 850.0
        elif bar.trading_day <= date(2024, 1, 1) + timedelta(days=160):
            volume = 700.0
        else:
            volume = 900.0
        adjusted.append(
            Bar(
                symbol=bar.symbol,
                exchange=bar.exchange,
                trading_day=bar.trading_day,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                close_price=bar.close_price,
                volume=volume,
                turnover=round(volume * bar.close_price, 2),
            )
        )
    return adjusted


def test_bars_to_frame_sorts_and_maps_market_bars():
    frame = bars_to_frame([_bar(2, 12.0), _bar(0, 10.0), _bar(1, 11.0)])

    assert list(frame.columns) == ["trading_day", "symbol", "exchange", "open", "high", "low", "close", "volume", "turnover"]
    assert [value.isoformat() for value in frame["trading_day"].tolist()] == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert frame.iloc[-1]["close"] == 12.0


def test_preview_returns_no_bars_blocker_for_empty_input():
    preview = preview_research_signals([])

    assert preview.symbol == ""
    assert preview.score.direction == "neutral"
    assert preview.blockers[0].code == "NO_BARS"
    assert preview.signals == []


def test_relative_strength_index_handles_rising_and_falling_windows():
    rising = relative_strength_index([10, 11, 12, 13, 14, 15, 16], period=3)
    falling = relative_strength_index([16, 15, 14, 13, 12, 11, 10], period=3)

    assert rising[-1] == 100.0
    assert falling[-1] == 0.0


def test_enhanced_rsi_marks_oversold_recovery_and_bearish_divergence():
    closes = [12, 11.5, 11, 10.4, 9.8, 9.5, 9.7, 10.1, 10.8, 11.4, 11.9, 12.3, 12.6, 12.9, 13.1, 13.0, 13.2]
    frame = bars_to_frame(_bars(closes))

    result = scan_enhanced_rsi(frame, period=3, lookback=30)
    kinds = {signal.kind for signal in result.signals}

    assert "RSI_OVERSOLD" in kinds
    assert "RSI_BULLISH_RECOVERY" in kinds
    assert result.rsi_score > 0


def test_enhanced_rsi_marks_bearish_divergence_when_price_highs_rise_and_rsi_fades():
    closes = [10, 11, 12, 13, 12.2, 13.1, 13.6, 12.9, 13.4, 13.9, 13.1]
    frame = bars_to_frame(_bars(closes))

    result = scan_enhanced_rsi(frame, period=3, lookback=30)

    assert any(signal.kind == "RSI_BEARISH_DIVERGENCE" for signal in result.signals)


def test_chan_scanner_marks_second_buy_after_higher_low_reversal():
    closes = [12.0, 11.4, 10.8, 10.1, 9.8, 10.4, 11.1, 11.6, 10.9, 10.4, 10.8, 11.5, 12.0, 12.4]
    frame = bars_to_frame(_bars(closes))

    result = scan_chan_patterns(frame, lookback=40, order=1)

    assert any(signal.kind == "CHAN_BUY_T2" for signal in result.signals)
    assert result.chan_score > 0


def test_chan_scanner_marks_second_sell_after_lower_high_breakdown():
    closes = [9.0, 9.8, 10.6, 11.4, 12.0, 11.5, 10.9, 10.2, 10.8, 11.3, 10.7, 10.0, 9.4, 9.0]
    frame = bars_to_frame(_bars(closes))

    result = scan_chan_patterns(frame, lookback=40, order=1)

    assert any(signal.kind == "CHAN_SELL_T2" for signal in result.signals)
    assert result.chan_score < 0


def test_chan_structure_normalizes_contained_klines():
    bars = [
        _bar(0, 10.0, high=10.0, low=9.0),
        _bar(1, 10.4, high=11.0, low=10.0),
        _bar(2, 10.5, high=10.8, low=10.2),
        _bar(3, 11.0, high=12.0, low=10.8),
    ]

    normalized = normalize_containment(bars_to_frame(bars))

    assert len(normalized) == 3
    assert normalized[1].high == 11.0
    assert normalized[1].low == 10.2


def test_chan_structure_builds_fractals_strokes_and_pivots():
    bars = [
        _bar(0, 10.0, high=10.4, low=9.8),
        _bar(1, 9.4, high=9.8, low=9.1),
        _bar(2, 10.2, high=10.7, low=9.9),
        _bar(3, 11.2, high=11.8, low=10.8),
        _bar(4, 10.4, high=10.9, low=10.0),
        _bar(5, 9.8, high=10.1, low=9.4),
        _bar(6, 10.8, high=11.2, low=10.2),
        _bar(7, 11.6, high=12.0, low=11.0),
        _bar(8, 10.8, high=11.2, low=10.2),
        _bar(9, 10.1, high=10.4, low=9.7),
        _bar(10, 11.1, high=11.5, low=10.7),
        _bar(11, 11.8, high=12.3, low=11.3),
    ]

    result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=2, min_rebound_pct=0.03)

    assert [fractal.kind for fractal in result.fractals] == ["bottom", "top", "bottom", "top", "bottom"]
    assert [stroke.direction for stroke in result.strokes[:4]] == ["up", "down", "up", "down"]
    assert result.pivots


def test_chan_structure_marks_third_buy_and_sell_points():
    buy_bars = [
        _bar(0, 10.0, high=10.4, low=9.8),
        _bar(1, 9.4, high=9.8, low=9.1),
        _bar(2, 10.4, high=10.9, low=10.0),
        _bar(3, 11.6, high=12.0, low=11.1),
        _bar(4, 10.8, high=11.0, low=10.2),
        _bar(5, 10.1, high=10.5, low=9.7),
        _bar(6, 11.5, high=12.0, low=11.0),
        _bar(7, 12.8, high=13.2, low=12.2),
        _bar(8, 12.6, high=12.8, low=12.4),
        _bar(9, 12.5, high=12.6, low=12.3),
        _bar(10, 12.3, high=12.4, low=12.1),
        _bar(11, 12.8, high=13.0, low=12.5),
    ]
    sell_bars = [
        _bar(0, 12.0, high=12.4, low=11.7),
        _bar(1, 12.8, high=13.2, low=12.2),
        _bar(2, 11.8, high=12.1, low=11.4),
        _bar(3, 10.7, high=11.1, low=10.2),
        _bar(4, 11.3, high=11.7, low=10.9),
        _bar(5, 12.0, high=12.4, low=11.6),
        _bar(6, 10.9, high=11.3, low=10.5),
        _bar(7, 9.6, high=9.7, low=9.4),
        _bar(8, 9.7, high=9.8, low=9.6),
        _bar(9, 9.9, high=10.0, low=9.7),
        _bar(10, 9.5, high=9.8, low=9.1),
    ]

    buy_result = scan_chan_structure(bars_to_frame(buy_bars), min_stroke_bars=2, min_rebound_pct=0.03)
    sell_result = scan_chan_structure(bars_to_frame(sell_bars), min_stroke_bars=2, min_rebound_pct=0.03)

    assert any(signal.kind == "CHAN_STRUCT_BUY_T3" for signal in buy_result.signals)
    assert any(signal.kind == "CHAN_STRUCT_SELL_T3" for signal in sell_result.signals)


def test_chan_structure_builds_segments_recursive_pivots_and_divergence():
    bars = _strict_chan_bars()

    result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=4, min_rebound_pct=0.02)

    assert len(result.segments) >= 4
    assert result.recursive_pivots
    assert any(pivot.level == "segment" for pivot in result.recursive_pivots)
    assert result.divergences
    assert any(
        signal.kind
        in {
            "CHAN_STRUCT_BUY_T1_DIVERGENCE",
            "CHAN_STRUCT_BUY_CONFIRM",
            "CHAN_STRUCT_SELL_T1_DIVERGENCE",
            "CHAN_STRUCT_SELL_CONFIRM",
        }
        for signal in result.signals
    )


def test_chan_structure_builds_non_overlapping_segments_from_breaks():
    segments = _build_segments(_strict_segment_strokes())
    segment_pivots = [pivot for pivot in _build_recursive_pivots([], segments) if pivot.level == "segment"]

    assert [(segment.start_stroke_index, segment.end_stroke_index, segment.break_stroke_index) for segment in segments] == [
        (0, 4, 5),
        (5, 9, 10),
        (10, 12, None),
    ]
    assert [(segment.start.index, segment.end.index) for segment in segments] == [(0, 25), (25, 50), (50, 65)]
    assert [segment.broken_by_next for segment in segments] == [True, True, False]
    assert all(left.end.index <= right.start.index for left, right in zip(segments, segments[1:]))
    assert segment_pivots


def test_chan_structure_scores_divergence_with_macd_and_volume_evidence():
    result = scan_chan_structure(
        bars_to_frame(_indicator_divergence_bars(rebound_after_bottom=True)),
        min_stroke_bars=4,
        min_rebound_pct=0.02,
    )

    buy_divergence = next(divergence for divergence in result.divergences if divergence.action == "buy")
    sell_divergence = next(divergence for divergence in result.divergences if divergence.action == "sell")
    buy_confirm = next(signal for signal in result.signals if signal.kind == "CHAN_STRUCT_BUY_CONFIRM")
    sell_confirm = next(signal for signal in result.signals if signal.kind == "CHAN_STRUCT_SELL_CONFIRM")

    assert buy_divergence.base_score > 36.0
    assert buy_divergence.macd_strength > 0
    assert buy_divergence.volume_strength > 0
    assert buy_divergence.confirmation_score > buy_divergence.base_score
    assert buy_confirm.score == buy_divergence.confirmation_score
    assert buy_confirm.strength > 0.52
    assert "MACD" in buy_confirm.reason
    assert "成交量" in buy_confirm.reason

    assert sell_divergence.base_score > 36.0
    assert sell_divergence.macd_strength > 0
    assert sell_divergence.volume_strength > 0
    assert sell_divergence.confirmation_score > sell_divergence.base_score
    assert sell_confirm.score == -sell_divergence.confirmation_score
    assert sell_confirm.strength > 0.52
    assert "MACD" in sell_confirm.reason
    assert "成交量" in sell_confirm.reason


def test_chan_structure_overlay_exposes_segments_recursive_pivots_and_divergences():
    bars = _strict_chan_bars()
    result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=4, min_rebound_pct=0.02)

    overlay = _chan_structure_overlay(result)

    assert overlay.segment_count == len(result.segments)
    assert overlay.recursive_pivot_count == len(result.recursive_pivots)
    assert overlay.divergence_count == len(result.divergences)
    assert overlay.segments[0].stroke_count >= 3
    assert overlay.segments[0].start_stroke_index == result.segments[0].start_stroke_index
    assert overlay.segments[0].end_stroke_index == result.segments[0].end_stroke_index
    assert any(pivot.level == "segment" for pivot in overlay.recursive_pivots)
    assert overlay.divergences[0].kind == "top"

    strict_segments = _build_segments(_strict_segment_strokes())
    strict_overlay = _chan_structure_overlay(
        ChanStructureResult(
            klines=[],
            fractals=[],
            strokes=[],
            pivots=[],
            segments=strict_segments,
            recursive_pivots=[],
            divergences=[],
            signals=[],
            chan_score=0.0,
        )
    )
    assert any(segment.break_stroke_index is not None for segment in strict_overlay.segments)


def test_chan_structure_overlay_exposes_indicator_divergence_evidence():
    result = scan_chan_structure(
        bars_to_frame(_indicator_divergence_bars(rebound_after_bottom=False)),
        min_stroke_bars=4,
        min_rebound_pct=0.02,
    )

    overlay = _chan_structure_overlay(result)

    assert overlay.divergences[0].base_score == result.divergences[0].base_score
    assert overlay.divergences[0].macd_strength == result.divergences[0].macd_strength
    assert overlay.divergences[0].volume_strength == result.divergences[0].volume_strength
    assert overlay.divergences[0].confirmation_score == result.divergences[0].confirmation_score
    assert overlay.divergences[0].macd_reference == result.divergences[0].macd_reference
    assert overlay.divergences[0].macd_current == result.divergences[0].macd_current
    assert overlay.divergences[0].volume_reference == result.divergences[0].volume_reference
    assert overlay.divergences[0].volume_current == result.divergences[0].volume_current


def test_preview_returns_insufficient_bars_blocker_before_running_detectors():
    preview = preview_research_signals(_bars([10, 10.2, 10.1]), min_bars=10)

    assert preview.blockers[0].code == "INSUFFICIENT_BARS"
    assert preview.signals == []
    assert preview.score.direction == "neutral"


def test_preview_combines_chan_and_rsi_scores_for_valid_bars():
    closes = [12, 11.4, 10.8, 10.1, 9.8, 10.4, 11.1, 11.6, 10.9, 10.4, 10.8, 11.5, 12.0, 12.4, 12.8, 13.0]
    preview = preview_research_signals(_bars(closes), min_bars=12, lookback=40)

    assert preview.symbol == "000001"
    assert preview.exchange == "SZSE"
    assert preview.start.isoformat() == "2024-01-01"
    assert preview.end.isoformat() == "2024-01-16"
    assert preview.blockers == []
    assert preview.score.direction in {"bullish", "bearish", "neutral"}
    assert preview.signals


def test_preview_includes_chan_structure_overlay_payload():
    price_ranges = [
        (11.0, 10.0),
        (9.5, 9.0),
        (10.0, 9.5),
        (10.5, 10.0),
        (11.0, 10.5),
        (11.5, 11.0),
        (12.0, 11.5),
        (13.0, 12.0),
        (12.4, 11.6),
        (12.0, 11.2),
        (11.6, 10.8),
        (11.2, 10.4),
        (10.8, 10.2),
        (10.5, 10.0),
        (11.0, 10.4),
        (11.6, 11.0),
        (12.2, 11.6),
        (12.8, 12.2),
        (13.3, 12.7),
        (14.0, 13.0),
        (13.5, 12.8),
        (13.2, 12.6),
        (12.9, 12.4),
        (12.7, 12.2),
        (12.6, 12.1),
        (12.5, 12.0),
        (13.4, 12.8),
        (13.8, 13.1),
        (14.1, 13.4),
        (14.5, 13.8),
    ]
    bars = [_bar(index, (high + low) / 2, high=high, low=low) for index, (high, low) in enumerate(price_ranges)]

    preview = preview_research_signals(bars, min_bars=12, lookback=120)

    assert preview.chan_structure is not None
    assert preview.chan_structure.fractal_count > 0
    assert preview.chan_structure.stroke_count > 0
    assert preview.chan_structure.pivot_count > 0
    assert preview.chan_structure.fractals[0].kind in {"top", "bottom"}
    assert preview.chan_structure.strokes[0].start_day is not None
    assert preview.chan_structure.pivots[0].start_day is not None
    assert any(signal.kind.startswith("CHAN_STRUCT_") for signal in preview.chan_structure.signals)
