import sys
import json
from datetime import date
from pathlib import Path

import pandas as pd

from ai_trade_system.data import write_bars_csv
from ai_trade_system.cli import main
from ai_trade_system.market import Bar
from ai_trade_system.strategies.popular import ChanStructureStrategy


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


def test_cli_stocks_search_prints_name_code_and_exchange(monkeypatch, tmp_path: Path, capsys):
    catalog_path = tmp_path / "stocks.csv"
    catalog_path.write_text("code,name,exchange\n000001,平安银行,SZSE\n600000,浦发银行,SSE\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["ai-trade", "stocks", "search", "平安", "--catalog", str(catalog_path)])

    main()

    output = capsys.readouterr().out
    assert "000001" in output
    assert "平安银行" in output
    assert "SZSE" in output


def test_cli_stocks_refresh_writes_catalog(monkeypatch, tmp_path: Path, capsys):
    class FakeAkshare:
        @staticmethod
        def stock_info_a_code_name():
            return pd.DataFrame([{"code": "1", "name": "平安银行"}])

    monkeypatch.setitem(sys.modules, "akshare", FakeAkshare)
    output_path = tmp_path / "a_share_stocks.csv"
    monkeypatch.setattr(sys, "argv", ["ai-trade", "stocks", "refresh", "--output", str(output_path)])

    main()

    assert "wrote 1 stocks" in capsys.readouterr().out
    assert output_path.read_text(encoding="utf-8").splitlines() == [
        "code,name,exchange",
        "000001,平安银行,SZSE",
    ]


def test_cli_data_update_watchlist_writes_managed_csv_files(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.chdir(tmp_path)
    watchlist_path = tmp_path / "config/watchlist.json"
    watchlist_path.parent.mkdir(parents=True, exist_ok=True)
    watchlist_path.write_text(
        json.dumps({"stocks": [{"code": "601318", "name": "中国平安", "exchange": "SSE"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    from ai_trade_system import data_manager

    def fake_fetch(symbol: str, start_date: str, end_date: str, exchange: str, adjust: str):
        assert (symbol, start_date, end_date, exchange, adjust) == ("601318", "20260617", "20260618", "SSE", "qfq")
        return [_bar(symbol, exchange, date(2026, 6, 17), 51.0), _bar(symbol, exchange, date(2026, 6, 18), 52.0)]

    monkeypatch.setattr(data_manager, "fetch_akshare_daily_bars", fake_fetch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai-trade",
            "data",
            "update-watchlist",
            "--start",
            "20260617",
            "--end",
            "20260618",
            "--if-stale",
        ],
    )

    main()

    output = capsys.readouterr().out
    assert "updated=1 skipped=0 failed=0" in output
    assert "601318\tSSE\tupdated" in output
    assert (tmp_path / "data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv").exists()


def test_cli_backtest_uses_chan_structure_strategy(monkeypatch, tmp_path: Path, capsys):
    data_path = tmp_path / "bars.csv"
    write_bars_csv([_bar("000001", "SZSE", date(2026, 6, 18), 10.0)], data_path)
    seen = {}

    class FakeResult:
        final_equity = 100000.0
        trades = []

    def fake_run_backtest(bars, strategy, config):
        seen["strategy"] = strategy
        return FakeResult()

    monkeypatch.setattr("ai_trade_system.cli.run_backtest", fake_run_backtest)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai-trade",
            "backtest",
            "--data",
            str(data_path),
            "--symbol",
            "000001",
            "--size",
            "200",
        ],
    )

    main()

    assert isinstance(seen["strategy"], ChanStructureStrategy)
    assert seen["strategy"].trade_size == 200
    assert "final_equity=100000.00" in capsys.readouterr().out
