from __future__ import annotations

from datetime import datetime

from ai_trade_system.realtime_sources import BinanceSpotMarketDataSource, DemoRealtimeMarketDataSource, FallbackMarketDataSource, YahooChartMarketDataSource


class FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict, timeout: float):
        self.calls.append((url, params))
        return FakeResponse(self.payload)


def test_yahoo_chart_source_converts_latest_quote_to_bars() -> None:
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1719835800, 1719835860],
                    "indicators": {
                        "quote": [
                            {
                                "open": [190.0, 191.0],
                                "high": [191.5, 192.5],
                                "low": [189.5, 190.5],
                                "close": [191.2, 192.0],
                                "volume": [1000, 1200],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    session = FakeSession(payload)
    source = YahooChartMarketDataSource(session=session)

    bars = source.fetch_bars("AAPL", "NASDAQ", "20260701", "20260701", "qfq", "1m")

    assert session.calls[0][0] == "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"
    assert session.calls[0][1]["interval"] == "1m"
    assert session.calls[0][1]["range"] == "1d"
    assert [bar.close_price for bar in bars] == [191.2, 192.0]
    assert bars[0].exchange == "NASDAQ"
    assert bars[0].timestamp == datetime.fromtimestamp(1719835800)


def test_binance_source_converts_kline_rows_to_bars() -> None:
    payload = [
        [1719835800000, "65000.0", "65100.0", "64900.0", "65050.0", "12.5", 1719835859999, "813125.0"],
        [1719835860000, "65050.0", "65200.0", "65000.0", "65150.0", "8.0", 1719835919999, "521200.0"],
    ]
    session = FakeSession(payload)
    source = BinanceSpotMarketDataSource(session=session)

    bars = source.fetch_bars("BTCUSDT", "CRYPTO", "20260701", "20260701", "qfq", "1m")

    assert session.calls[0][0] == "https://api.binance.com/api/v3/klines"
    assert session.calls[0][1]["symbol"] == "BTCUSDT"
    assert session.calls[0][1]["interval"] == "1m"
    assert session.calls[0][1]["limit"] == 100
    assert [bar.close_price for bar in bars] == [65050.0, 65150.0]
    assert bars[1].turnover == 521200.0


def test_fallback_source_uses_demo_when_primary_fails() -> None:
    class BrokenSource:
        market = "us_stock"

        def fetch_bars(self, *_args, **_kwargs):
            raise RuntimeError("provider unavailable")

    source = FallbackMarketDataSource(
        primary=BrokenSource(),
        fallback=DemoRealtimeMarketDataSource("us_stock", {"AAPL": 190.0}),
    )

    bars = source.fetch_bars("AAPL", "NASDAQ", "20260701", "20260701", "qfq", "1m")

    assert len(bars) == 1
    assert bars[0].symbol == "AAPL"
    assert source.last_error == "provider unavailable"
