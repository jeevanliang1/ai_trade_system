from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Protocol

import requests

from ai_trade_system.data import fetch_akshare_bars
from ai_trade_system.market import Bar


class MarketDataSource(Protocol):
    market: str

    def fetch_bars(self, symbol: str, exchange: str, start_date: str, end_date: str, adjust: str, timeframe: str) -> list[Bar]:
        ...


BarFetcher = Callable[[str, str, str, str, str, str], list[Bar]]
HTTP_TIMEOUT_SECONDS = 8.0


class CallableMarketDataSource:
    def __init__(self, market: str, fetcher: BarFetcher) -> None:
        self.market = market
        self._fetcher = fetcher

    def fetch_bars(self, symbol: str, exchange: str, start_date: str, end_date: str, adjust: str, timeframe: str) -> list[Bar]:
        return self._fetcher(symbol, start_date, end_date, exchange, adjust, timeframe)


class DemoRealtimeMarketDataSource:
    def __init__(self, market: str, base_prices: dict[str, float]) -> None:
        self.market = market
        self.base_prices = base_prices
        self._ticks: dict[str, int] = {}

    def fetch_bars(self, symbol: str, exchange: str, start_date: str, end_date: str, adjust: str, timeframe: str) -> list[Bar]:
        tick = self._ticks.get(symbol, 0) + 1
        self._ticks[symbol] = tick
        base_price = self.base_prices.get(symbol, 100.0)
        close_price = round(base_price * (1 + tick * 0.001), 4)
        now = datetime.now().replace(second=0, microsecond=0)
        return [
            Bar(
                symbol=symbol,
                exchange=exchange,
                trading_day=now.date(),
                timestamp=now,
                timeframe=timeframe,
                open_price=round(close_price * 0.999, 4),
                high_price=round(close_price * 1.002, 4),
                low_price=round(close_price * 0.998, 4),
                close_price=close_price,
                volume=1000 + tick * 10,
                turnover=close_price * (1000 + tick * 10),
            )
        ]


class YahooChartMarketDataSource:
    market = "us_stock"

    def __init__(self, session: Any | None = None, base_url: str = "https://query1.finance.yahoo.com/v8/finance/chart") -> None:
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")

    def fetch_bars(self, symbol: str, exchange: str, start_date: str, end_date: str, adjust: str, timeframe: str) -> list[Bar]:
        interval = _external_interval(timeframe)
        response = self.session.get(
            f"{self.base_url}/{symbol}",
            params={"range": "1d", "interval": interval, "includePrePost": "false"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result:
            return []
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        bars: list[Bar] = []
        for index, timestamp in enumerate(timestamps):
            open_price = _float_at(quote.get("open"), index)
            high_price = _float_at(quote.get("high"), index)
            low_price = _float_at(quote.get("low"), index)
            close_price = _float_at(quote.get("close"), index)
            volume = _float_at(quote.get("volume"), index, default=0.0)
            if open_price is None or high_price is None or low_price is None or close_price is None:
                continue
            bar_time = datetime.fromtimestamp(int(timestamp))
            bars.append(
                Bar(
                    symbol=symbol,
                    exchange=exchange,
                    trading_day=bar_time.date(),
                    timestamp=bar_time,
                    timeframe=timeframe,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume or 0.0,
                    turnover=close_price * (volume or 0.0),
                )
            )
        return bars


class BinanceSpotMarketDataSource:
    market = "crypto"

    def __init__(self, session: Any | None = None, base_url: str = "https://api.binance.com") -> None:
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")

    def fetch_bars(self, symbol: str, exchange: str, start_date: str, end_date: str, adjust: str, timeframe: str) -> list[Bar]:
        interval = _external_interval(timeframe)
        response = self.session.get(
            f"{self.base_url}/api/v3/klines",
            params={"symbol": symbol.upper(), "interval": interval, "limit": 100},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        bars: list[Bar] = []
        for row in response.json():
            if len(row) < 8:
                continue
            bar_time = datetime.fromtimestamp(int(row[0]) / 1000)
            open_price = float(row[1])
            high_price = float(row[2])
            low_price = float(row[3])
            close_price = float(row[4])
            volume = float(row[5])
            turnover = float(row[7])
            bars.append(
                Bar(
                    symbol=symbol,
                    exchange=exchange,
                    trading_day=bar_time.date(),
                    timestamp=bar_time,
                    timeframe=timeframe,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    turnover=turnover,
                )
            )
        return bars


class FallbackMarketDataSource:
    def __init__(self, primary: MarketDataSource, fallback: MarketDataSource) -> None:
        self.market = primary.market
        self.primary = primary
        self.fallback = fallback
        self.last_error: str | None = None

    def fetch_bars(self, symbol: str, exchange: str, start_date: str, end_date: str, adjust: str, timeframe: str) -> list[Bar]:
        try:
            bars = self.primary.fetch_bars(symbol, exchange, start_date, end_date, adjust, timeframe)
            self.last_error = None
            return bars
        except Exception as exc:
            self.last_error = str(exc)
            return self.fallback.fetch_bars(symbol, exchange, start_date, end_date, adjust, timeframe)


def default_realtime_market_data_sources(fetch_bars: BarFetcher = fetch_akshare_bars) -> dict[str, MarketDataSource]:
    return {
        "a_share": CallableMarketDataSource("a_share", fetch_bars),
        "us_stock": FallbackMarketDataSource(
            YahooChartMarketDataSource(),
            DemoRealtimeMarketDataSource("us_stock", {"AAPL": 190.0, "NVDA": 120.0, "TSLA": 180.0}),
        ),
        "crypto": FallbackMarketDataSource(
            BinanceSpotMarketDataSource(),
            DemoRealtimeMarketDataSource("crypto", {"BTCUSDT": 65000.0, "ETHUSDT": 3500.0}),
        ),
    }


def _external_interval(timeframe: str) -> str:
    if timeframe == "daily":
        return "1d"
    return timeframe


def _float_at(values: list[Any] | None, index: int, default: float | None = None) -> float | None:
    if values is None or index >= len(values):
        return default
    value = values[index]
    if value is None:
        return default
    return float(value)
