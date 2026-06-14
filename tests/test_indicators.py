from datetime import date, timedelta

from ai_trade_system.indicators import latest_indicator_snapshot, simple_moving_average
from ai_trade_system.market import Bar


def _bars(closes: list[float]) -> list[Bar]:
    start = date(2024, 1, 1)
    return [
        Bar(
            symbol="000001",
            exchange="SZSE",
            trading_day=start + timedelta(days=index),
            open_price=close - 1,
            high_price=close + 1,
            low_price=close - 2,
            close_price=close,
            volume=1000 + index,
            turnover=10000 + index,
        )
        for index, close in enumerate(closes)
    ]


def test_simple_moving_average_returns_none_until_window_is_full():
    assert simple_moving_average([10, 12, 14], 2) == [None, 11.0, 13.0]


def test_latest_indicator_snapshot_summarizes_trend_momentum_and_risk():
    snapshot = latest_indicator_snapshot(_bars([10, 11, 12, 13, 14, 15, 16]), short_window=3, long_window=5)

    assert snapshot.symbol == "000001"
    assert snapshot.close_price == 16
    assert snapshot.short_ma == 15
    assert snapshot.long_ma == 14
    assert snapshot.trend == "bullish"
    assert snapshot.momentum > 0
