import csv
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

from ai_trade_system.data import (
    fetch_akshare_bars,
    fetch_akshare_daily_bars,
    normalize_akshare_bars,
    normalize_akshare_minute_bars,
    read_bars_csv,
    write_bars_csv,
)
from ai_trade_system.market import Bar


def test_normalize_akshare_bars_maps_chinese_columns_and_sorts_rows():
    raw = pd.DataFrame(
        [
            {"日期": "2024-01-03", "开盘": 10.2, "最高": 10.8, "最低": 10.1, "收盘": 10.6, "成交量": 1200, "成交额": 12600},
            {"日期": "2024-01-02", "开盘": 10.0, "最高": 10.5, "最低": 9.9, "收盘": 10.2, "成交量": 1000, "成交额": 10100},
        ]
    )

    bars = normalize_akshare_bars(raw, symbol="000001", exchange="SZSE")

    assert [bar.trading_day for bar in bars] == [date(2024, 1, 2), date(2024, 1, 3)]
    assert bars[0].symbol == "000001"
    assert bars[0].exchange == "SZSE"
    assert bars[0].open_price == 10.0
    assert bars[0].close_price == 10.2
    assert bars[0].volume == 1000


def test_normalize_akshare_bars_rejects_missing_required_columns():
    raw = pd.DataFrame([{"日期": "2024-01-02", "开盘": 10.0}])

    try:
        normalize_akshare_bars(raw, symbol="000001", exchange="SZSE")
    except ValueError as exc:
        assert "missing required columns" in str(exc)
        assert "收盘" in str(exc)
    else:
        raise AssertionError("missing columns should raise ValueError")


def test_fetch_akshare_daily_bars_wraps_network_errors(monkeypatch):
    class FakeAkshare:
        @staticmethod
        def stock_zh_a_hist(**kwargs):
            raise requests.exceptions.ProxyError("proxy blocked")

    monkeypatch.setitem(__import__("sys").modules, "akshare", FakeAkshare)

    try:
        fetch_akshare_daily_bars("000001", "20240102", "20240105", "SZSE")
    except RuntimeError as exc:
        assert "AKShare request failed" in str(exc)
        assert "existing CSV" in str(exc)
    else:
        raise AssertionError("network errors should raise a friendly RuntimeError")


def test_fetch_akshare_daily_bars_falls_back_to_tencent_when_eastmoney_fails(monkeypatch):
    calls = []

    class FakeAkshare:
        @staticmethod
        def stock_zh_a_hist(**kwargs):
            calls.append(("eastmoney", kwargs))
            raise requests.exceptions.ProxyError("proxy blocked")

        @staticmethod
        def stock_zh_a_hist_tx(**kwargs):
            calls.append(("tencent", kwargs))
            return pd.DataFrame(
                [
                    {"date": "2024-01-03", "open": 7.63, "close": 7.64, "high": 7.66, "low": 7.59, "amount": 733610},
                    {"date": "2024-01-02", "open": 7.83, "close": 7.65, "high": 7.86, "low": 7.65, "amount": 1158366},
                ]
            )

    monkeypatch.setitem(__import__("sys").modules, "akshare", FakeAkshare)

    bars = fetch_akshare_daily_bars("000001", "20240102", "20240105", "SZSE")

    assert [call[0] for call in calls] == ["eastmoney", "tencent"]
    assert calls[1][1]["symbol"] == "sz000001"
    assert [bar.trading_day for bar in bars] == [date(2024, 1, 2), date(2024, 1, 3)]
    assert bars[0].close_price == 7.65


def test_normalize_akshare_minute_bars_maps_timestamp_and_timeframe():
    raw = pd.DataFrame(
        [
            {"day": "2024-01-02 09:35:00", "open": 10.2, "high": 10.4, "low": 10.1, "close": 10.3, "volume": 1200},
            {"day": "2024-01-02 09:31:00", "open": 10.0, "high": 10.2, "low": 9.9, "close": 10.1, "volume": 1000},
        ]
    )

    bars = normalize_akshare_minute_bars(raw, symbol="000001", exchange="SZSE", timeframe="5m")

    assert [bar.timestamp for bar in bars] == [datetime(2024, 1, 2, 9, 31), datetime(2024, 1, 2, 9, 35)]
    assert [bar.trading_day for bar in bars] == [date(2024, 1, 2), date(2024, 1, 2)]
    assert [bar.timeframe for bar in bars] == ["5m", "5m"]
    assert bars[0].turnover == 0.0


def test_bars_csv_round_trips_minute_metadata_and_reads_legacy_daily(tmp_path: Path):
    minute_path = tmp_path / "minute.csv"
    write_bars_csv(
        [
            Bar(
                symbol="000001",
                exchange="SZSE",
                trading_day=date(2024, 1, 2),
                open_price=10.0,
                high_price=10.2,
                low_price=9.9,
                close_price=10.1,
                volume=1000,
                turnover=10100,
                timestamp=datetime(2024, 1, 2, 9, 31),
                timeframe="1m",
            )
        ],
        minute_path,
    )

    minute_rows = read_bars_csv(minute_path)

    assert minute_rows[0].timestamp == datetime(2024, 1, 2, 9, 31)
    assert minute_rows[0].timeframe == "1m"

    legacy_path = tmp_path / "legacy.csv"
    with legacy_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["symbol", "exchange", "trading_day", "open_price", "high_price", "low_price", "close_price", "volume", "turnover"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "000001",
                "exchange": "SZSE",
                "trading_day": "2024-01-02",
                "open_price": 10,
                "high_price": 10.2,
                "low_price": 9.9,
                "close_price": 10.1,
                "volume": 1000,
                "turnover": 10100,
            }
        )

    legacy_rows = read_bars_csv(legacy_path)

    assert legacy_rows[0].timeframe == "daily"
    assert legacy_rows[0].timestamp is None


def test_fetch_akshare_bars_routes_minute_requests_to_sina(monkeypatch):
    calls = []

    class FakeAkshare:
        @staticmethod
        def stock_zh_a_minute(**kwargs):
            calls.append(kwargs)
            return pd.DataFrame(
                [
                    {"day": "2024-01-02 09:31:00", "open": 10, "high": 10.2, "low": 9.9, "close": 10.1, "volume": 1000},
                ]
            )

    monkeypatch.setitem(__import__("sys").modules, "akshare", FakeAkshare)

    bars = fetch_akshare_bars("000001", "20240102", "20240102", "SZSE", "qfq", timeframe="5m")

    assert calls == [{"symbol": "sz000001", "period": "5", "adjust": "qfq"}]
    assert bars[0].timestamp == datetime(2024, 1, 2, 9, 31)
    assert bars[0].timeframe == "5m"
