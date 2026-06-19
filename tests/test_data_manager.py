from __future__ import annotations

from datetime import date
from pathlib import Path

from ai_trade_system.data import read_bars_csv, write_bars_csv
from ai_trade_system.data_manager import data_file_for_stock, list_watchlist_data_status, update_stock_data, update_watchlist_data
from ai_trade_system.market import Bar


def _bar(symbol: str, exchange: str, day: date, close: float) -> Bar:
    return Bar(
        symbol=symbol,
        exchange=exchange,
        trading_day=day,
        open_price=close - 0.2,
        high_price=close + 0.4,
        low_price=close - 0.5,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
    )


def test_data_file_for_stock_uses_canonical_market_directory(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    data_file = data_file_for_stock({"code": "601318", "name": "中国平安", "exchange": "sse"}, adjust="qfq")

    assert data_file.code == "601318"
    assert data_file.exchange == "SSE"
    assert data_file.latest_path == Path("data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv")
    assert data_file.increment_path("20260618", "20260617", "20260618") == Path(
        "data/market/a_share/SSE/601318/increments/601318_SSE_daily_qfq_20260618_from_20260617_to_20260618.csv"
    )
    assert data_file.manifest_path == Path("data/market/a_share/SSE/601318/manifest.json")


def test_update_stock_data_merges_latest_csv_and_writes_increment_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stock = {"code": "601318", "name": "中国平安", "exchange": "SSE"}
    data_file = data_file_for_stock(stock)
    write_bars_csv(
        [
            _bar("601318", "SSE", date(2026, 6, 16), 50.0),
            _bar("601318", "SSE", date(2026, 6, 17), 51.0),
        ],
        data_file.latest_path,
    )

    def fake_fetch(symbol: str, start_date: str, end_date: str, exchange: str, adjust: str):
        assert (symbol, start_date, end_date, exchange, adjust) == ("601318", "20260618", "20260618", "SSE", "qfq")
        return [_bar(symbol, exchange, date(2026, 6, 18), 52.0)]

    result = update_stock_data(stock, start_date="20260601", end_date="20260618", fetcher=fake_fetch)

    assert result.status == "updated"
    assert result.fetched_rows == 1
    assert result.latest_rows == 3
    assert result.latest_path == data_file.latest_path.as_posix()
    assert result.increment_path == data_file.increment_path("20260618", "20260618", "20260618").as_posix()
    assert [bar.trading_day for bar in read_bars_csv(data_file.latest_path)] == [date(2026, 6, 16), date(2026, 6, 17), date(2026, 6, 18)]
    assert read_bars_csv(result.increment_path)[0].close_price == 52.0

    manifest = data_file.load_manifest()
    assert manifest["code"] == "601318"
    assert manifest["name"] == "中国平安"
    assert manifest["latest_start"] == "2026-06-16"
    assert manifest["latest_end"] == "2026-06-18"
    assert manifest["latest_rows"] == 3
    assert manifest["last_increment_path"] == result.increment_path


def test_update_stock_data_keeps_existing_csv_when_increment_fetch_fails(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stock = {"code": "688001", "name": "华兴源创", "exchange": "SSE"}
    data_file = data_file_for_stock(stock)
    write_bars_csv(
        [
            _bar("688001", "SSE", date(2026, 6, 17), 30.0),
            _bar("688001", "SSE", date(2026, 6, 18), 31.0),
        ],
        data_file.latest_path,
    )

    def fail_fetch(symbol: str, start_date: str, end_date: str, exchange: str, adjust: str):
        assert (symbol, start_date, end_date, exchange, adjust) == ("688001", "20260619", "20260619", "SSE", "qfq")
        raise RuntimeError("provider has no data for requested end date")

    result = update_stock_data(stock, start_date="20230619", end_date="20260619", if_stale=True, fetcher=fail_fetch)

    assert result.status == "skipped"
    assert result.fetched_start == "20260619"
    assert result.fetched_end == "20260619"
    assert result.fetched_rows == 0
    assert result.latest_rows == 2
    assert result.latest_start == "2026-06-17"
    assert result.latest_end == "2026-06-18"
    assert result.latest_path == data_file.latest_path.as_posix()
    assert result.increment_path is None
    assert "using existing local data" in result.message
    assert "provider has no data" in result.message
    assert [bar.trading_day for bar in read_bars_csv(data_file.latest_path)] == [date(2026, 6, 17), date(2026, 6, 18)]


def test_watchlist_status_marks_missing_and_stale_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stock = {"code": "000001", "name": "平安银行", "exchange": "SZSE"}
    data_file = data_file_for_stock(stock)
    write_bars_csv([_bar("000001", "SZSE", date(2026, 6, 17), 12.0)], data_file.latest_path)
    data_file.write_manifest(
        {
            "code": "000001",
            "name": "平安银行",
            "exchange": "SZSE",
            "adjust": "qfq",
            "latest_path": data_file.latest_path.as_posix(),
            "latest_start": "2026-06-17",
            "latest_end": "2026-06-17",
            "latest_rows": 1,
        }
    )

    statuses = list_watchlist_data_status([stock, {"code": "601318", "name": "中国平安", "exchange": "SSE"}], as_of=date(2026, 6, 18))

    assert statuses[0]["exists"] is True
    assert statuses[0]["stale"] is True
    assert statuses[0]["latest_end"] == "2026-06-17"
    assert statuses[1]["exists"] is False
    assert statuses[1]["stale"] is True
    assert statuses[1]["latest_path"].endswith("601318_SSE_daily_qfq_latest.csv")


def test_update_watchlist_data_updates_needed_stocks_and_skips_fresh_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stocks = [
        {"code": "000001", "name": "平安银行", "exchange": "SZSE"},
        {"code": "601318", "name": "中国平安", "exchange": "SSE"},
    ]
    fresh_file = data_file_for_stock(stocks[0])
    write_bars_csv([_bar("000001", "SZSE", date(2026, 6, 18), 12.0)], fresh_file.latest_path)
    fresh_file.write_manifest(
        {
            "code": "000001",
            "name": "平安银行",
            "exchange": "SZSE",
            "adjust": "qfq",
            "latest_path": fresh_file.latest_path.as_posix(),
            "latest_start": "2026-06-18",
            "latest_end": "2026-06-18",
            "latest_rows": 1,
        }
    )

    fetched: list[str] = []

    def fake_fetch(symbol: str, start_date: str, end_date: str, exchange: str, adjust: str):
        fetched.append(symbol)
        return [_bar(symbol, exchange, date(2026, 6, 18), 52.0)]

    result = update_watchlist_data(stocks, start_date="20260617", end_date="20260618", if_stale=True, fetcher=fake_fetch)

    assert result["updated"] == 1
    assert result["skipped"] == 1
    assert result["failed"] == 0
    assert fetched == ["601318"]
    assert [item["status"] for item in result["files"]] == ["skipped", "updated"]
