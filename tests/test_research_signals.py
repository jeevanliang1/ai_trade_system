from __future__ import annotations

from datetime import date, timedelta

from ai_trade_system.market import Bar
from ai_trade_system.research.dataframe import bars_to_frame
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
