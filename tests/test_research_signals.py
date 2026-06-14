from __future__ import annotations

from datetime import date, timedelta

from ai_trade_system.market import Bar
from ai_trade_system.research.chan import scan_chan_patterns
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
