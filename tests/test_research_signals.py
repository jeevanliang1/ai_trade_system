from __future__ import annotations

from datetime import date, timedelta

from ai_trade_system.market import Bar
from ai_trade_system.research.chan import scan_chan_patterns
from ai_trade_system.research.chan_structure import normalize_containment, scan_chan_structure
from ai_trade_system.research.dataframe import bars_to_frame
from ai_trade_system.research.enhanced_rsi import relative_strength_index, scan_enhanced_rsi
from ai_trade_system.research.service import preview_research_signals


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
