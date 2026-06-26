from __future__ import annotations

from datetime import date, datetime

from ai_trade_system.market import Bar, Signal
from ai_trade_system.realtime import RealtimeMonitorService
from ai_trade_system.realtime_sources import MarketDataSource
from ai_trade_system.stock_catalog import StockInfo
from ai_trade_system.strategy import Strategy


class ThresholdStrategy(Strategy):
    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.close_price >= 13:
            return [Signal("buy", bar.symbol, bar.close_price, 100, "threshold reached")]
        return []


class RecordingSource(MarketDataSource):
    def __init__(self, market: str, bars: list[Bar]) -> None:
        self.market = market
        self.bars = bars
        self.calls: list[tuple[str, str, str]] = []

    def fetch_bars(self, symbol: str, exchange: str, start_date: str, end_date: str, adjust: str, timeframe: str) -> list[Bar]:
        self.calls.append((symbol, exchange, timeframe))
        return self.bars


def _bar(symbol: str, minute: int, close: float) -> Bar:
    return Bar(
        symbol=symbol,
        exchange="SZSE",
        trading_day=date(2026, 6, 22),
        timestamp=datetime(2026, 6, 22, 10, minute),
        timeframe="1m",
        open_price=close - 0.1,
        high_price=close + 0.2,
        low_price=close - 0.2,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
    )


def test_monitor_warms_strategy_without_alerting_historical_signals() -> None:
    batches = [
        [_bar("000001", 0, 10), _bar("000001", 1, 13)],
        [_bar("000001", 0, 10), _bar("000001", 1, 13), _bar("000001", 2, 14)],
    ]

    def fetcher(*_args, **_kwargs):
        return batches.pop(0)

    service = RealtimeMonitorService(fetch_bars=fetcher)
    service.start(
        strategy=ThresholdStrategy(),
        strategy_id="test:threshold",
        stocks=[StockInfo("000001", "平安银行", "SZSE")],
        start_date="20260622",
        adjust="qfq",
        timeframe="1m",
        poll_interval_seconds=1,
        background=False,
    )

    service.poll_once()
    warmup_events = service.events()
    assert [event["event"] for event in warmup_events] == ["monitor_started", "bar_updated", "monitor_heartbeat"]
    assert warmup_events[1]["warmup"] is True

    service.poll_once()
    events = service.events()
    signal_events = [event for event in events if event["event"] == "signal_triggered"]
    assert len(signal_events) == 1
    assert signal_events[0]["symbol"] == "000001"
    assert signal_events[0]["side"] == "buy"
    assert signal_events[0]["reason"] == "threshold reached"

    service.stop()


def test_monitor_skips_duplicate_latest_bars() -> None:
    latest = [_bar("000001", 0, 10), _bar("000001", 1, 11)]

    def fetcher(*_args, **_kwargs):
        return latest

    service = RealtimeMonitorService(fetch_bars=fetcher)
    service.start(
        strategy=ThresholdStrategy(),
        strategy_id="test:threshold",
        stocks=[StockInfo("000001", "平安银行", "SZSE")],
        start_date="20260622",
        adjust="qfq",
        timeframe="1m",
        poll_interval_seconds=1,
        background=False,
    )

    service.poll_once()
    service.poll_once()

    bar_events = [event for event in service.events() if event["event"] == "bar_updated"]
    assert len(bar_events) == 1
    assert service.status()["last_bar_time"] == "2026-06-22T10:01:00"

    service.stop()


def test_monitor_routes_stocks_to_market_data_sources() -> None:
    a_share_source = RecordingSource("a_share", [_bar("000001", 0, 10)])
    us_source = RecordingSource("us_stock", [_bar("AAPL", 0, 190)])
    crypto_source = RecordingSource("crypto", [_bar("BTCUSDT", 0, 65000)])
    service = RealtimeMonitorService(
        market_data_sources={
            "a_share": a_share_source,
            "us_stock": us_source,
            "crypto": crypto_source,
        }
    )

    stocks = [
        StockInfo("000001", "平安银行", "SZSE"),
        StockInfo("AAPL", "Apple", "NASDAQ"),
        StockInfo("BTCUSDT", "Bitcoin", "CRYPTO"),
    ]
    service.start(
        strategy=ThresholdStrategy(),
        strategy_id="test:threshold",
        stocks=stocks,
        start_date="20260622",
        adjust="qfq",
        timeframe="1m",
        poll_interval_seconds=1,
        background=False,
        stock_markets={
            "000001.SZSE": "a_share",
            "AAPL.NASDAQ": "us_stock",
            "BTCUSDT.CRYPTO": "crypto",
        },
        market_counts={"a_share": 1, "us_stock": 1, "crypto": 1},
    )

    service.poll_once()
    status = service.status()

    assert a_share_source.calls == [("000001", "SZSE", "1m")]
    assert us_source.calls == [("AAPL", "NASDAQ", "1m")]
    assert crypto_source.calls == [("BTCUSDT", "CRYPTO", "1m")]
    assert status["market_counts"] == {"a_share": 1, "us_stock": 1, "crypto": 1}
    assert status["stock_markets"]["AAPL.NASDAQ"] == "us_stock"
    bar_events = [event for event in service.events() if event["event"] == "bar_updated"]
    assert {event["market"] for event in bar_events} == {"a_share", "us_stock", "crypto"}

    service.stop()
