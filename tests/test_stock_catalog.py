from pathlib import Path

import pandas as pd

from ai_trade_system.stock_catalog import (
    StockInfo,
    infer_exchange,
    load_stock_catalog,
    load_symbol_catalog,
    refresh_stock_catalog,
    search_stock_catalog,
)


def test_load_stock_catalog_preserves_six_digit_codes(tmp_path: Path):
    catalog_path = tmp_path / "stocks.csv"
    catalog_path.write_text(
        "code,name,exchange\n000001,平安银行,SZSE\n600000,浦发银行,SSE\n",
        encoding="utf-8",
    )

    stocks = load_stock_catalog(catalog_path)

    assert stocks == [
        StockInfo("000001", "平安银行", "SZSE"),
        StockInfo("600000", "浦发银行", "SSE"),
    ]


def test_load_stock_catalog_missing_file_returns_empty_list(tmp_path: Path):
    assert load_stock_catalog(tmp_path / "missing.csv") == []


def test_search_stock_catalog_matches_code_prefix_and_compact_name():
    stocks = [
        StockInfo("000001", "平安银行", "SZSE"),
        StockInfo("000002", "万  科Ａ", "SZSE"),
        StockInfo("600000", "浦发银行", "SSE"),
    ]

    assert [stock.code for stock in search_stock_catalog(stocks, "00000")] == ["000001", "000002"]
    assert [stock.code for stock in search_stock_catalog(stocks, "万科")] == ["000002"]
    assert [stock.code for stock in search_stock_catalog(stocks, "  银行  ", limit=1)] == ["000001"]


def test_load_symbol_catalog_adds_us_stock_and_crypto_defaults(tmp_path: Path):
    catalog_path = tmp_path / "stocks.csv"
    catalog_path.write_text("code,name,exchange\n000001,平安银行,SZSE\n", encoding="utf-8")

    stocks = load_symbol_catalog(catalog_path)

    assert StockInfo("000001", "平安银行", "SZSE") in stocks
    assert StockInfo("AAPL", "Apple", "NASDAQ") in stocks
    assert StockInfo("BTCUSDT", "Bitcoin", "CRYPTO") in stocks


def test_search_stock_catalog_matches_non_a_share_symbols_without_zero_fill():
    stocks = [
        StockInfo("000001", "平安银行", "SZSE"),
        StockInfo("AAPL", "Apple", "NASDAQ"),
        StockInfo("BTCUSDT", "Bitcoin", "CRYPTO"),
    ]

    assert search_stock_catalog(stocks, "aap")[0] == StockInfo("AAPL", "Apple", "NASDAQ")
    assert search_stock_catalog(stocks, "bitcoin")[0] == StockInfo("BTCUSDT", "Bitcoin", "CRYPTO")


def test_infer_exchange_covers_main_a_share_prefixes():
    assert infer_exchange("600000") == "SSE"
    assert infer_exchange("000001") == "SZSE"
    assert infer_exchange("300001") == "SZSE"
    assert infer_exchange("920000") == "BSE"
    assert infer_exchange("830000") == "BSE"
    assert infer_exchange("430001") == "BSE"


def test_refresh_stock_catalog_writes_standard_csv(monkeypatch, tmp_path: Path):
    class FakeAkshare:
        @staticmethod
        def stock_info_a_code_name():
            return pd.DataFrame(
                [
                    {"code": "1", "name": "平安银行"},
                    {"code": "600000", "name": "浦发银行"},
                    {"code": "920000", "name": "安徽凤凰"},
                ]
            )

    monkeypatch.setitem(__import__("sys").modules, "akshare", FakeAkshare)
    output = tmp_path / "a_share_stocks.csv"

    stocks = refresh_stock_catalog(output)

    assert stocks == [
        StockInfo("000001", "平安银行", "SZSE"),
        StockInfo("600000", "浦发银行", "SSE"),
        StockInfo("920000", "安徽凤凰", "BSE"),
    ]
    assert output.read_text(encoding="utf-8").splitlines() == [
        "code,name,exchange",
        "000001,平安银行,SZSE",
        "600000,浦发银行,SSE",
        "920000,安徽凤凰,BSE",
    ]
