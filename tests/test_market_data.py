from datetime import date

import pandas as pd
import requests

from ai_trade_system.data import fetch_akshare_daily_bars, normalize_akshare_bars


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
